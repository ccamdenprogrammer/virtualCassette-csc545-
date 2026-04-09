"""
Block processor for chaining DSP effects in real-time.

Processes audio blocks through the effect chain:
Source -> Speed -> Echo -> Gain -> Limiter
"""

import numpy as np
from typing import Optional

from ..models.parameters import ParameterStore, EffectParameters
from ..dsp.echo import EchoProcessor
from ..dsp.utils import db_to_linear
from .source_reader import SourceReader
from .. import config


class BlockProcessor:
    """
    Processes audio blocks through the complete DSP effect chain.

    Handles parameter smoothing and effect chaining for real-time playback.
    """

    def __init__(
        self,
        source_reader: SourceReader,
        parameter_store: ParameterStore,
        sample_rate: int,
        channels: int
    ):
        """
        Initialize block processor.

        Args:
            source_reader: Source reader for audio data
            parameter_store: Thread-safe parameter store
            sample_rate: Audio sample rate
            channels: Number of audio channels
        """
        self.source_reader = source_reader
        self.parameter_store = parameter_store
        self.sample_rate = sample_rate
        self.channels = channels

        # Initialize DSP processors
        self.echo_processor = EchoProcessor(
            sample_rate,
            channels,
            max_delay_ms=config.MAX_ECHO_BUFFER_MS
        )

        # Smoothed parameter values
        self._smooth_speed = config.DEFAULT_SPEED
        self._smooth_gain = db_to_linear(config.DEFAULT_OUTPUT_GAIN_DB)

        # Smoothing coefficient
        self._alpha = config.PARAM_SMOOTHING_ALPHA

    def reset(self) -> None:
        """Reset all processor state."""
        self.source_reader.reset()
        self.echo_processor.reset()

        # Reset smoothed values
        self._smooth_speed = config.DEFAULT_SPEED
        self._smooth_gain = db_to_linear(config.DEFAULT_OUTPUT_GAIN_DB)

    def process(self, output_frames: int) -> np.ndarray:
        """
        Process one block of audio through the effect chain.

        Args:
            output_frames: Number of frames to generate

        Returns:
            Processed audio block (output_frames, channels)
        """
        # Get current parameter snapshot
        params = self.parameter_store.get_snapshot()

        # Apply parameter smoothing
        target_speed = params.speed if not params.bypass_speed else 1.0
        self._smooth_speed += self._alpha * (target_speed - self._smooth_speed)

        target_gain = db_to_linear(params.output_gain_db)
        self._smooth_gain += self._alpha * (target_gain - self._smooth_gain)

        # Read from source with speed control
        block, exhausted = self.source_reader.read(output_frames, self._smooth_speed)

        # Apply echo
        block = self.echo_processor.process(
            block,
            mix=params.echo_mix,
            delay_ms=params.echo_delay_ms,
            feedback=params.echo_feedback,
            bypass=params.bypass_echo
        )

        # Apply output gain
        block = block * self._smooth_gain

        # Final hard clip to prevent output clipping
        block = np.clip(block, -1.0, 1.0)

        return block.astype(np.float32)

    def is_source_exhausted(self) -> bool:
        """Check if source audio has been fully played."""
        return self.source_reader.is_exhausted()

    def get_position(self) -> int:
        """Get current playhead position in frames."""
        return self.source_reader.get_position()

    def set_position(self, frame: int) -> None:
        """Set playhead position."""
        self.source_reader.set_position(frame)
