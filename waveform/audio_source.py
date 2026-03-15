"""Audio source abstractions for waveform data collection."""

from __future__ import annotations

import math
import random
import threading
import time
from array import array
from collections import deque
from typing import Deque, Optional, Protocol

from kivy.utils import platform

from waveform.constants import (
    MAX_EXPECTED_RMS,
    MIC_SAMPLE_FPS,
    MOCK_ATTACK_ALPHA,
    MOCK_DETAIL_FREQ_HZ,
    MOCK_DETAIL_SWAY,
    MOCK_RELEASE_ALPHA,
    MOCK_SAMPLE_FPS,
    MOCK_SILENCE_BASE,
    MOCK_SILENCE_MAX_SEC,
    MOCK_SILENCE_MIN_SEC,
    MOCK_SILENCE_NOISE,
    MOCK_SPEAK_BASE,
    MOCK_SPEAK_MAX_SEC,
    MOCK_SPEAK_MIN_SEC,
    MOCK_SPEAK_NOISE,
    MOCK_SPEAK_SWAY,
    MOCK_SPEAK_SWAY_FREQ_HZ,
    SAMPLE_RATE,
)


class AudioSource(Protocol):
    """Contract used by the waveform widget to consume amplitude data."""

    def start(self) -> None:
        """Start producing normalized amplitude values."""

    def stop(self) -> None:
        """Stop producing data and release resources."""

    def get_buffer(self) -> Deque[float]:
        """Return the underlying ring buffer."""


class MockSource:
    """Mock generator using sine waves + random noise for desktop testing."""

    def __init__(
        self, amplitudes: Deque[float], sample_fps: float = MOCK_SAMPLE_FPS
    ) -> None:
        self._amplitudes = amplitudes
        self._sample_fps = sample_fps
        self._running = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_speaking = True
        self._remaining_ticks = 0
        self._smoothed_level = MOCK_SILENCE_BASE

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._running.set()
        self._thread = threading.Thread(
            target=self._run, name="mock-audio-source", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def get_buffer(self) -> Deque[float]:
        return self._amplitudes

    def _run(self) -> None:
        interval = 1.0 / self._sample_fps
        t = 0.0

        # Start with a fresh speaking/silence segment duration.
        self._reset_segment_ticks()

        while self._running.is_set():
            self._remaining_ticks -= 1
            if self._remaining_ticks <= 0:
                self._is_speaking = not self._is_speaking
                self._reset_segment_ticks()

            target = self._build_target_level(t)
            self._smoothed_level = self._smooth_level(self._smoothed_level, target)
            self._amplitudes.append(self._clamp01(self._smoothed_level))

            t += interval
            time.sleep(interval)

    def _build_target_level(self, t: float) -> float:
        if self._is_speaking:
            # Speaking section has wide envelope and mid/high details.
            sway = MOCK_SPEAK_SWAY * math.sin(
                2.0 * math.pi * MOCK_SPEAK_SWAY_FREQ_HZ * t
            )
            detail = MOCK_DETAIL_SWAY * math.sin(
                2.0 * math.pi * MOCK_DETAIL_FREQ_HZ * t
            )
            noise = random.uniform(-MOCK_SPEAK_NOISE, MOCK_SPEAK_NOISE)
            return self._clamp01(MOCK_SPEAK_BASE + sway + detail + noise)

        # Silence section stays near floor with tiny residual noise.
        noise = random.uniform(-MOCK_SILENCE_NOISE, MOCK_SILENCE_NOISE)
        return self._clamp01(MOCK_SILENCE_BASE + noise)

    def _reset_segment_ticks(self) -> None:
        if self._is_speaking:
            duration = random.uniform(MOCK_SPEAK_MIN_SEC, MOCK_SPEAK_MAX_SEC)
        else:
            duration = random.uniform(MOCK_SILENCE_MIN_SEC, MOCK_SILENCE_MAX_SEC)
        self._remaining_ticks = max(1, int(duration * self._sample_fps))

    @staticmethod
    def _smooth_level(current: float, target: float) -> float:
        # Faster attack keeps speech peaks responsive, slower release avoids flicker.
        alpha = MOCK_ATTACK_ALPHA if target > current else MOCK_RELEASE_ALPHA
        return current + (target - current) * alpha

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, value))


class MicrophoneSource:
    """Android microphone source based on AudioRecord through pyjnius."""

    def __init__(
        self, amplitudes: Deque[float], sample_fps: float = MIC_SAMPLE_FPS
    ) -> None:
        self._amplitudes = amplitudes
        self._sample_fps = sample_fps
        self._running = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Lazy-loaded Android objects (initialized only on Android runtime).
        self._recorder = None
        self._buffer_size = 0

    def start(self) -> None:
        if platform != "android":
            raise RuntimeError("MicrophoneSource is only available on Android")
        if self._thread and self._thread.is_alive():
            return

        self._setup_recorder()
        self._running.set()
        self._thread = threading.Thread(
            target=self._run, name="android-mic-source", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._release_recorder()

    def get_buffer(self) -> Deque[float]:
        return self._amplitudes

    def _setup_recorder(self) -> None:
        from jnius import autoclass

        AudioRecord = autoclass("android.media.AudioRecord")
        AudioFormat = autoclass("android.media.AudioFormat")
        MediaRecorder_AudioSource = autoclass("android.media.MediaRecorder$AudioSource")

        channel = AudioFormat.CHANNEL_IN_MONO
        encoding = AudioFormat.ENCODING_PCM_16BIT
        self._buffer_size = AudioRecord.getMinBufferSize(SAMPLE_RATE, channel, encoding)
        if self._buffer_size <= 0:
            raise RuntimeError("AudioRecord.getMinBufferSize returned invalid size")

        self._recorder = AudioRecord(
            MediaRecorder_AudioSource.MIC,
            SAMPLE_RATE,
            channel,
            encoding,
            self._buffer_size,
        )
        self._recorder.startRecording()

    def _release_recorder(self) -> None:
        if self._recorder is None:
            return
        try:
            self._recorder.stop()
        except Exception:
            pass
        try:
            self._recorder.release()
        except Exception:
            pass
        self._recorder = None

    def _run(self) -> None:
        from jnius import autoclass

        Array = autoclass("java.lang.reflect.Array")
        Short = autoclass("java.lang.Short")

        chunk_size = max(1, int(SAMPLE_RATE / self._sample_fps))

        # Pyjnius cannot mutate pure Python arrays when passed to Java out-parameters.
        # We must explicitly create a Java short[] using reflection.
        j_short_array = Array.newInstance(Short.TYPE, chunk_size)

        while self._running.is_set() and self._recorder is not None:
            read_count = self._recorder.read(j_short_array, 0, chunk_size)
            if read_count <= 0:
                continue

            # Calculate RMS from 16-bit PCM samples and normalize into [0, 1].
            acc = 0.0
            for i in range(read_count):
                sample = float(Array.getShort(j_short_array, i))
                acc += sample * sample
            rms = math.sqrt(acc / read_count)
            normalized = min(rms / MAX_EXPECTED_RMS, 1.0)
            self._amplitudes.append(normalized)


def build_audio_source(use_mock: bool, amplitudes: Deque[float]) -> AudioSource:
    """Factory that selects Android mic or mock source based on runtime."""
    if use_mock or platform != "android":
        return MockSource(amplitudes)
    return MicrophoneSource(amplitudes)
