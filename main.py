"""Application entrypoint for the Android-style waveform demo."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

# Disable Kivy CLI parsing so application-specific args (e.g. --mock) work directly.
os.environ.setdefault("KIVY_NO_ARGS", "1")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.utils import platform

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

    def build(self) -> BoxLayout:
        Window.clearcolor = BACKGROUND_RGBA
        self._ui_font = _resolve_ui_font()
        self._ascii_ui = self._ui_font is None

        buffer = create_default_buffer(Window.width)
        self._waveform = WaveformWidget(amplitudes=buffer)

        if platform == "android" and not self._use_mock:
            _request_android_mic_permission()

        self._source = build_audio_source(use_mock=self._use_mock, amplitudes=buffer)

        # Build a simple control bar for start/stop and runtime diagnostics.
        root = BoxLayout(orientation="vertical", spacing=dp(8), padding=[dp(10)] * 4)
        header = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(8)
        )

        self._toggle_button = Button(
            text=self._ui_text("开始录音", "Start"),
            size_hint_x=None,
            width=dp(120),
            font_name=self._ui_font,
        )
        self._toggle_button.bind(on_release=self._on_toggle_pressed)

        self._status_label = Label(
            text=self._ui_text("状态: 已停止", "Status: Stopped"),
            halign="left",
            valign="middle",
            font_name=self._ui_font,
        )
        self._status_label.bind(
            size=lambda inst, _v: setattr(inst, "text_size", inst.size)
        )

        self._fps_label = Label(
            text="FPS: --",
            size_hint_x=None,
            width=dp(90),
            halign="right",
            valign="middle",
            font_name=self._ui_font,
        )
        self._fps_label.bind(
            size=lambda inst, _v: setattr(inst, "text_size", inst.size)
        )

        self._timer_label = Label(
            text=self._ui_text("时长: 00:00", "Time: 00:00"),
            size_hint_x=None,
            width=dp(120),
            halign="right",
            valign="middle",
            font_name=self._ui_font,
        )
        self._timer_label.bind(
            size=lambda inst, _v: setattr(inst, "text_size", inst.size)
        )

        header.add_widget(self._toggle_button)
        header.add_widget(self._status_label)
        header.add_widget(self._timer_label)
        header.add_widget(self._fps_label)
        root.add_widget(header)
        root.add_widget(self._waveform)

        # Delay source startup until the first frame to avoid startup race with UI init.
        Clock.schedule_once(lambda _dt: self._start_source(), 0)
        self._fps_event = Clock.schedule_interval(self._update_hud, 0.2)
        return root

    def _on_toggle_pressed(self, _instance: Button) -> None:
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
        except Exception:
            # If mic source startup fails, fallback to mock mode automatically.
            fallback = build_audio_source(
                use_mock=True, amplitudes=self._source.get_buffer()
            )
            self._source = fallback
            self._source.start()
        self._is_running = True
        self._update_status_ui()

    def _stop_source(self) -> None:
        if self._source is None or not self._is_running:
            return
        self._source.stop()
        self._is_running = False
        self._update_status_ui()

    def _update_status_ui(self) -> None:
        if self._toggle_button is not None:
            self._toggle_button.text = self._ui_text("停止录音", "Stop") if self._is_running else self._ui_text("开始录音", "Start")
        if self._status_label is not None:
            mode = "Mock" if self._use_mock or platform != "android" else "Mic"
            status = self._ui_text("录音中", "Recording") if self._is_running else self._ui_text("已停止", "Stopped")
            self._status_label.text = self._ui_text("状态", "Status") + f": {status} ({mode})"

    def _update_hud(self, dt: float) -> None:
        if self._is_running:
            self._elapsed_seconds += dt

        if self._timer_label is not None:
            total = int(self._elapsed_seconds)
            minutes = total // 60
            seconds = total % 60
            prefix = self._ui_text("时长", "Time")
            self._timer_label.text = f"{prefix}: {minutes:02d}:{seconds:02d}"

        if self._fps_label is None:
            return
        self._fps_label.text = f"FPS: {Clock.get_fps():.1f}"

    def on_stop(self) -> None:
        if self._fps_event is not None:
            self._fps_event.cancel()
            self._fps_event = None
        if self._source is not None and self._is_running:
            self._source.stop()


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
