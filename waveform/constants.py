"""Shared constants for waveform rendering and data generation."""

from kivy.metrics import dp

# Visual metrics.
BAR_MIN_WIDTH_DP = 4.0
BAR_MAX_WIDTH_DP = 4.0
BAR_GAP_DP = 6.0
BAR_MIN_HEIGHT_DP = 12.0
BAR_MAX_HEIGHT_DP = 180.0
CONTAINER_MIN_HEIGHT_DP = 240.0
CONTAINER_VERTICAL_PADDING_DP = 8.0

# Animation and data rates.
RENDER_FPS = 60.0
BAR_SPAWN_FPS = 5.0
SCROLL_SPEED_DP_PER_SEC = (BAR_MAX_WIDTH_DP + BAR_GAP_DP) * BAR_SPAWN_FPS

# Keep microphone analysis responsive while slowing mock visual feed.
MIC_SAMPLE_FPS = 5.0
MOCK_SAMPLE_FPS = 5.0

# Mock speech envelope (used only in desktop/testing mode).
# Speaking and silence alternate to mimic real recording cadence.
MOCK_SPEAK_MIN_SEC = 1.1
MOCK_SPEAK_MAX_SEC = 2.8
MOCK_SILENCE_MIN_SEC = 0.35
MOCK_SILENCE_MAX_SEC = 1.4

# Speaking segment dynamics.
MOCK_SPEAK_BASE = 0.52
MOCK_SPEAK_SWAY = 0.30
MOCK_SPEAK_SWAY_FREQ_HZ = 0.42
MOCK_DETAIL_SWAY = 0.16
MOCK_DETAIL_FREQ_HZ = 2.4
MOCK_SPEAK_NOISE = 0.05

# Silence segment dynamics.
MOCK_SILENCE_BASE = 0.03
MOCK_SILENCE_NOISE = 0.015

# Attack/release smoothing for anti-flicker while preserving strong rise/fall.
MOCK_ATTACK_ALPHA = 0.45
MOCK_RELEASE_ALPHA = 0.20

# Theme colors (close to Voice Memos style).
BACKGROUND_RGBA = (0.00, 0.00, 0.00, 1.0)
BAR_RGBA = (0.92, 0.97, 1.0, 1.0)
PLAYHEAD_RGBA = (1.0, 0.23, 0.19, 1.0)

# UI metrics
PLAYHEAD_WIDTH_DP = 2.0
PLAYHEAD_MARGIN_RIGHT_DP = 72.0
FADE_OUT_WIDTH_DP = 80.0
TIMER_FONT_SIZE_DP = 72.0
BTN_OUTER_RADIUS_DP = 38.0
BTN_INNER_IDLE_RADIUS_DP = 32.0
BTN_INNER_REC_SIZE_DP = 32.0
BTN_INNER_REC_RADIUS_DP = 8.0

# Audio constants.
SAMPLE_RATE = 44100
MAX_EXPECTED_RMS = 2500.0


def to_dp(value: float) -> float:
    """Convert a dp value into device pixels."""
    return float(dp(value))
