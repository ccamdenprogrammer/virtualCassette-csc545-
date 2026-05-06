"""
Block processor for chaining DSP effects in real-time.

Processes audio blocks through the effect chain:
Source -> Speed -> Echo -> Gain -> Limiter
"""

import numpy as np
from typing import Optional

from models.parameters import ParameterStore, EffectParameters
from dsp.echo import EchoProcessor
from dsp.utils import db_to_linear
from .source_reader import SourceReader
import config


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
        channels: int,
        file_id: str
    ):
        """
        Initialize block processor.

        Args:
            source_reader: Source reader for audio data
            parameter_store: Thread-safe parameter store
            sample_rate: Audio sample rate
            channels: Number of audio channels
            file_id: ID of the audio file this processor handles
        """
        self.source_reader = source_reader
        self.parameter_store = parameter_store
        self.sample_rate = sample_rate
        self.channels = channels
        self.file_id = file_id

        # Initialize DSP processors
        self.echo_processor = EchoProcessor(
            sample_rate,
            channels,
            max_delay_ms=config.MAX_ECHO_BUFFER_MS
        )

        # Smoothed parameter values
        self._smooth_speed = config.DEFAULT_SPEED
        self._smooth_gain = np.array(
            [
                db_to_linear(config.DEFAULT_OUTPUT_GAIN_LEFT_DB),
                db_to_linear(config.DEFAULT_OUTPUT_GAIN_RIGHT_DB),
            ],
            dtype=np.float32,
        )
        self._smooth_track_volume = config.DEFAULT_TRACK_VOLUME

        # Smoothing coefficient
        self._alpha = config.PARAM_SMOOTHING_ALPHA

    def reset(self) -> None:
        """Reset all processor state."""
        self.source_reader.reset()
        self.echo_processor.reset()

        # Reset smoothed values
        self._smooth_speed = config.DEFAULT_SPEED
        self._smooth_gain = np.array(
            [
                db_to_linear(config.DEFAULT_OUTPUT_GAIN_LEFT_DB),
                db_to_linear(config.DEFAULT_OUTPUT_GAIN_RIGHT_DB),
            ],
            dtype=np.float32,
        )
        self._smooth_track_volume = config.DEFAULT_TRACK_VOLUME

    def process(self, output_frames: int) -> np.ndarray:
        """
        Process one block of audio through the effect chain.

        Args:
            output_frames: Number of frames to generate

        Returns:
            Processed audio block (output_frames, channels)
        """
        # Get current parameter snapshot
        params = self.parameter_store.get_snapshot_for_file(self.file_id)

        # Apply parameter smoothing
        target_speed = params.speed if not params.bypass_speed else 1.0
        self._smooth_speed += self._alpha * (target_speed - self._smooth_speed)

        target_gain = np.array(
            [
                db_to_linear(params.output_gain_left_db),
                db_to_linear(params.output_gain_right_db),
            ],
            dtype=np.float32,
        )
        self._smooth_gain += self._alpha * (target_gain - self._smooth_gain)

        target_track_volume = np.clip(
            params.track_volume,
            config.TRACK_VOLUME_MIN,
            config.TRACK_VOLUME_MAX,
        )
        self._smooth_track_volume += self._alpha * (
            target_track_volume - self._smooth_track_volume
        )

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
        if block.ndim == 2 and block.shape[1] > 1:
            block = block * self._smooth_track_volume * self._smooth_gain[: block.shape[1]]
        else:
            block = block * self._smooth_track_volume * self._smooth_gain[0]

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
