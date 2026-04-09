"""
Main application coordinator for Real-Time Audio FX.

Orchestrates the UI, audio engine, and services.
"""

import logging
from pathlib import Path
from typing import Any, Optional

from .models.parameters import ParameterStore
from .models.transport import TransportInfo
from .models.audio_file import AudioFile
from .services.file_loader import FileLoader
from .services.device_service import DeviceService
from .services.exporter import Exporter
from .engine.audio_engine import AudioEngine
from . import config

logger = logging.getLogger(__name__)


class App:
    """
    Main application class coordinating all components.

    Provides a clean interface for the UI to interact with
    the audio engine and services.
    """

    def __init__(self):
        """Initialize the application."""
        logger.info("Initializing application")

        # Initialize parameter store
        self.parameter_store = ParameterStore()

        # Determine engine sample rate
        self.sample_rate = DeviceService.get_engine_sample_rate()

        # Initialize services
        self.file_loader = FileLoader(self.sample_rate)
        self.exporter = Exporter(self.sample_rate)

        # Initialize audio engine
        self.engine = AudioEngine(
            self.parameter_store,
            self.sample_rate,
            block_size=config.DEFAULT_BLOCK_SIZE
        )

        # Current audio file
        self._audio_file: Optional[AudioFile] = None

        logger.info(f"Application initialized at {self.sample_rate} Hz")

    def load_file(self, path: str | Path) -> None:
        """
        Load an audio file.

        Args:
            path: Path to the audio file

        Raises:
            FileLoaderError: If file cannot be loaded
        """
        logger.info(f"Loading file: {path}")

        # Load and optionally resample audio
        self._audio_file = self.file_loader.load(path)

        # Load into engine
        self.engine.load_audio(self._audio_file)

        logger.info(f"File loaded: {self._audio_file.filename}")

    def has_audio_loaded(self) -> bool:
        """Check if an audio file is loaded."""
        return self._audio_file is not None

    def get_file_info(self) -> str:
        """Get formatted file information string."""
        if self._audio_file is None:
            return "No file loaded"
        return self._audio_file.get_metadata_string()

    def play(self) -> None:
        """Start or resume playback."""
        self.engine.play()

    def pause(self) -> None:
        """Pause playback."""
        self.engine.pause()

    def stop(self) -> None:
        """Stop playback and reset position."""
        self.engine.stop()

    def set_loop(self, enabled: bool) -> None:
        """Enable or disable loop mode."""
        self.engine.set_loop(enabled)

    def seek(self, seconds: float) -> None:
        """Seek to position in seconds."""
        self.engine.seek(seconds)

    def set_parameter(self, name: str, value: Any) -> None:
        """
        Update an effect parameter.

        Args:
            name: Parameter name
            value: New value
        """
        self.parameter_store.set_value(name, value)

    def reset_parameters(self) -> None:
        """Reset all parameters to defaults."""
        self.parameter_store.reset()

    def get_transport_info(self) -> TransportInfo:
        """Get current transport state."""
        return self.engine.get_transport_info()

    def get_engine_error(self) -> Optional[Exception]:
        """Get any engine callback error."""
        error = self.engine.get_callback_error()
        if error:
            # Clear error after reading
            self.engine._callback_error = None
        return error

    def export(self, output_path: str | Path) -> Path:
        """
        Export processed audio to file.

        Args:
            output_path: Path for output file

        Returns:
            Path to exported file

        Raises:
            ExportError: If export fails
        """
        if self._audio_file is None:
            raise ValueError("No audio file loaded")

        params = self.parameter_store.get_snapshot()
        return self.exporter.export(
            self._audio_file,
            params,
            output_path
        )

    def shutdown(self) -> None:
        """Shutdown the application."""
        logger.info("Shutting down application")
        self.engine.shutdown()
