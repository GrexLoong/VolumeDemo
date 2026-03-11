"""Waveform rendering widget using Kivy canvas instructions."""

from __future__ import annotations

from collections import deque
from typing import Deque, List

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.uix.widget import Widget

from waveform.constants import (
    BACKGROUND_RGBA,
    BAR_GAP_DP,
    BAR_MAX_HEIGHT_DP,
    BAR_MIN_HEIGHT_DP,
    BAR_RADIUS_DP,
    BAR_RGBA,
    BAR_WIDTH_DP,
    EMA_ALPHA,
    RENDER_FPS,
    to_dp,
)


class WaveformWidget(Widget):
    """Render right-to-left scrolling waveform bars with smooth interpolation."""

    def __init__(self, amplitudes: Deque[float], **kwargs) -> None:
        super().__init__(**kwargs)
        self._amplitudes = amplitudes
        self._bars: List[RoundedRectangle] = []
        self._smoothed_heights: List[float] = []

        # Device-pixel values cached from dp constants.
        self._bar_width = to_dp(BAR_WIDTH_DP)
        self._bar_gap = to_dp(BAR_GAP_DP)
        self._bar_min_height = to_dp(BAR_MIN_HEIGHT_DP)
        self._bar_max_height = to_dp(BAR_MAX_HEIGHT_DP)
        self._bar_radius = to_dp(BAR_RADIUS_DP)

        with self.canvas.before:
            Color(*BACKGROUND_RGBA)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self._on_layout_change, size=self._on_layout_change)
        Clock.schedule_once(lambda _dt: self._rebuild_bars(), 0)
        Clock.schedule_interval(self.update_frame, 1.0 / RENDER_FPS)

    def _on_layout_change(self, *_args) -> None:
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        self._rebuild_bars()

    def _rebuild_bars(self) -> None:
        # Rebuild bars only when layout changes to avoid per-frame object churn.
        for bar in self._bars:
            self.canvas.remove(bar)
        self._bars.clear()

        width_per_bar = self._bar_width + self._bar_gap
        if width_per_bar <= 0:
            return

        bar_count = int(self.width // width_per_bar) + 2
        bar_count = max(bar_count, 8)
        self._smoothed_heights = [self._bar_min_height for _ in range(bar_count)]

        with self.canvas:
            Color(*BAR_RGBA)
            for _ in range(bar_count):
                bar = RoundedRectangle(
                    pos=(self.right, self.center_y),
                    size=(0.0, 0.0),
                    radius=[self._bar_radius],
                )
                self._bars.append(bar)

    def update_frame(self, _dt: float) -> None:
        if not self._bars:
            return

        snapshot = list(self._amplitudes)
        snapshot_len = len(snapshot)
        center_y = self.y + self.height * 0.5
        stride = self._bar_width + self._bar_gap

        for index, bar in enumerate(self._bars):
            data_index = snapshot_len - 1 - index
            if data_index < 0:
                bar.size = (0.0, 0.0)
                continue

            amplitude = snapshot[data_index]
            target_h = self._bar_min_height + amplitude * (
                self._bar_max_height - self._bar_min_height
            )

            # EMA smoothing improves perceived fluidity between data ticks.
            current_h = self._smoothed_heights[index]
            smooth_h = current_h * (1.0 - EMA_ALPHA) + target_h * EMA_ALPHA
            self._smoothed_heights[index] = smooth_h

            x = self.right - (index + 1) * stride
            y = center_y - smooth_h * 0.5
            bar.pos = (x, y)
            bar.size = (self._bar_width, smooth_h)


def create_default_buffer(width_hint_px: float) -> Deque[float]:
    """Create a ring buffer sized to current widget width estimate."""
    width_per_bar = to_dp(BAR_WIDTH_DP) + to_dp(BAR_GAP_DP)
    estimated_count = int(width_hint_px // width_per_bar) + 8
    return deque(maxlen=max(estimated_count, 32))
