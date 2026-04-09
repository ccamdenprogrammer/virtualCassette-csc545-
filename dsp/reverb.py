"""
Real-time reverb using Schroeder algorithm.

Implements parallel comb filters + series allpass filters,
optimized for block processing.
"""

import numpy as np


class CombFilter:
    """Single comb filter with feedback and damping, optimized for block processing."""

    def __init__(self, delay_samples: int, channels: int):
        self.delay_samples = delay_samples
        self.channels = channels
        self.buffer = np.zeros((delay_samples, channels), dtype=np.float32)
        self.pos = 0
        self.filter_state = np.zeros(channels, dtype=np.float32)

    def process_block(self, block: np.ndarray, feedback: float, damping: float) -> np.ndarray:
        """Process entire block through the comb filter."""
        frames = block.shape[0]
        output = np.zeros_like(block)

        # Local variable cache for speed
        buffer = self.buffer
        delay_samples = self.delay_samples
        pos = self.pos
        filter_state = self.filter_state.copy()
        damp_inv = 1.0 - damping

        for i in range(frames):
            # Read delayed sample
            delayed = buffer[pos]

            # Apply one-pole lowpass for damping
            filter_state = delayed * damp_inv + filter_state * damping

            # Output is the delayed sample
            output[i] = delayed

            # Write new sample with feedback
            buffer[pos] = block[i] + filter_state * feedback

            # Advance position
            pos = (pos + 1) % delay_samples

        # Save state
        self.pos = pos
        self.filter_state = filter_state

        return output

    def reset(self):
        self.buffer.fill(0)
        self.filter_state.fill(0)
        self.pos = 0


class AllpassFilter:
    """Single allpass filter for diffusion, optimized for block processing."""

    def __init__(self, delay_samples: int, channels: int, gain: float = 0.5):
        self.delay_samples = delay_samples
        self.channels = channels
        self.gain = gain
        self.buffer = np.zeros((delay_samples, channels), dtype=np.float32)
        self.pos = 0

    def process_block(self, block: np.ndarray) -> np.ndarray:
        """Process entire block through the allpass filter."""
        frames = block.shape[0]
        output = np.zeros_like(block)

        # Local variable cache for speed
        buffer = self.buffer
        delay_samples = self.delay_samples
        pos = self.pos
        gain = self.gain

        for i in range(frames):
            buffered = buffer[pos]

            # Correct Schroeder allpass formula
            out_sample = buffered - gain * block[i]
            buffer[pos] = block[i] + gain * out_sample

            output[i] = out_sample
            pos = (pos + 1) % delay_samples

        # Save state
        self.pos = pos

        return output

    def reset(self):
        self.buffer.fill(0)
        self.pos = 0


class ReverbProcessor:
    """
    Schroeder reverb with parallel comb filters and series allpass filters.
    """

    def __init__(self, sample_rate: int, channels: int):
        self.sample_rate = sample_rate
        self.channels = channels

        # Comb filter delay times - tuned for natural sound
        # Using prime-ish numbers to avoid resonances
        comb_delays_ms = [29.7, 37.1, 41.1, 43.7, 31.3, 35.9]
        self.combs = []
        for delay_ms in comb_delays_ms:
            delay_samples = max(1, int(delay_ms * sample_rate / 1000.0))
            self.combs.append(CombFilter(delay_samples, channels))

        # Allpass filter delays
        allpass_delays_ms = [5.0, 1.7, 11.3]
        self.allpasses = []
        for delay_ms in allpass_delays_ms:
            delay_samples = max(1, int(delay_ms * sample_rate / 1000.0))
            self.allpasses.append(AllpassFilter(delay_samples, channels, gain=0.5))

        self.num_combs = len(self.combs)

    def reset(self) -> None:
        """Reset all filter states."""
        for comb in self.combs:
            comb.reset()
        for ap in self.allpasses:
            ap.reset()

    def process(
        self,
        block: np.ndarray,
        mix: float,
        room_size: float,
        damping: float,
        bypass: bool = False
    ) -> np.ndarray:
        """Apply reverb to audio block."""
        if bypass or mix < 0.001:
            return block.copy()

        # Clamp parameters to valid ranges
        mix = np.clip(mix, 0.0, 1.0)
        room_size = np.clip(room_size, 0.0, 1.0)
        damping = np.clip(damping, 0.0, 0.9)  # Cap to prevent filter issues

        # Map room_size to feedback (0.5 to 0.9)
        feedback = 0.5 + room_size * 0.4

        # Process through parallel comb filters
        comb_sum = np.zeros_like(block)
        for comb in self.combs:
            comb_sum += comb.process_block(block, feedback, damping)

        # Average the comb outputs
        reverb_signal = comb_sum / self.num_combs

        # Process through series allpass filters
        for ap in self.allpasses:
            reverb_signal = ap.process_block(reverb_signal)

        # Mix dry and wet
        output = block * (1.0 - mix) + reverb_signal * mix

        return np.clip(output, -1.0, 1.0).astype(np.float32)
