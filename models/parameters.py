"""
Effect parameters model and thread-safe parameter store.
"""

import copy
import threading
from dataclasses import dataclass, field
from typing import Any

import config


@dataclass
class EffectParameters:
    """
    Container for all effect parameters.
    All values are designed to be read atomically as a snapshot.
    """
    # Speed control (1.0 = normal, <1 slower, >1 faster)
    speed: float = config.DEFAULT_SPEED

    # Pitch shift in semitones (-12 to +12)
    pitch_semitones: float = config.DEFAULT_PITCH

    # Echo parameters
    echo_mix: float = config.DEFAULT_ECHO_MIX
    echo_delay_ms: float = config.DEFAULT_ECHO_DELAY_MS
    echo_feedback: float = config.DEFAULT_ECHO_FEEDBACK

    # Reverb parameters
    reverb_mix: float = config.DEFAULT_REVERB_MIX
    reverb_room_size: float = config.DEFAULT_REVERB_ROOM_SIZE
    reverb_damping: float = config.DEFAULT_REVERB_DAMPING

    # Output gain in dB
    output_gain_db: float = config.DEFAULT_OUTPUT_GAIN_DB
    output_gain_left_db: float = config.DEFAULT_OUTPUT_GAIN_LEFT_DB
    output_gain_right_db: float = config.DEFAULT_OUTPUT_GAIN_RIGHT_DB

    # Per-track volume trim (linear)
    track_volume: float = config.DEFAULT_TRACK_VOLUME

    # Bypass flags
    bypass_speed: bool = False
    bypass_pitch: bool = False
    bypass_echo: bool = False
    bypass_reverb: bool = False


class ParameterStore:
    """
    Thread-safe store for effect parameters per file.

    Provides atomic snapshot reads and updates to ensure
    the audio callback always sees consistent parameter values.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._file_params: dict[str, EffectParameters] = {}  # file_id -> params
        self._defaults = EffectParameters()

    def get_snapshot(self) -> EffectParameters:
        """
        Get a copy of default parameters (for backward compatibility).
        Safe to call from audio callback - uses short lock.
        """
        with self._lock:
            return copy.copy(self._defaults)

    def get_snapshot_for_file(self, file_id: str) -> EffectParameters:
        """
        Get a snapshot of parameters for a specific file.
        Falls back to defaults if file not found.
        Safe to call from audio callback - uses short lock.
        """
        with self._lock:
            if file_id in self._file_params:
                return copy.copy(self._file_params[file_id])
            else:
                return copy.copy(self._defaults)

    def get_snapshot_all(self) -> dict[str, EffectParameters]:
        """
        Get snapshots for all files.
        Returns dict of file_id -> EffectParameters
        """
        with self._lock:
            return {fid: copy.copy(params) for fid, params in self._file_params.items()}

    def update(self, file_ids: list[str] | None = None, **kwargs: Any) -> None:
        """
        Update one or more parameters for specified files.
        If file_ids is None, updates defaults.

        Example:
            store.update(file_ids=['file1', 'file2'], speed=1.5, echo_mix=0.3)
        """
        with self._lock:
            if file_ids is None:
                # Update defaults
                for key, value in kwargs.items():
                    if hasattr(self._defaults, key):
                        setattr(self._defaults, key, value)
                    else:
                        raise ValueError(f"Unknown parameter: {key}")
            else:
                # Update specific files
                for file_id in file_ids:
                    if file_id not in self._file_params:
                        self._file_params[file_id] = copy.copy(self._defaults)
                    params = self._file_params[file_id]
                    for key, value in kwargs.items():
                        if hasattr(params, key):
                            setattr(params, key, value)
                        else:
                            raise ValueError(f"Unknown parameter: {key}")

    def reset(self, file_ids: list[str] | None = None) -> None:
        """Reset parameters to defaults for specified files, or all if None."""
        with self._lock:
            if file_ids is None:
                self._file_params.clear()
                self._defaults = EffectParameters()
            else:
                for file_id in file_ids:
                    self._file_params[file_id] = copy.copy(self._defaults)

    def get_value(self, name: str, file_id: str | None = None) -> Any:
        """Get a single parameter value for a file, or defaults if None."""
        with self._lock:
            params = self._file_params.get(file_id, self._defaults) if file_id else self._defaults
            return getattr(params, name)

    def set_value(self, name: str, value: Any, file_ids: list[str] | None = None) -> None:
        """Set a single parameter value for specified files, or defaults if None."""
        with self._lock:
            if file_ids is None:
                if hasattr(self._defaults, name):
                    setattr(self._defaults, name, value)
                else:
                    raise ValueError(f"Unknown parameter: {name}")
            else:
                for file_id in file_ids:
                    if file_id not in self._file_params:
                        self._file_params[file_id] = copy.copy(self._defaults)
                    params = self._file_params[file_id]
                    if hasattr(params, name):
                        setattr(params, name, value)
                    else:
                        raise ValueError(f"Unknown parameter: {name}")

    def add_file(self, file_id: str) -> None:
        """Add a new file with default parameters."""
        with self._lock:
            if file_id not in self._file_params:
                self._file_params[file_id] = copy.copy(self._defaults)

    def remove_file(self, file_id: str) -> None:
        """Remove parameters for a file."""
        with self._lock:
            self._file_params.pop(file_id, None)
