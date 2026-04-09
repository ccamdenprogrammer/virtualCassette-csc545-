"""
Real-time pitch shifting using a delay-line based approach.

This uses two crossfading delay lines to achieve pitch shifting
that works reliably in real-time block processing.
"""

import numpy as np


class PitchProcessor:
    """
    Real-time pitch shifter using crossfading delay lines.

    This approach reads from a circular buffer at a variable rate,
    using two read pointers that crossfade to avoid discontinuities.
    """

    def __init__(self, sample_rate: int, channels: int):
        self.sample_rate = sample_rate
        self.channels = channels

        # Buffer size (about 150ms for more headroom)
        self.buffer_size = int(sample_rate * 0.15)

        # Circular buffer for input
        self._buffer = np.zeros((self.buffer_size, channels), dtype=np.float32)
        self._write_pos = 0

        # Grain/window size for crossfading (about 20ms)
        self._grain_size = int(sample_rate * 0.020)
        self._half_grain = self._grain_size // 2

        # Two read positions - offset from write position to read "old" data
        self._read_pos1 = 0.0
        self._read_pos2 = 0.0
        self._init_read_positions()

        # Crossfade state
        self._grain_counter = 0
        self._active_reader = 1  # Which reader is currently primary

        # Pre-compute Hann window for crossfade
        self._window = np.hanning(self._grain_size).astype(np.float32)

    def _init_read_positions(self):
        """Initialize read positions at safe offsets from write position."""
        # Reader 1 starts at a safe distance behind write
        self._read_pos1 = float(self._write_pos - self.buffer_size // 3)
        if self._read_pos1 < 0:
            self._read_pos1 += self.buffer_size
        # Reader 2 offset by half grain from reader 1
        self._read_pos2 = self._read_pos1 - self._half_grain
        if self._read_pos2 < 0:
            self._read_pos2 += self.buffer_size

    def reset(self) -> None:
        """Reset processor state."""
        self._buffer.fill(0)
        self._write_pos = 0
        self._grain_counter = 0
        self._active_reader = 1
        self._init_read_positions()

    def process(self, block: np.ndarray, semitones: float, bypass: bool = False) -> np.ndarray:
        """Apply pitch shift to audio block."""
        if bypass or abs(semitones) < 0.01:
            return block.copy()

        frames = block.shape[0]
        output = np.zeros((frames, self.channels), dtype=np.float32)

        # Pitch ratio determines read speed
        pitch_ratio = 2.0 ** (semitones / 12.0)

        # Local variable cache for speed
        buffer = self._buffer
        buffer_size = self.buffer_size
        grain_size = self._grain_size
        half_grain = self._half_grain
        window = self._window

        write_pos = self._write_pos
        read_pos1 = self._read_pos1
        read_pos2 = self._read_pos2
        grain_counter = self._grain_counter

        for i in range(frames):
            # Write input to buffer
            buffer[write_pos] = block[i]

            # Read from both positions with linear interpolation
            # Reader 1
            idx1 = int(read_pos1)
            frac1 = read_pos1 - idx1
            idx1_next = (idx1 + 1) % buffer_size
            idx1 = idx1 % buffer_size
            sample1 = buffer[idx1] * (1.0 - frac1) + buffer[idx1_next] * frac1

            # Reader 2
            idx2 = int(read_pos2)
            frac2 = read_pos2 - idx2
            idx2_next = (idx2 + 1) % buffer_size
            idx2 = idx2 % buffer_size
            sample2 = buffer[idx2] * (1.0 - frac2) + buffer[idx2_next] * frac2

            # Crossfade using pre-computed window
            # First half of grain: fade out reader 1, fade in reader 2
            # Second half: reader 2 full, reader 1 silent (preparing for next)
            if grain_counter < grain_size:
                w = window[grain_counter]
                output[i] = sample1 * (1.0 - w) + sample2 * w
            else:
                output[i] = sample2

            # Advance write position
            write_pos = (write_pos + 1) % buffer_size

            # Advance read positions at pitch-shifted rate
            read_pos1 += pitch_ratio
            read_pos2 += pitch_ratio

            # Wrap read positions
            if read_pos1 >= buffer_size:
                read_pos1 -= buffer_size
            if read_pos2 >= buffer_size:
                read_pos2 -= buffer_size

            # Update grain counter
            grain_counter += 1

            # When grain completes, swap readers and reposition
            if grain_counter >= grain_size + half_grain:
                grain_counter = 0

                # Swap: reader2 becomes reader1
                read_pos1 = read_pos2

                # Reposition reader2 at a safe distance behind write position
                # The offset depends on pitch ratio to ensure we don't read stale data
                if pitch_ratio > 1.0:
                    # Pitch up: reading faster, need more distance behind
                    safe_offset = buffer_size // 2
                else:
                    # Pitch down: reading slower, less distance needed
                    safe_offset = buffer_size // 3

                read_pos2 = float(write_pos - safe_offset)
                if read_pos2 < 0:
                    read_pos2 += buffer_size

        # Save state
        self._write_pos = write_pos
        self._read_pos1 = read_pos1
        self._read_pos2 = read_pos2
        self._grain_counter = grain_counter

        return output
