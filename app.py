"""
Main application coordinator for Real-Time Audio FX.

Orchestrates the UI, audio engine, and services.
"""

import logging
from pathlib import Path
from typing import Any, Optional

from models.parameters import ParameterStore
from models.transport import TransportInfo
from models.audio_file import AudioFile
from services.file_loader import FileLoader
from services.device_service import DeviceService
from services.exporter import Exporter
from engine.audio_engine import AudioEngine
import config

# for stem separator
try:
    from services.stem_separator import StemSeparator as _StemSeparator
    STEM_SEPARATOR_AVAILABLE = True
except ImportError:
    _StemSeparator = None  # type: ignore[assignment]
    STEM_SEPARATOR_AVAILABLE = False

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

        # Stem separator
        if STEM_SEPARATOR_AVAILABLE and _StemSeparator is not None:
            self.stem_separator = _StemSeparator()
        else:
            self.stem_separator = None
        self._stems = {}

        # Initialize audio engine
        self.engine = AudioEngine(
            self.parameter_store,
            self.sample_rate,
            block_size=config.DEFAULT_BLOCK_SIZE
        )

        # Current audio files (multi-track support)
        self._audio_files: list[AudioFile] = []
        self._selected_files: set[str] = set()  # IDs of selected files

        logger.info(f"Application initialized at {self.sample_rate} Hz")

    def load_file(self, path: str | Path) -> None:
        """
        Load an audio file and add to the track list.

        Args:
            path: Path to the audio file

        Raises:
            FileLoaderError: If file cannot be loaded
        """
        logger.info(f"Loading file: {path}")

        # Load and optionally resample audio
        audio_file = self.file_loader.load(path)
        self._audio_files.append(audio_file)
        self._selected_files.add(audio_file.id)

        # Add to parameter store with defaults
        self.parameter_store.add_file(audio_file.id)

        # Load into engine (for now, still single file - will change in Phase 3)
        self.engine.load_audio(audio_file)

        logger.info(f"File loaded: {audio_file.filename}")

    def has_audio_loaded(self) -> bool:
        """Check if any audio files are loaded."""
        return len(self._audio_files) > 0

    def get_audio_files(self) -> list[AudioFile]:
        """Get list of all loaded audio files."""
        return self._audio_files.copy()

    def get_selected_files(self) -> set[str]:
        """Get set of selected file IDs."""
        return self._selected_files.copy()

    def select_file(self, file_id: str) -> None:
        """Select a file by ID."""
        if any(f.id == file_id for f in self._audio_files):
            self._selected_files.add(file_id)

    def deselect_file(self, file_id: str) -> None:
        """Deselect a file by ID."""
        self._selected_files.discard(file_id)

    def select_all_files(self) -> None:
        """Select all loaded files."""
        self._selected_files = {f.id for f in self._audio_files}

    def deselect_all_files(self) -> None:
        """Deselect all files."""
        self._selected_files.clear()

    def remove_file(self, file_id: str) -> None:
        """Remove a file by ID."""
        self._audio_files = [f for f in self._audio_files if f.id != file_id]
        self._selected_files.discard(file_id)
        self.parameter_store.remove_file(file_id)
        self.engine.remove_audio(file_id)
        # If no files left, stop engine
        if not self._audio_files:
            self.engine.stop()

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
        Update an effect parameter for selected files.

        Args:
            name: Parameter name
            value: New value
        """
        selected_ids = list(self._selected_files) or [f.id for f in self._audio_files]
        self.parameter_store.set_value(name, value, selected_ids)

    def set_file_parameter(self, file_id: str, name: str, value: Any) -> None:
        """Update a parameter for one specific file."""
        self.parameter_store.set_value(name, value, [file_id])

    def get_file_parameters(self, file_id: str):
        """Get the current parameter snapshot for one file."""
        return self.parameter_store.get_snapshot_for_file(file_id)

    def reset_parameters(self) -> None:
        """Reset all parameters to defaults for selected files."""
        selected_ids = list(self._selected_files) or [f.id for f in self._audio_files]
        self.parameter_store.reset(selected_ids)

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

    def get_metering_snapshot(self) -> dict[str, object]:
        """Get live stereo metering for each track and the master bus."""
        return self.engine.get_metering_snapshot()

    def export(self, output_path: str | Path) -> Path:
        """
        Export mixed audio from all loaded files.

        Args:
            output_path: Path for output file

        Returns:
            Path to exported file

        Raises:
            ExportError: If export fails
        """
        if not self._audio_files:
            raise ValueError("No audio files loaded")

        params_dict = self.parameter_store.get_snapshot_all()
        return self.exporter.export(
            self._audio_files,
            params_dict,
            output_path
        )

    def shutdown(self) -> None:
        """Shutdown the application."""
        logger.info("Shutting down application")
        self.engine.shutdown()
    
    # Stem Seperator  
    def separate_stems(self, two_stems: Optional[str] = None) -> dict:
        """Separate current audio file into stems."""
        if not STEM_SEPARATOR_AVAILABLE or self.stem_separator is None:
            raise ValueError("Stem separation not available - demucs not installed")
        if not self._audio_files:
            raise ValueError("No audio files loaded")
        # For now, separate the first file
        audio_file = self._audio_files[0]
        self._stems = self.stem_separator.separate(str(audio_file.path), two_stems)
        if not self._stems:
            raise ValueError(
                "Separation finished but no stem files were found in the output folder"
            )
        return self._stems

    def load_stems_as_tracks(self) -> None:
        """Load separated stems from the last separation run."""
        if not self._stems:
            raise ValueError("No stems available - run separate_stems first")

        loaded_count = 0
        for stem_name, stem_path in self._stems.items():
            if stem_path.exists():
                self.load_file(stem_path)
                logger.info(f"Loaded stem: {stem_name} from {stem_path}")
                loaded_count += 1
            else:
                logger.warning(f"Stem file not found: {stem_path}")

        if loaded_count == 0:
            raise ValueError("No stem files were found to load")

        logger.info(f"Loaded {loaded_count} stem files from the last separation")

    def load_stems_from_directory(self, directory_path: str | Path) -> None:
        """Load stem files from a directory as individual tracks."""
        directory = Path(directory_path)
        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"Directory not found: {directory_path}")
        
        # Common stem file patterns
        stem_patterns = ["vocals.wav", "drums.wav", "bass.wav", "guitar.wav", "piano.wav", "other.wav"]
        
        loaded_count = 0
        for pattern in stem_patterns:
            stem_file = directory / pattern
            if stem_file.exists():
                self.load_file(stem_file)
                logger.info(f"Loaded stem: {pattern} from {stem_file}")
                loaded_count += 1
        
        if loaded_count == 0:
            raise ValueError(f"No stem files found in {directory_path}")
        
        logger.info(f"Loaded {loaded_count} stem files from {directory_path}")
