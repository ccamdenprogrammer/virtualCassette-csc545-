"""
Tests for the echo processor component.
"""

import numpy as np
import pytest

from realtime_audio_fx.dsp.echo import EchoProcessor


class TestEchoProcessor:
    """Tests for EchoProcessor class."""

    def test_init(self):
        """Test echo processor initialization."""
        processor = EchoProcessor(44100, 2)
        assert processor.sample_rate == 44100
        assert processor.channels == 2

    def test_bypass_returns_input(self):
        """Test that bypass returns input unchanged."""
        processor = EchoProcessor(44100, 2)
        block = np.random.randn(512, 2).astype(np.float32)

        output = processor.process(
            block, mix=0.5, delay_ms=100, feedback=0.5, bypass=True
        )

        np.testing.assert_array_equal(output, block)

    def test_zero_mix_returns_input(self):
        """Test that zero mix returns input unchanged."""
        processor = EchoProcessor(44100, 2)
        block = np.random.randn(512, 2).astype(np.float32)

        output = processor.process(
            block, mix=0.0, delay_ms=100, feedback=0.5
        )

        np.testing.assert_array_equal(output, block)

    def test_output_shape_preserved(self):
        """Test that output shape matches input."""
        processor = EchoProcessor(44100, 2)
        block = np.random.randn(512, 2).astype(np.float32)

        output = processor.process(
            block, mix=0.5, delay_ms=100, feedback=0.5
        )

        assert output.shape == block.shape

    def test_delayed_signal(self):
        """Test that echo produces delayed signal."""
        processor = EchoProcessor(44100, 2)

        # Create impulse
        block1 = np.zeros((512, 2), dtype=np.float32)
        block1[0, :] = 1.0

        # Use short delay that fits within a few blocks
        delay_ms = 20  # 20ms = ~882 samples at 44100Hz

        # Process with echo
        output1 = processor.process(
            block1, mix=0.5, delay_ms=delay_ms, feedback=0.5
        )

        # Process more blocks to see echo appear
        total_energy = np.sum(np.abs(output1))
        for _ in range(5):
            block = np.zeros((512, 2), dtype=np.float32)
            output = processor.process(
                block, mix=1.0, delay_ms=delay_ms, feedback=0.5
            )
            total_energy += np.sum(np.abs(output))

        # There should be energy in the output due to delayed signal
        assert total_energy > 0.1

    def test_feedback_increases_tail(self):
        """Test that higher feedback creates longer tail."""
        delay_ms = 10  # Short delay to fit in blocks

        # Process with low feedback
        proc_low = EchoProcessor(44100, 2)
        impulse = np.zeros((256, 2), dtype=np.float32)
        impulse[0, :] = 1.0

        proc_low.process(impulse.copy(), mix=1.0, delay_ms=delay_ms, feedback=0.1)

        # Process several more blocks
        energy_low = 0
        for _ in range(20):
            block = np.zeros((256, 2), dtype=np.float32)
            out = proc_low.process(block, mix=1.0, delay_ms=delay_ms, feedback=0.1)
            energy_low += np.sum(np.abs(out))

        # Process with high feedback
        proc_high = EchoProcessor(44100, 2)
        proc_high.process(impulse.copy(), mix=1.0, delay_ms=delay_ms, feedback=0.8)

        energy_high = 0
        for _ in range(20):
            block = np.zeros((256, 2), dtype=np.float32)
            out = proc_high.process(block, mix=1.0, delay_ms=delay_ms, feedback=0.8)
            energy_high += np.sum(np.abs(out))

        # High feedback should have more energy in tail
        assert energy_high > energy_low

    def test_reset_clears_buffer(self):
        """Test that reset clears the delay buffer."""
        processor = EchoProcessor(44100, 2)

        # Fill buffer with signal
        block = np.ones((512, 2), dtype=np.float32)
        processor.process(block, mix=0.5, delay_ms=100, feedback=0.9)

        # Reset
        processor.reset()

        # Next output should be clean
        zeros = np.zeros((512, 2), dtype=np.float32)
        output = processor.process(zeros, mix=1.0, delay_ms=100, feedback=0.5)

        # Should be all zeros (or very close)
        assert np.allclose(output, 0, atol=1e-6)

    def test_state_persists_across_blocks(self):
        """Test that delay state persists across blocks."""
        processor = EchoProcessor(44100, 2)

        # Send impulse
        impulse = np.zeros((256, 2), dtype=np.float32)
        impulse[0, :] = 1.0
        processor.process(impulse, mix=0.5, delay_ms=100, feedback=0.5)

        # Check that subsequent blocks have signal
        silence = np.zeros((256, 2), dtype=np.float32)
        has_energy = False
        for _ in range(20):
            output = processor.process(
                silence, mix=0.5, delay_ms=100, feedback=0.5
            )
            if np.max(np.abs(output)) > 0.01:
                has_energy = True
                break

        assert has_energy

    def test_no_nan_output(self):
        """Test that output contains no NaN values."""
        processor = EchoProcessor(44100, 2)
        block = np.random.randn(512, 2).astype(np.float32)

        output = processor.process(
            block, mix=0.5, delay_ms=100, feedback=0.5
        )

        assert not np.any(np.isnan(output))

    def test_feedback_stability(self):
        """Test that high feedback doesn't cause runaway."""
        processor = EchoProcessor(44100, 2)

        # Process many blocks with high feedback
        for _ in range(100):
            block = np.random.randn(512, 2).astype(np.float32) * 0.1
            output = processor.process(
                block, mix=0.5, delay_ms=50, feedback=0.89
            )
            # Output should stay bounded
            assert np.all(np.abs(output) < 10)

    def test_varying_delay(self):
        """Test changing delay time during processing."""
        processor = EchoProcessor(44100, 2)

        for delay in [50, 100, 200, 500]:
            block = np.random.randn(512, 2).astype(np.float32)
            output = processor.process(
                block, mix=0.5, delay_ms=delay, feedback=0.5
            )
            assert output.shape == block.shape
            assert not np.any(np.isnan(output))
