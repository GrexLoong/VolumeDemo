"""Waveform rendering widget using Kivy canvas instructions."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, List

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.uix.widget import Widget

from waveform.constants import (
    BACKGROUND_RGBA,
    BAR_GAP_DP,
    BAR_MAX_HEIGHT_DP,
    BAR_MAX_WIDTH_DP,
    BAR_MIN_HEIGHT_DP,
    BAR_MIN_WIDTH_DP,
    BAR_RGBA,
    BAR_SPAWN_FPS,
    CONTAINER_MIN_HEIGHT_DP,
    CONTAINER_VERTICAL_PADDING_DP,
    FADE_OUT_WIDTH_DP,
    PLAYHEAD_RGBA,
    PLAYHEAD_WIDTH_DP,
    RENDER_FPS,
    SCROLL_SPEED_DP_PER_SEC,
    to_dp,
)


@dataclass
class BarItem:
    """Render instruction and geometry state for one waveform bar."""

    color: Color
    rect: RoundedRectangle
    absolute_x: float
    width: float
    height: float


class WaveformWidget(Widget):
    """Render fixed-gap capsule bars scrolling right-to-left at constant speed."""

    def __init__(self, amplitudes: Deque[float], **kwargs) -> None:
        super().__init__(**kwargs)
        self._amplitudes = amplitudes
        self._bars: List[BarItem] = []
        self._spawn_accumulator = 0.0
        self._viewport_x = 0.0
        self.is_recording = False

        # Device-pixel values cached from dp constants.
        self._bar_min_width = to_dp(BAR_MIN_WIDTH_DP)
        self._bar_max_width = to_dp(BAR_MAX_WIDTH_DP)
        self._bar_gap = to_dp(BAR_GAP_DP)
        self._bar_min_height = to_dp(BAR_MIN_HEIGHT_DP)
        self._bar_max_height = to_dp(BAR_MAX_HEIGHT_DP)
        self._container_min_height = to_dp(CONTAINER_MIN_HEIGHT_DP)
        self._vertical_padding = to_dp(CONTAINER_VERTICAL_PADDING_DP)
        self._spawn_interval = 1.0 / BAR_SPAWN_FPS
        self._scroll_speed = to_dp(SCROLL_SPEED_DP_PER_SEC)
        self._playhead_width = to_dp(PLAYHEAD_WIDTH_DP)
        self._fade_out_width = to_dp(FADE_OUT_WIDTH_DP)

        with self.canvas.before:
            Color(*BACKGROUND_RGBA)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)

        with self.canvas.after:
            Color(*PLAYHEAD_RGBA)
            self._playhead_rect = Rectangle()

        self.bind(pos=self._on_layout_change, size=self._on_layout_change)
        Clock.schedule_interval(self.update_frame, 1.0 / RENDER_FPS)

    def _on_layout_change(self, *_args) -> None:
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

        self._playhead_rect.pos = (self.right - self._playhead_width * 0.5, self.y)
        self._playhead_rect.size = (self._playhead_width, self.height)

        # Redraw all bars relative to the new layout directly using their absolute timeline offsets.
        center_y = self._container_center_y()
        for bar in self._bars:
            screen_x = self.right - (self._viewport_x - bar.absolute_x)
            y = center_y - bar.height * 0.5
            bar.rect.pos = (screen_x, y)

    def _container_center_y(self) -> float:
        return self.y + self.height * 0.5

    def _map_amplitude_to_size(self, amplitude: float) -> tuple[float, float]:
        amp = max(0.0, min(1.0, amplitude))

        # Apply a visual curve to make dynamics more pronounced.
        # This forces low noise to stay near 0, and medium volumes to reach higher.
        visual_amp = max(0.0, (amp - 0.03) * 1.25)
        visual_amp = min(1.0, visual_amp)

        # Height follows strict 12dp~58dp range.
        target_h = self._bar_min_height + visual_amp * (
            self._bar_max_height - self._bar_min_height
        )

        # Keep vertical safety margin if container is temporarily too short.
        available_h = max(0.0, self.height - self._vertical_padding * 2.0)
        capped_max_h = min(self._bar_max_height, available_h)
        if capped_max_h < self._bar_min_height:
            capped_max_h = self._bar_min_height
        height = max(self._bar_min_height, min(target_h, capped_max_h))

        # Width naturally scales from min to max based on the visual amplitude
        width = self._bar_min_width + visual_amp * (
            self._bar_max_width - self._bar_min_width
        )
        return width, height

    def _latest_amplitude(self) -> float:
        if not self._amplitudes:
            return 0.0
        return float(self._amplitudes[-1])

    def _spawn_bar(self) -> None:
        amplitude = self._latest_amplitude()
        width, height = self._map_amplitude_to_size(amplitude)
        center_y = self._container_center_y()

        if self._bars:
            rightmost = self._bars[-1]
            abs_x = rightmost.absolute_x + rightmost.width + self._bar_gap
        else:
            abs_x = self._viewport_x - width

        screen_x = self.right - (self._viewport_x - abs_x)
        y = center_y - height * 0.5
        radius = width * 0.5

        with self.canvas:
            color = Color(*BAR_RGBA)
            rect = RoundedRectangle(
                pos=(screen_x, y),
                size=(width, height),
                radius=[radius, radius, radius, radius],
            )

        self._bars.append(
            BarItem(
                color=color, rect=rect, absolute_x=abs_x, width=width, height=height
            )
        )

    def _move_and_prune(self, dt: float) -> None:
        self._viewport_x += self._scroll_speed * dt

        if not self._bars:
            return

        center_y = self._container_center_y()
        fade_start_x = self.x + self._fade_out_width
        alive: List[BarItem] = []

        for bar in self._bars:
            screen_x = self.right - (self._viewport_x - bar.absolute_x)

            if screen_x + bar.width < self.x:
                self.canvas.remove(bar.color)
                self.canvas.remove(bar.rect)
                continue

            y = center_y - bar.height * 0.5
            bar.rect.pos = (screen_x, y)
            bar.rect.size = (bar.width, bar.height)

            if screen_x < fade_start_x:
                alpha_factor = max(0.0, (screen_x - self.x) / self._fade_out_width)
                bar.color.a = alpha_factor * BAR_RGBA[3]
            else:
                bar.color.a = BAR_RGBA[3]

            alive.append(bar)

        self._bars = alive

    def _ensure_container_hint(self) -> None:
        # The component should reserve enough vertical room for 58dp bars.
        if self.height < self._container_min_height:
            self.size_hint_y = None
            self.height = self._container_min_height

    def update_frame(self, dt: float) -> None:
        self._ensure_container_hint()

        if not self.is_recording:
            return

        self._move_and_prune(dt)

        self._spawn_accumulator += dt
        while self._spawn_accumulator >= self._spawn_interval:
            self._spawn_accumulator -= self._spawn_interval
            self._spawn_bar()


def create_default_buffer(width_hint_px: float) -> Deque[float]:
    """Create a ring buffer sized to current widget width estimate."""
    width_per_bar = to_dp(BAR_MAX_WIDTH_DP) + to_dp(BAR_GAP_DP)
    estimated_count = int(width_hint_px // width_per_bar) + 8
    return deque(maxlen=max(estimated_count, 32))
