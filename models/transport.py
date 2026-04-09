"""
Transport state model for playback control.
"""

from dataclasses import dataclass
from enum import Enum


class TransportState(Enum):
    """Playback transport states."""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass
class TransportInfo:
    """
    Snapshot of current transport information.
    """
    state: TransportState
    position_frames: int
    position_seconds: float
    total_frames: int
    total_seconds: float
    loop_enabled: bool

    @property
    def progress(self) -> float:
        """Return playback progress as 0.0-1.0."""
        if self.total_frames <= 0:
            return 0.0
        return min(1.0, self.position_frames / self.total_frames)
