"""
Real-time echo/delay processor with feedback.

Implements a circular delay buffer for live echo effects.
"""

import numpy as np

from .. import config


class EchoProcessor:
    """
    Real-time echo processor with circular delay buffer.

    Features:
    - Variable delay time (1-1000ms)
    - Feedback control
    - Wet/dry mix
    - Smooth parameter updates during playback
    """

    def __init__(
        self,
        sample_rate: int,
        channels: int,
        max_delay_ms: float = config.MAX_ECHO_BUFFER_MS
    ):
        """
        Initialize echo processor.

        Args:
            sample_rate: Audio sample rate
            channels: Number of channels
            max_delay_ms: Maximum delay time in milliseconds
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.max_delay_ms = max_delay_ms

        # Calculate buffer size for maximum delay
        self.max_delay_samples = int(np.ceil(max_delay_ms * sample_rate / 1000.0))

        # Circular delay buffer: (samples, channels)
        self._buffer = np.zeros(
            (self.max_delay_samples, channels),
            dtype=np.float32
        )

        # Write position in circular buffer
        self._write_idx = 0

    def reset(self) -> None:
        """Reset delay buffer and write position."""
        self._buffer.fill(0)
        self._write_idx = 0

    def process(
        self,
        block: np.ndarray,
        mix: float,
        delay_ms: float,
        feedback: float,
        bypass: bool = False
    ) -> np.ndarray:
        """
        Apply echo effect to audio block.

        Args:
            block: Input audio (frames, channels)
            mix: Wet/dry mix (0.0 = dry, 1.0 = wet)
            delay_ms: Delay time in milliseconds
            feedback: Feedback amount (0.0-0.9)
            bypass: If True, return input unchanged

        Returns:
            Processed audio matching input shape
        """
        if bypass:
            return block

        frames = block.shape[0]

        # Clamp parameters
        mix = np.clip(mix, 0.0, 1.0)
        feedback = np.clip(feedback, 0.0, config.ECHO_FEEDBACK_MAX)
        delay_ms = np.clip(delay_ms, config.ECHO_DELAY_MIN_MS, self.max_delay_ms)

        # Calculate delay in samples
        delay_samples = max(1, int(delay_ms * self.sample_rate / 1000.0))
        delay_samples = min(delay_samples, self.max_delay_samples - 1)

        # Skip processing if mix is zero (but still update buffer for continuity)
        if mix < 1e-6:
            # Still feed the delay line for when mix increases
            for i in range(frames):
                self._buffer[self._write_idx] = block[i]
                self._write_idx = (self._write_idx + 1) % self.max_delay_samples
            return block.copy()

        # Process audio
        output = np.zeros_like(block)

        for i in range(frames):
            # Calculate read position
            read_idx = (self._write_idx - delay_samples) % self.max_delay_samples

            # Read delayed sample
            delayed = self._buffer[read_idx]

            # Get input sample
            dry = block[i]

            # Mix output
            output[i] = dry * (1.0 - mix) + delayed * mix

            # Write to delay buffer with feedback
            feedback_sample = dry + delayed * feedback

            # Soft clip the feedback to prevent runaway
            feedback_sample = np.clip(feedback_sample, -2.0, 2.0)

            self._buffer[self._write_idx] = feedback_sample

            # Advance write position
            self._write_idx = (self._write_idx + 1) % self.max_delay_samples

        return output.astype(np.float32)

    def get_tail_energy(self) -> float:
        """
        Get current energy in the delay buffer.
        Useful for determining when echo tail has decayed.
        """
        return float(np.mean(np.abs(self._buffer)))
