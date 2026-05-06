"""
Audio exporter service for offline rendering with effects.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

import numpy as np
import soundfile as sf

import config

if TYPE_CHECKING:
    from models import AudioFile, EffectParameters

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
        audio_files: list["AudioFile"],
        params_dict: dict[str, "EffectParameters"],
        output_path: str | Path,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Path:
        """
        Export mixed audio with current effect settings for all files.

        Args:
            audio_files: List of source audio files
            params_dict: Dict of file_id -> EffectParameters
            output_path: Path for output file
            progress_callback: Optional callback for progress updates (0.0-1.0)

        Returns:
            Path to exported file

        Raises:
            ExportError: If export fails
        """
        from engine.source_reader import SourceReader
        from dsp.echo import EchoProcessor
        from dsp.utils import db_to_linear

        output_path = Path(output_path)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not audio_files:
            raise ExportError("No audio files to export")

        # Assume all files have same sample rate and channels
        sample_rate = audio_files[0].sample_rate
        channels = audio_files[0].channel_count

        try:
            # Create DSP processors for each file
            source_readers = {}
            echo_procs = {}
            
            for audio_file in audio_files:
                file_id = audio_file.id
                params = params_dict.get(file_id)
                if not params:
                    continue  # Skip if no params
                
                source_readers[file_id] = SourceReader(
                    audio_file.data,
                    audio_file.total_frames,
                    loop_enabled=False
                )
                
                echo_procs[file_id] = EchoProcessor(
                    sample_rate,
                    channels,
                    max_delay_ms=config.MAX_ECHO_BUFFER_MS
                )

            # Calculate max duration
            max_frames = max(f.total_frames for f in audio_files)
            tail_frames = int(config.EXPORT_TAIL_SECONDS * sample_rate)
            total_frames = max_frames + tail_frames

            logger.info(f"Exporting {len(audio_files)} files to {output_path}")
            logger.info(f"Estimated duration: {total_frames / sample_rate:.2f}s")

            # Open output file for streaming write
            with sf.SoundFile(
                str(output_path),
                mode="w",
                samplerate=sample_rate,
                channels=channels,
                format="WAV",
                subtype="FLOAT",
            ) as outfile:

                frames_written = 0
                sources_exhausted = {fid: False for fid in source_readers}

                while frames_written < total_frames:
                    # Mix block from all sources
                    mixed_block = np.zeros((self.block_size, channels), dtype=np.float32)
                    
                    for file_id, source_reader in source_readers.items():
                        params = params_dict[file_id]
                        echo_proc = echo_procs[file_id]
                        
                        # Read block from source
                        if not sources_exhausted[file_id]:
                            effective_speed = params.speed if not params.bypass_speed else 1.0
                            block, exhausted = source_reader.read(
                                self.block_size,
                                effective_speed
                            )
                            if exhausted:
                                sources_exhausted[file_id] = True
                        else:
                            # Generate silence for tail rendering
                            block = np.zeros((self.block_size, channels), dtype=np.float32)

                        # Apply echo
                        block = echo_proc.process(
                            block,
                            params.echo_mix,
                            params.echo_delay_ms,
                            params.echo_feedback,
                            bypass=params.bypass_echo
                        )

                        # Apply gain
                        gain = np.array(
                            [
                                db_to_linear(params.output_gain_left_db),
                                db_to_linear(params.output_gain_right_db),
                            ],
                            dtype=np.float32,
                        )
                        track_volume = np.clip(
                            params.track_volume,
                            config.TRACK_VOLUME_MIN,
                            config.TRACK_VOLUME_MAX,
                        )
                        if block.ndim == 2 and block.shape[1] > 1:
                            block = block * track_volume * gain[: block.shape[1]]
                        else:
                            block = block * track_volume * gain[0]
                        
                        # Add to mix
                        mixed_block += block

                    # Clip final mix
                    mixed_block = np.clip(mixed_block, -1.0, 1.0)

                    # Write to file
                    outfile.write(mixed_block)
                    frames_written += len(mixed_block)

                    # Progress callback
                    if progress_callback:
                        progress = min(1.0, frames_written / total_frames)
                        progress_callback(progress)

            logger.info(f"Export complete: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise ExportError(f"Failed to export audio: {e}")
