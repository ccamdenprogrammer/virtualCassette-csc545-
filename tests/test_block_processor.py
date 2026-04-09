"""
Tests for the block processor component.
"""

import numpy as np
import pytest

from realtime_audio_fx.models.parameters import ParameterStore
from realtime_audio_fx.engine.source_reader import SourceReader
from realtime_audio_fx.engine.block_processor import BlockProcessor


class TestBlockProcessor:
    """Tests for BlockProcessor class."""

    @pytest.fixture
    def setup(self):
        """Create test fixtures."""
        # Create test audio
        audio = np.random.randn(10000, 2).astype(np.float32) * 0.5
        source_reader = SourceReader(audio, 10000, loop_enabled=False)
        param_store = ParameterStore()

        processor = BlockProcessor(
            source_reader=source_reader,
            parameter_store=param_store,
            sample_rate=44100,
            channels=2,
        )

        return processor, param_store

    def test_process_output_shape(self, setup):
        """Test that process returns correct shape."""
        processor, _ = setup

        output = processor.process(512)

        assert output.shape == (512, 2)

    def test_process_output_dtype(self, setup):
        """Test that process returns float32."""
        processor, _ = setup

        output = processor.process(512)

        assert output.dtype == np.float32

    def test_process_clipped_output(self, setup):
        """Test that output is clipped to valid range."""
        processor, param_store = setup

        # Set high gain
        param_store.update(output_gain_db=20.0)

        output = processor.process(512)

        assert np.all(output >= -1.0)
        assert np.all(output <= 1.0)

    def test_speed_affects_playback(self, setup):
        """Test that speed parameter affects playback rate."""
        processor1, param_store1 = setup

        # Create another processor for comparison
        audio = np.random.randn(10000, 2).astype(np.float32) * 0.5
        source_reader2 = SourceReader(audio, 10000, loop_enabled=False)
        param_store2 = ParameterStore()
        processor2 = BlockProcessor(
            source_reader=source_reader2,
            parameter_store=param_store2,
            sample_rate=44100,
            channels=2,
        )

        # Set different speeds
        param_store1.update(speed=1.0)
        param_store2.update(speed=2.0)

        # Process same number of blocks
        for _ in range(10):
            processor1.process(512)
            processor2.process(512)

        # Fast playback should have advanced further
        assert processor2.get_position() > processor1.get_position()

    def test_reset(self, setup):
        """Test reset functionality."""
        processor, _ = setup

        # Process some blocks
        for _ in range(5):
            processor.process(512)

        assert processor.get_position() > 0

        # Reset
        processor.reset()

        assert processor.get_position() == 0

    def test_source_exhaustion(self, setup):
        """Test source exhaustion detection."""
        # Create short audio
        audio = np.random.randn(1000, 2).astype(np.float32)
        source_reader = SourceReader(audio, 1000, loop_enabled=False)
        param_store = ParameterStore()

        processor = BlockProcessor(
            source_reader=source_reader,
            parameter_store=param_store,
            sample_rate=44100,
            channels=2,
        )

        # Process until exhausted
        for _ in range(10):
            processor.process(512)
            if processor.is_source_exhausted():
                break

        assert processor.is_source_exhausted()

    def test_no_nan_output(self, setup):
        """Test that output never contains NaN."""
        processor, param_store = setup

        # Apply various effects
        param_store.update(
            pitch_semitones=5.0,
            echo_mix=0.5,
            reverb_mix=0.5,
        )

        for _ in range(20):
            output = processor.process(512)
            assert not np.any(np.isnan(output))

    def test_varying_block_sizes(self, setup):
        """Test processing with various block sizes."""
        processor, _ = setup

        for block_size in [128, 256, 512, 1024]:
            output = processor.process(block_size)
            assert output.shape == (block_size, 2)
            assert not np.any(np.isnan(output))
