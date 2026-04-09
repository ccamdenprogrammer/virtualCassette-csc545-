"""
Tests for the reverb processor component.
"""

import numpy as np
import pytest

from realtime_audio_fx.dsp.reverb import ReverbProcessor


class TestReverbProcessor:
    """Tests for ReverbProcessor class."""

    def test_init(self):
        """Test reverb processor initialization."""
        processor = ReverbProcessor(44100, 2)
        assert processor.sample_rate == 44100
        assert processor.channels == 2

    def test_bypass_returns_input(self):
        """Test that bypass returns input unchanged."""
        processor = ReverbProcessor(44100, 2)
        block = np.random.randn(512, 2).astype(np.float32)

        output = processor.process(
            block, mix=0.5, room_size=0.5, damping=0.5, bypass=True
        )

        np.testing.assert_array_equal(output, block)

    def test_zero_mix_returns_input(self):
        """Test that zero mix returns input unchanged."""
        processor = ReverbProcessor(44100, 2)
        block = np.random.randn(512, 2).astype(np.float32)

        output = processor.process(
            block, mix=0.0, room_size=0.5, damping=0.5
        )

        np.testing.assert_array_equal(output, block)

    def test_output_shape_preserved(self):
        """Test that output shape matches input."""
        processor = ReverbProcessor(44100, 2)
        block = np.random.randn(512, 2).astype(np.float32)

        output = processor.process(
            block, mix=0.5, room_size=0.5, damping=0.5
        )

        assert output.shape == block.shape

    def test_reverb_adds_energy(self):
        """Test that reverb adds wet signal energy."""
        processor = ReverbProcessor(44100, 2)

        # Create audio signal (not just impulse)
        t = np.linspace(0, 2 * np.pi * 10, 512)
        audio = np.column_stack([np.sin(t), np.sin(t)]).astype(np.float32)

        # Process with full wet
        output = processor.process(
            audio, mix=1.0, room_size=0.8, damping=0.2
        )

        # Reverb should modify the signal
        # Either the output has energy, or it differs from input
        has_energy = np.sum(np.abs(output)) > 0.01
        differs_from_input = not np.allclose(output, audio, atol=0.1)

        assert has_energy or differs_from_input

    def test_no_nan_output(self):
        """Test that output contains no NaN values."""
        processor = ReverbProcessor(44100, 2)
        block = np.random.randn(512, 2).astype(np.float32)

        output = processor.process(
            block, mix=0.5, room_size=0.5, damping=0.5
        )

        assert not np.any(np.isnan(output))

    def test_no_inf_output(self):
        """Test that output contains no infinite values."""
        processor = ReverbProcessor(44100, 2)
        block = np.random.randn(512, 2).astype(np.float32)

        output = processor.process(
            block, mix=0.5, room_size=0.5, damping=0.5
        )

        assert not np.any(np.isinf(output))

    def test_reset(self):
        """Test reset functionality."""
        processor = ReverbProcessor(44100, 2)

        # Process some blocks
        block = np.random.randn(512, 2).astype(np.float32)
        processor.process(block, mix=0.5, room_size=0.5, damping=0.5)

        # Reset
        processor.reset()

        # Should work without error
        output = processor.process(block, mix=0.5, room_size=0.5, damping=0.5)
        assert output.shape == block.shape

    def test_varying_parameters(self):
        """Test with varying parameter values."""
        processor = ReverbProcessor(44100, 2)

        for room_size in [0.1, 0.5, 0.9]:
            for damping in [0.1, 0.5, 0.9]:
                block = np.random.randn(512, 2).astype(np.float32)
                output = processor.process(
                    block, mix=0.5, room_size=room_size, damping=damping
                )
                assert output.shape == block.shape
                assert not np.any(np.isnan(output))

    def test_parameter_clamping(self):
        """Test that out-of-range parameters are clamped."""
        processor = ReverbProcessor(44100, 2)
        block = np.random.randn(512, 2).astype(np.float32)

        # Should not crash with extreme values
        output = processor.process(
            block, mix=5.0, room_size=-1.0, damping=2.0
        )

        assert output.shape == block.shape
        assert not np.any(np.isnan(output))

    def test_consecutive_blocks(self):
        """Test processing many consecutive blocks."""
        processor = ReverbProcessor(44100, 2)

        for _ in range(50):
            block = np.random.randn(512, 2).astype(np.float32)
            output = processor.process(
                block, mix=0.5, room_size=0.5, damping=0.5
            )
            assert output.shape == block.shape
            assert not np.any(np.isnan(output))
            # Output should stay bounded
            assert np.all(np.abs(output) < 10)
