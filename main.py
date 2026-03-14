"""Application entrypoint for the Android-style waveform demo."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from typing import Optional

# Disable Kivy CLI parsing so application-specific args (e.g. --mock) work directly.
os.environ.setdefault("KIVY_NO_ARGS", "1")

try:
    from kivy.animation import Animation
    from kivy.app import App
    from kivy.clock import Clock
    from kivy.core.window import Window
    from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
    from kivy.metrics import dp
    from kivy.uix.anchorlayout import AnchorLayout
    from kivy.uix.behaviors import ButtonBehavior
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.floatlayout import FloatLayout
    from kivy.uix.label import Label
    from kivy.uix.widget import Widget
    from kivy.utils import platform
except ModuleNotFoundError as exc:
    if exc.name != "kivy":
        raise

    # Auto-bootstrap into the project conda env so users can run from base shell.
    if os.environ.get("VOLUME_DEMO_BOOTSTRAPPED") != "1":
        conda_cmd = shutil.which("conda")
        if conda_cmd:
            env = os.environ.copy()
            env["VOLUME_DEMO_BOOTSTRAPPED"] = "1"
            cmd = [
                conda_cmd,
                "run",
                "-n",
                "voldemo",
                "python",
                os.path.abspath(__file__),
                *sys.argv[1:],
            ]
            raise SystemExit(subprocess.call(cmd, env=env))

    print(
        "Missing dependency: kivy. Please run: conda activate voldemo; pip install -r requirements.txt"
    )
    raise SystemExit(1)

from waveform.audio_source import AudioSource, build_audio_source
from waveform.constants import BACKGROUND_RGBA
from waveform.widget import WaveformWidget, create_default_buffer


def _resolve_ui_font() -> Optional[str]:
    """Return a CJK-capable font path when available, else None."""
    if platform != "win":
        return None

    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _request_android_mic_permission() -> None:
    """Ask for microphone permission at runtime on Android 6.0+ devices."""
    if platform != "android":
        return
    try:
        from android.permissions import Permission, request_permissions

        request_permissions([Permission.RECORD_AUDIO])
    except Exception:
        # Keep app alive in mock fallback mode if permission API is unavailable.
        pass


class RecordButton(ButtonBehavior, Widget):
    """Custom iOS-style recording button."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        from waveform.constants import BTN_OUTER_RADIUS_DP

        self.size_hint = (None, None)
        side = dp(BTN_OUTER_RADIUS_DP * 2 + 4)
        self.size = (side, side)

        self.is_recording = False
        self._animating = False

        with self.canvas:
            Color(1, 1, 1, 1)
            self.outer_line = Line(
                circle=(self.center_x, self.center_y, dp(BTN_OUTER_RADIUS_DP)),
                width=dp(2.5),
            )

            Color(1, 0.23, 0.19, 1)
            from waveform.constants import BTN_INNER_IDLE_RADIUS_DP

            radius = dp(BTN_INNER_IDLE_RADIUS_DP)
            self.inner_shape = RoundedRectangle(
                pos=(self.center_x - radius, self.center_y - radius),
                size=(radius * 2, radius * 2),
                radius=[
                    (radius, radius),
                    (radius, radius),
                    (radius, radius),
                    (radius, radius),
                ],
            )

        self.bind(pos=self.update_canvas, size=self.update_canvas)

    def update_canvas(self, *_args) -> None:
        from waveform.constants import (
            BTN_OUTER_RADIUS_DP,
            BTN_INNER_IDLE_RADIUS_DP,
            BTN_INNER_REC_SIZE_DP,
        )

        self.outer_line.circle = (self.center_x, self.center_y, dp(BTN_OUTER_RADIUS_DP))

        if not self._animating:
            if self.is_recording:
                s = dp(BTN_INNER_REC_SIZE_DP)
            else:
                s = dp(BTN_INNER_IDLE_RADIUS_DP * 2)

            self.inner_shape.pos = (self.center_x - s * 0.5, self.center_y - s * 0.5)
            self.inner_shape.size = (s, s)

    def set_recording_state(self, is_recording: bool) -> None:
        if getattr(self, "inner_shape", None) is None:
            return

        self.is_recording = is_recording
        self._animating = True

        from waveform.constants import (
            BTN_INNER_IDLE_RADIUS_DP,
            BTN_INNER_REC_SIZE_DP,
            BTN_INNER_REC_RADIUS_DP,
        )

        if is_recording:
            r = dp(BTN_INNER_REC_RADIUS_DP)
            target_size = dp(BTN_INNER_REC_SIZE_DP)
            target_radius = [(r, r), (r, r), (r, r), (r, r)]
        else:
            r = dp(BTN_INNER_IDLE_RADIUS_DP)
            target_size = dp(BTN_INNER_IDLE_RADIUS_DP * 2)
            target_radius = [(r, r), (r, r), (r, r), (r, r)]

        target_pos = (
            self.center_x - target_size * 0.5,
            self.center_y - target_size * 0.5,
        )

        anim = Animation(
            pos=target_pos,
            size=(target_size, target_size),
            radius=target_radius,
            d=0.25,
            t="out_quad",
        )
        anim.on_complete = self._on_anim_complete
        anim.start(self.inner_shape)

    def _on_anim_complete(self, *_args) -> None:
        self._animating = False


class WaveformApp(App):
    """Main Kivy app that wires source data into the waveform widget."""

    def __init__(self, use_mock: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self._use_mock = use_mock
        self._source: Optional[AudioSource] = None
        self._is_running = False
        self._elapsed_seconds = 0.0
        self._waveform: Optional[WaveformWidget] = None
        self._status_label: Optional[Label] = None
        self._fps_label: Optional[Label] = None
        self._timer_label: Optional[Label] = None
        self._toggle_button: Optional[Button] = None
        self._ui_font: Optional[str] = None
        self._ascii_ui = False
        self._fps_event = None

    def _ui_text(self, zh: str, en: str) -> str:
        """Use Chinese text when a CJK-capable font exists, else ASCII fallback."""
        return en if self._ascii_ui else zh

    def build(self) -> Widget:
        Window.clearcolor = BACKGROUND_RGBA
        self._ui_font = _resolve_ui_font()
        self._ascii_ui = self._ui_font is None

        buffer = create_default_buffer(Window.width)
        self._waveform = WaveformWidget(amplitudes=buffer)

        if platform == "android" and not self._use_mock:
            _request_android_mic_permission()

        self._source = build_audio_source(use_mock=self._use_mock, amplitudes=buffer)

        root = FloatLayout()

        # High contrast, large timer label at the top.
        from waveform.constants import TIMER_FONT_SIZE_DP

        self._timer_label = Label(
            text="00:00.00",
            font_size=dp(TIMER_FONT_SIZE_DP),
            bold=True,
            halign="center",
            valign="middle",
            size_hint=(None, None),
            size=(dp(300), dp(100)),
            pos_hint={"center_x": 0.5, "top": 0.9},
        )

        # Big center layout for waveform container
        wave_container = BoxLayout(
            orientation="vertical",
            size_hint=(1.0, None),
            height=dp(200),
            pos_hint={"center_x": 0.5, "center_y": 0.55},
        )
        wave_container.add_widget(self._waveform)

        # Bottom circular record button.
        self._toggle_button = RecordButton(pos_hint={"center_x": 0.5, "y": 0.1})
        self._toggle_button.bind(on_release=self._on_toggle_pressed)

        root.add_widget(self._timer_label)
        root.add_widget(wave_container)
        root.add_widget(self._toggle_button)

        self._fps_event = Clock.schedule_interval(self._update_hud, 0.05)
        return root

    def _on_toggle_pressed(self, _instance) -> None:
        if self._is_running:
            self._stop_source()
        else:
            self._start_source()

    def _start_source(self) -> None:
        if self._source is None or self._is_running:
            return
        self._elapsed_seconds = 0.0
        try:
            self._source.start()
        except Exception as e:
            if self._timer_label:
                self._timer_label.font_size = "14sp"
                self._timer_label.text = f"MIC ERROR: {str(e)[:50]}"
            return

        self._is_running = True
        if self._waveform:
            self._waveform.is_recording = True
        self._update_status_ui()

    def _stop_source(self) -> None:
        if self._source is None or not self._is_running:
            return
        self._source.stop()
        self._is_running = False
        if self._waveform:
            self._waveform.is_recording = False
        self._update_status_ui()

    def _update_status_ui(self) -> None:
        if self._toggle_button is not None and hasattr(
            self._toggle_button, "set_recording_state"
        ):
            self._toggle_button.set_recording_state(self._is_running)

    def _update_hud(self, dt: float) -> None:
        if self._is_running:
            self._elapsed_seconds += dt

        if self._timer_label is not None:
            total_time = self._elapsed_seconds
            minutes = int(total_time) // 60
            seconds = int(total_time) % 60
            milliseconds = int((total_time * 100) % 100)
            self._timer_label.text = f"{minutes:02d}:{seconds:02d}.{milliseconds:02d}"

    def on_stop(self) -> None:
        if self._fps_event is not None:
            self._fps_event.cancel()
            self._fps_event = None
        if self._source is not None and self._is_running:
            self._source.stop()

    def on_pause(self) -> bool:
        # Halt recording and animation when the app is backgrounded to save resources.
        if self._is_running:
            self._stop_source()
        return True

    def on_resume(self) -> None:
        # Upon returning to the foreground, remain in the paused state to let the user manually resume.
        pass


def parse_args(argv: list[str]) -> argparse.Namespace:
    """CLI options: support mock mode for non-Android and CI validation."""
    parser = argparse.ArgumentParser(description="Kivy waveform demo")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force mock data source even on Android devices.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    app = WaveformApp(use_mock=args.mock)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
