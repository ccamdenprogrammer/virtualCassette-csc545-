"""
Audio file loading service.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
from scipy import signal

from ..models.audio_file import AudioFile

logger = logging.getLogger(__name__)


class FileLoaderError(Exception):
    """Exception raised for file loading errors."""
    pass


class FileLoader:
    """
    Service for loading audio files and resampling to engine sample rate.
    """

    SUPPORTED_EXTENSIONS = {".wav", ".flac", ".ogg", ".mp3", ".aiff", ".aif"}

    def __init__(self, engine_sample_rate: int):
        """
        Initialize the file loader.

        Args:
            engine_sample_rate: Target sample rate for loaded audio
        """
        self.engine_sample_rate = engine_sample_rate

    def load(self, path: str | Path) -> AudioFile:
        """
        Load an audio file and resample if necessary.

        Args:
            path: Path to the audio file

        Returns:
            AudioFile with normalized float32 data

        Raises:
            FileLoaderError: If file cannot be loaded or is invalid
        """
        path = Path(path)

        # Validate file exists
        if not path.exists():
            raise FileLoaderError(f"File not found: {path}")

        # Validate extension
        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise FileLoaderError(
                f"Unsupported file format: {path.suffix}. "
                f"Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

        try:
            # Load audio with soundfile
            data, sample_rate = sf.read(str(path), always_2d=True, dtype="float32")
            logger.info(f"Loaded {path.name}: {data.shape}, {sample_rate} Hz")

        except Exception as e:
            raise FileLoaderError(f"Failed to read audio file: {e}")

        # Validate data
        if data.size == 0:
            raise FileLoaderError("Audio file is empty")

        channels = data.shape[1]
        if channels > 2:
            raise FileLoaderError(
                f"Unsupported channel count: {channels}. "
                "Only mono (1) and stereo (2) are supported."
            )

        original_sample_rate = sample_rate
        original_frames = data.shape[0]

        # Resample if necessary
        if sample_rate != self.engine_sample_rate:
            logger.info(
                f"Resampling from {sample_rate} Hz to {self.engine_sample_rate} Hz"
            )
            data = self._resample(data, sample_rate, self.engine_sample_rate)
            sample_rate = self.engine_sample_rate

        # Ensure float32
        data = data.astype(np.float32, copy=False)

        # Normalize to [-1, 1] if needed
        max_val = np.abs(data).max()
        if max_val > 1.0:
            logger.warning(f"Normalizing audio (max amplitude: {max_val:.2f})")
            data = data / max_val

        return AudioFile(
            path=path,
            original_sample_rate=original_sample_rate,
            sample_rate=sample_rate,
            channel_count=channels,
            total_frames=data.shape[0],
            data=data,
        )

    def _resample(
        self,
        data: np.ndarray,
        original_rate: int,
        target_rate: int
    ) -> np.ndarray:
        """
        Resample audio data to target sample rate.

        Uses scipy.signal.resample_poly for quality resampling.
        """
        from math import gcd

        # Find greatest common divisor for rational resampling
        g = gcd(original_rate, target_rate)
        up = target_rate // g
        down = original_rate // g

        # Resample each channel
        resampled_channels = []
        for ch in range(data.shape[1]):
            resampled = signal.resample_poly(data[:, ch], up, down)
            resampled_channels.append(resampled)

        return np.column_stack(resampled_channels).astype(np.float32)
