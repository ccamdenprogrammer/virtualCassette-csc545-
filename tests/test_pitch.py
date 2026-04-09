"""
Tests for the pitch processor component.
"""

import numpy as np
import pytest

from realtime_audio_fx.dsp.pitch import PitchProcessor


class TestPitchProcessor:
    """Tests for PitchProcessor class."""

    def test_init(self):
        """Test pitch processor initialization."""
        processor = PitchProcessor(44100, 2)
        assert processor.sample_rate == 44100
        assert processor.channels == 2

    def test_bypass_returns_input(self):
        """Test that bypass returns input unchanged."""
        processor = PitchProcessor(44100, 2)
        block = np.random.randn(512, 2).astype(np.float32)

        output = processor.process(block, semitones=5.0, bypass=True)

        np.testing.assert_array_equal(output, block)

    def test_zero_semitones_returns_input(self):
        """Test that zero semitones returns input unchanged."""
        processor = PitchProcessor(44100, 2)
        block = np.random.randn(512, 2).astype(np.float32)

        output = processor.process(block, semitones=0.0)

        np.testing.assert_array_equal(output, block)

    def test_output_shape_preserved(self):
        """Test that output shape matches input."""
        processor = PitchProcessor(44100, 2)
        block = np.random.randn(512, 2).astype(np.float32)

        output = processor.process(block, semitones=5.0)

        assert output.shape == block.shape

    def test_pitch_up_changes_signal(self):
        """Test that pitch up materially changes the signal."""
        processor = PitchProcessor(44100, 2)

        # Create sine wave with more cycles for visible pitch change
        t = np.linspace(0, 2 * np.pi * 20, 1024)
        block = np.column_stack([np.sin(t), np.sin(t)]).astype(np.float32)

        # Process first to fill context buffer
        processor.process(block.copy(), semitones=12.0)

        # Process again - should show pitch effect
        output = processor.process(block.copy(), semitones=12.0)

        # Compare RMS of differences - pitch shift should create some difference
        diff = np.abs(output - block)
        max_diff = np.max(diff)

        # With 12 semitones (octave), waveform should differ
        assert max_diff > 0.01 or not np.allclose(output[:100], block[:100], atol=0.05)

    def test_pitch_down_changes_signal(self):
        """Test that pitch down materially changes the signal."""
        processor = PitchProcessor(44100, 2)

        t = np.linspace(0, 2 * np.pi * 20, 1024)
        block = np.column_stack([np.sin(t), np.sin(t)]).astype(np.float32)

        # Process first to fill context buffer
        processor.process(block.copy(), semitones=-12.0)

        # Process again
        output = processor.process(block.copy(), semitones=-12.0)

        # Compare differences
        diff = np.abs(output - block)
        max_diff = np.max(diff)

        assert max_diff > 0.01 or not np.allclose(output[:100], block[:100], atol=0.05)

    def test_no_nan_output(self):
        """Test that output contains no NaN values."""
        processor = PitchProcessor(44100, 2)
        block = np.random.randn(512, 2).astype(np.float32)

        for semitones in [-12, -6, -1, 1, 6, 12]:
            output = processor.process(block, semitones=semitones)
            assert not np.any(np.isnan(output))

    def test_no_inf_output(self):
        """Test that output contains no infinite values."""
        processor = PitchProcessor(44100, 2)
        block = np.random.randn(512, 2).astype(np.float32)

        for semitones in [-12, -6, -1, 1, 6, 12]:
            output = processor.process(block, semitones=semitones)
            assert not np.any(np.isinf(output))

    def test_reset(self):
        """Test reset functionality."""
        processor = PitchProcessor(44100, 2)

        # Process some blocks
        block = np.random.randn(512, 2).astype(np.float32)
        processor.process(block, semitones=5.0)

        # Reset
        processor.reset()

        # Should work without error
        output = processor.process(block, semitones=5.0)
        assert output.shape == block.shape

    def test_consecutive_blocks(self):
        """Test processing consecutive blocks maintains stability."""
        processor = PitchProcessor(44100, 2)

        for _ in range(10):
            block = np.random.randn(512, 2).astype(np.float32)
            output = processor.process(block, semitones=5.0)
            assert output.shape == block.shape
            assert not np.any(np.isnan(output))

    def test_varying_pitch_values(self):
        """Test with varying pitch values during processing."""
        processor = PitchProcessor(44100, 2)

        for semitones in np.linspace(-12, 12, 20):
            block = np.random.randn(512, 2).astype(np.float32)
            output = processor.process(block, semitones=semitones)
            assert output.shape == block.shape
            assert not np.any(np.isnan(output))
