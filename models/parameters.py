"""
Effect parameters model and thread-safe parameter store.
"""

import copy
import threading
from dataclasses import dataclass, field
from typing import Any

from .. import config


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

    # Bypass flags
    bypass_speed: bool = False
    bypass_pitch: bool = False
    bypass_echo: bool = False
    bypass_reverb: bool = False


class ParameterStore:
    """
    Thread-safe store for effect parameters.

    Provides atomic snapshot reads and updates to ensure
    the audio callback always sees consistent parameter values.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._params = EffectParameters()

    def get_snapshot(self) -> EffectParameters:
        """
        Get a copy of current parameters.
        Safe to call from audio callback - uses short lock.
        """
        with self._lock:
            return copy.copy(self._params)

    def update(self, **kwargs: Any) -> None:
        """
        Update one or more parameters atomically.

        Example:
            store.update(speed=1.5, echo_mix=0.3)
        """
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._params, key):
                    setattr(self._params, key, value)
                else:
                    raise ValueError(f"Unknown parameter: {key}")

    def reset(self) -> None:
        """Reset all parameters to defaults."""
        with self._lock:
            self._params = EffectParameters()

    def get_value(self, name: str) -> Any:
        """Get a single parameter value."""
        with self._lock:
            return getattr(self._params, name)

    def set_value(self, name: str, value: Any) -> None:
        """Set a single parameter value."""
        with self._lock:
            if hasattr(self._params, name):
                setattr(self._params, name, value)
            else:
                raise ValueError(f"Unknown parameter: {name}")
