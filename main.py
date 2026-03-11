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
from kivy.utils import platform

from waveform.audio_source import AudioSource, build_audio_source
from waveform.constants import BACKGROUND_RGBA
from waveform.widget import WaveformWidget, create_default_buffer


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

    def build(self) -> WaveformWidget:
        Window.clearcolor = BACKGROUND_RGBA
        buffer = create_default_buffer(Window.width)
        widget = WaveformWidget(amplitudes=buffer)

        if platform == "android" and not self._use_mock:
            _request_android_mic_permission()

        self._source = build_audio_source(use_mock=self._use_mock, amplitudes=buffer)

        # Delay source startup until the first frame to avoid startup race with UI init.
        Clock.schedule_once(lambda _dt: self._safe_start_source(), 0)
        return widget

    def _safe_start_source(self) -> None:
        if self._source is None:
            return
        try:
            self._source.start()
        except Exception:
            # If mic source startup fails, fallback to mock mode automatically.
            fallback = build_audio_source(
                use_mock=True, amplitudes=self._source.get_buffer()
            )
            self._source = fallback
            self._source.start()

    def on_stop(self) -> None:
        if self._source is not None:
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
