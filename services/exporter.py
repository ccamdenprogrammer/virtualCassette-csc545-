"""
Audio exporter service for offline rendering with effects.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

import numpy as np
import soundfile as sf

from .. import config

if TYPE_CHECKING:
    from ..models import AudioFile, EffectParameters

logger = logging.getLogger(__name__)


class ExportError(Exception):
    """Exception raised for export errors."""
    pass


class Exporter:
    """
    Service for exporting processed audio to disk.

    Renders audio offline using the same DSP chain as live playback,
    ensuring export matches what the user heard.
    """

    def __init__(self, sample_rate: int, block_size: int = 1024):
        """
        Initialize exporter.

        Args:
            sample_rate: Sample rate for exported audio
            block_size: Block size for offline rendering
        """
        self.sample_rate = sample_rate
        self.block_size = block_size

    def export(
        self,
        audio_file: "AudioFile",
        params: "EffectParameters",
        output_path: str | Path,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Path:
        """
        Export audio with current effect settings.

        Args:
            audio_file: Source audio file
            params: Effect parameters to apply
            output_path: Path for output file
            progress_callback: Optional callback for progress updates (0.0-1.0)

        Returns:
            Path to exported file

        Raises:
            ExportError: If export fails
        """
        from ..engine.source_reader import SourceReader
        from ..dsp.echo import EchoProcessor
        from ..dsp.utils import db_to_linear

        output_path = Path(output_path)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Create fresh DSP processors for export
            source_reader = SourceReader(
                audio_file.data,
                audio_file.total_frames,
                loop_enabled=False
            )

            echo_proc = EchoProcessor(
                self.sample_rate,
                audio_file.channel_count,
                max_delay_ms=config.MAX_ECHO_BUFFER_MS
            )

            # Calculate effective speed
            effective_speed = params.speed if not params.bypass_speed else 1.0

            # Estimate total output frames
            source_frames = audio_file.total_frames
            estimated_output_frames = int(source_frames / effective_speed)

            # Add tail for effects
            tail_frames = int(config.EXPORT_TAIL_SECONDS * self.sample_rate)
            total_frames = estimated_output_frames + tail_frames

            # Gain multiplier
            gain = db_to_linear(params.output_gain_db)

            logger.info(f"Exporting to {output_path}")
            logger.info(f"Estimated duration: {total_frames / self.sample_rate:.2f}s")

            # Open output file for streaming write
            with sf.SoundFile(
                str(output_path),
                mode="w",
                samplerate=self.sample_rate,
                channels=audio_file.channel_count,
                format="WAV",
                subtype="FLOAT",
            ) as outfile:

                frames_written = 0
                source_exhausted = False

                while frames_written < total_frames:
                    # Read block from source
                    if not source_exhausted:
                        block, exhausted = source_reader.read(
                            self.block_size,
                            effective_speed
                        )
                        if exhausted:
                            source_exhausted = True
                    else:
                        # Generate silence for tail rendering
                        block = np.zeros(
                            (self.block_size, audio_file.channel_count),
                            dtype=np.float32
                        )

                    # Apply echo
                    block = echo_proc.process(
                        block,
                        params.echo_mix,
                        params.echo_delay_ms,
                        params.echo_feedback,
                        bypass=params.bypass_echo
                    )

                    # Apply gain and clip
                    block = block * gain
                    block = np.clip(block, -1.0, 1.0)

                    # Write to file
                    outfile.write(block)
                    frames_written += len(block)

                    # Progress callback
                    if progress_callback:
                        progress = min(1.0, frames_written / total_frames)
                        progress_callback(progress)

            logger.info(f"Export complete: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise ExportError(f"Failed to export audio: {e}")
