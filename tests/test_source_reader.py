"""
Tests for the source reader component.
"""

import numpy as np
import pytest

from realtime_audio_fx.engine.source_reader import SourceReader


class TestSourceReader:
    """Tests for SourceReader class."""

    def test_init(self):
        """Test source reader initialization."""
        audio = np.random.randn(1000, 2).astype(np.float32)
        reader = SourceReader(audio, 1000, loop_enabled=False)

        assert reader.total_frames == 1000
        assert reader.loop_enabled is False
        assert reader.get_position() == 0
        assert reader.is_exhausted() is False

    def test_read_speed_1(self):
        """Test reading at normal speed."""
        # Create simple ramp audio
        audio = np.arange(1000).reshape(-1, 1).astype(np.float32)
        audio = np.column_stack([audio, audio])  # Stereo
        reader = SourceReader(audio, 1000, loop_enabled=False)

        block, exhausted = reader.read(100, speed=1.0)

        assert block.shape == (100, 2)
        assert not exhausted
        assert reader.get_position() == 100

    def test_read_speed_2(self):
        """Test reading at double speed."""
        audio = np.arange(1000).reshape(-1, 1).astype(np.float32)
        audio = np.column_stack([audio, audio])
        reader = SourceReader(audio, 1000, loop_enabled=False)

        block, exhausted = reader.read(100, speed=2.0)

        assert block.shape == (100, 2)
        # At speed 2, we should have advanced ~200 frames
        assert reader.get_position() >= 199

    def test_read_speed_half(self):
        """Test reading at half speed."""
        audio = np.arange(1000).reshape(-1, 1).astype(np.float32)
        audio = np.column_stack([audio, audio])
        reader = SourceReader(audio, 1000, loop_enabled=False)

        block, exhausted = reader.read(100, speed=0.5)

        assert block.shape == (100, 2)
        # At speed 0.5, we should have advanced ~50 frames
        assert reader.get_position() <= 51

    def test_loop_enabled(self):
        """Test looping behavior."""
        audio = np.random.randn(100, 2).astype(np.float32)
        reader = SourceReader(audio, 100, loop_enabled=True)

        # Read more than file length
        for _ in range(5):
            block, exhausted = reader.read(50, speed=1.0)
            assert not exhausted
            assert block.shape == (50, 2)

    def test_no_loop_exhaustion(self):
        """Test exhaustion when not looping."""
        audio = np.random.randn(100, 2).astype(np.float32)
        reader = SourceReader(audio, 100, loop_enabled=False)

        # Read until exhausted
        exhausted = False
        for _ in range(10):
            block, exhausted = reader.read(50, speed=1.0)
            if exhausted:
                break

        assert exhausted
        assert reader.is_exhausted()

    def test_reset(self):
        """Test reset functionality."""
        audio = np.random.randn(100, 2).astype(np.float32)
        reader = SourceReader(audio, 100, loop_enabled=False)

        # Read some data
        reader.read(50, speed=1.0)
        assert reader.get_position() > 0

        # Reset
        reader.reset()
        assert reader.get_position() == 0
        assert not reader.is_exhausted()

    def test_set_position(self):
        """Test setting playhead position."""
        audio = np.random.randn(100, 2).astype(np.float32)
        reader = SourceReader(audio, 100, loop_enabled=False)

        reader.set_position(50)
        assert reader.get_position() == 50

    def test_interpolation_quality(self):
        """Test that interpolation produces smooth output."""
        # Create sine wave
        t = np.linspace(0, 4 * np.pi, 1000)
        audio = np.sin(t).reshape(-1, 1).astype(np.float32)
        audio = np.column_stack([audio, audio])

        reader = SourceReader(audio, 1000, loop_enabled=False)

        # Read at fractional speed
        block, _ = reader.read(200, speed=1.5)

        # Output should still look like a sine wave (no NaN, reasonable range)
        assert not np.any(np.isnan(block))
        assert np.all(np.abs(block) <= 1.1)  # Allow slight overshoot from interp

    def test_mono_audio(self):
        """Test reading mono audio."""
        audio = np.random.randn(100, 1).astype(np.float32)
        reader = SourceReader(audio, 100, loop_enabled=False)

        block, _ = reader.read(50, speed=1.0)
        assert block.shape == (50, 1)
