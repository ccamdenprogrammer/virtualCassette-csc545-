"""
DSP utility functions.
"""

import numpy as np


def db_to_linear(db: float) -> float:
    """
    Convert decibels to linear amplitude.

    Args:
        db: Value in decibels

    Returns:
        Linear amplitude multiplier
    """
    return 10.0 ** (db / 20.0)


def linear_to_db(linear: float) -> float:
    """
    Convert linear amplitude to decibels.

    Args:
        linear: Linear amplitude value

    Returns:
        Value in decibels
    """
    if linear <= 0:
        return -120.0  # Effectively -infinity
    return 20.0 * np.log10(linear)


def soft_clip(x: np.ndarray, drive: float = 1.0) -> np.ndarray:
    """
    Apply soft clipping using tanh.

    Args:
        x: Input signal
        drive: Drive amount (1.0 = subtle, higher = more saturation)

    Returns:
        Soft-clipped signal normalized to [-1, 1]
    """
    if drive <= 0:
        return np.clip(x, -1.0, 1.0)

    return np.tanh(drive * x) / np.tanh(drive)


def crossfade(a: np.ndarray, b: np.ndarray, mix: float) -> np.ndarray:
    """
    Crossfade between two signals.

    Args:
        a: First signal (dry)
        b: Second signal (wet)
        mix: Mix amount (0.0 = all dry, 1.0 = all wet)

    Returns:
        Mixed signal
    """
    mix = np.clip(mix, 0.0, 1.0)
    return a * (1.0 - mix) + b * mix


def resample_linear(x: np.ndarray, target_length: int) -> np.ndarray:
    """
    Resample a 1D signal using linear interpolation.

    Args:
        x: Input signal (1D array)
        target_length: Desired output length

    Returns:
        Resampled signal
    """
    if len(x) == target_length:
        return x.copy()

    if target_length <= 0:
        return np.zeros(1, dtype=x.dtype)

    old_indices = np.linspace(0, len(x) - 1, num=len(x))
    new_indices = np.linspace(0, len(x) - 1, num=target_length)
    return np.interp(new_indices, old_indices, x).astype(x.dtype)


def ensure_stereo(block: np.ndarray) -> np.ndarray:
    """
    Ensure block is stereo by duplicating mono channel if needed.

    Args:
        block: Audio block (frames, channels)

    Returns:
        Stereo block (frames, 2)
    """
    if block.ndim == 1:
        return np.column_stack([block, block])
    if block.shape[1] == 1:
        return np.column_stack([block[:, 0], block[:, 0]])
    return block
