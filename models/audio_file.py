"""
Audio file model representing loaded audio data.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


@dataclass
class AudioFile:
    """
    Represents a loaded audio file with normalized float32 data.

    Audio data is always stored as:
    - dtype: float32
    - range: [-1.0, 1.0]
    - shape: (frames, channels) where channels is 1 or 2
    """
    path: Path
    original_sample_rate: int
    sample_rate: int  # May differ if resampled to engine rate
    channel_count: int
    total_frames: int
    data: np.ndarray  # Shape: (frames, channels), dtype: float32

    @property
    def filename(self) -> str:
        """Get the filename without path."""
        return self.path.name

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds at current sample rate."""
        if self.sample_rate <= 0:
            return 0.0
        return self.total_frames / self.sample_rate

    @property
    def original_duration_seconds(self) -> float:
        """Get original duration before any resampling."""
        if self.original_sample_rate <= 0:
            return 0.0
        return self.total_frames / self.original_sample_rate

    @property
    def is_mono(self) -> bool:
        """Check if audio is mono."""
        return self.channel_count == 1

    @property
    def is_stereo(self) -> bool:
        """Check if audio is stereo."""
        return self.channel_count == 2

    def get_metadata_string(self) -> str:
        """Get a formatted string of file metadata."""
        channels_str = "Mono" if self.is_mono else "Stereo"
        duration_str = f"{self.duration_seconds:.2f}s"
        sr_str = f"{self.sample_rate} Hz"

        info = f"{self.filename} | {channels_str} | {sr_str} | {duration_str}"

        if self.original_sample_rate != self.sample_rate:
            info += f" (resampled from {self.original_sample_rate} Hz)"

        return info
