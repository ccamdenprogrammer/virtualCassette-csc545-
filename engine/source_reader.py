"""
Source reader for streaming audio with speed control.

Handles playhead position and interpolated reading at variable speeds.
"""

import numpy as np
from typing import Tuple


class SourceReader:
    """
    Reads audio from source buffer with variable speed and interpolation.

    Maintains a floating-point playhead position for smooth speed changes.
    Uses linear interpolation for reading at non-integer positions.
    """

    def __init__(
        self,
        audio_data: np.ndarray,
        total_frames: int,
        loop_enabled: bool = False
    ):
        """
        Initialize source reader.

        Args:
            audio_data: Audio data array (frames, channels)
            total_frames: Total number of frames in audio
            loop_enabled: Whether to loop at end of file
        """
        self.audio = audio_data
        self.total_frames = total_frames
        self.loop_enabled = loop_enabled

        # Playhead position as float for fractional positioning
        self._source_pos: float = 0.0

        # Flag indicating source has been exhausted (when not looping)
        self._exhausted = False

    def reset(self) -> None:
        """Reset playhead to beginning."""
        self._source_pos = 0.0
        self._exhausted = False

    def set_position(self, frame: int) -> None:
        """Set playhead to specific frame position."""
        self._source_pos = float(max(0, min(frame, self.total_frames - 1)))
        self._exhausted = False

    def set_loop(self, enabled: bool) -> None:
        """Enable or disable looping."""
        self.loop_enabled = enabled
        if enabled:
            self._exhausted = False

    def get_position(self) -> int:
        """Get current playhead position in frames."""
        return int(self._source_pos)

    def is_exhausted(self) -> bool:
        """Check if source has been fully read (when not looping)."""
        return self._exhausted

    def read(
        self,
        output_frames: int,
        speed: float = 1.0
    ) -> Tuple[np.ndarray, bool]:
        """
        Read audio block at current speed.

        Args:
            output_frames: Number of output frames to generate
            speed: Playback speed multiplier (1.0 = normal)

        Returns:
            Tuple of (audio block, exhausted flag)
            Audio block shape: (output_frames, channels)
        """
        if self._exhausted:
            # Return silence if already exhausted
            channels = self.audio.shape[1] if self.audio.ndim > 1 else 1
            return np.zeros((output_frames, channels), dtype=np.float32), True

        # Clamp speed to positive values
        speed = max(0.01, speed)

        channels = self.audio.shape[1] if self.audio.ndim > 1 else 1

        # Calculate source positions for each output sample
        positions = self._source_pos + speed * np.arange(output_frames, dtype=np.float64)

        if self.loop_enabled:
            # Wrap positions for looping
            positions = positions % self.total_frames
            output = self._interpolate(positions)
            self._source_pos = (positions[-1] + speed) % self.total_frames
            return output, False

        else:
            # Non-looping: check for end of file
            valid_mask = positions < (self.total_frames - 1)
            output = np.zeros((output_frames, channels), dtype=np.float32)

            if np.any(valid_mask):
                valid_positions = positions[valid_mask]
                valid_output = self._interpolate(valid_positions)
                output[valid_mask] = valid_output

            # Update position
            last_pos = positions[-1] + speed
            if last_pos >= self.total_frames - 1:
                self._source_pos = float(self.total_frames - 1)
                self._exhausted = True
            else:
                self._source_pos = last_pos

            return output, self._exhausted

    def _interpolate(self, positions: np.ndarray) -> np.ndarray:
        """
        Interpolate audio at floating-point positions.

        Uses linear interpolation between adjacent samples.

        Args:
            positions: Array of floating-point frame positions

        Returns:
            Interpolated audio (len(positions), channels)
        """
        channels = self.audio.shape[1] if self.audio.ndim > 1 else 1

        # Calculate integer indices and fractional parts
        i0 = np.floor(positions).astype(np.int64)
        i1 = i0 + 1
        frac = (positions - i0).astype(np.float32)

        # Clamp indices to valid range
        i0 = np.clip(i0, 0, self.total_frames - 1)
        i1 = np.clip(i1, 0, self.total_frames - 1)

        # Interpolate each channel
        output = np.zeros((len(positions), channels), dtype=np.float32)

        for ch in range(channels):
            channel_data = self.audio[:, ch] if self.audio.ndim > 1 else self.audio

            # Gather samples at indices
            s0 = channel_data[i0]
            s1 = channel_data[i1]

            # Linear interpolation
            output[:, ch] = s0 * (1.0 - frac) + s1 * frac

        return output
