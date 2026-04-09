"""
DSP (Digital Signal Processing) modules for audio effects.
"""

from .utils import db_to_linear, linear_to_db
from .pitch import PitchProcessor
from .echo import EchoProcessor
from .reverb import ReverbProcessor

__all__ = [
    "db_to_linear",
    "linear_to_db",
    "PitchProcessor",
    "EchoProcessor",
    "ReverbProcessor",
]
