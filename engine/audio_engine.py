"""
Audio engine for real-time playback with effects.

Manages the sounddevice output stream and coordinates playback.
"""

import logging
import threading
from typing import Optional, Callable

import numpy as np
import sounddevice as sd

from models.parameters import ParameterStore
from models.transport import TransportState, TransportInfo
from models.audio_file import AudioFile
from .source_reader import SourceReader
from .block_processor import BlockProcessor
import config

logger = logging.getLogger(__name__)


class AudioEngine:
    """
    Real-time audio engine with effect processing.

    Manages:
    - Audio output stream via sounddevice
    - Playback transport (play/pause/stop)
    - DSP effect chain processing
    - Thread-safe parameter updates
    """

    def __init__(
        self,
        parameter_store: ParameterStore,
        sample_rate: int,
        block_size: int = config.DEFAULT_BLOCK_SIZE
    ):
        """
        Initialize audio engine.

        Args:
            parameter_store: Thread-safe parameter store
            sample_rate: Audio sample rate
            block_size: Audio callback block size
        """
        self.parameter_store = parameter_store
        self.sample_rate = sample_rate
        self.block_size = block_size

        # Transport state
        self._transport_lock = threading.Lock()
        self._transport_state = TransportState.STOPPED
        self._loop_enabled = False
        self._meter_lock = threading.Lock()
        self._track_metering: dict[str, dict[str, object]] = {}
        self._master_metering = self._empty_meter()

        # Audio data (multi-file support)
        self._audio_files: dict[str, AudioFile] = {}
        self._source_readers: dict[str, SourceReader] = {}
        self._block_processors: dict[str, BlockProcessor] = {}

        # Output stream
        self._stream: Optional[sd.OutputStream] = None
        self._channels = 2  # Default to stereo

        # Error tracking
        self._callback_error: Optional[Exception] = None
        self._stream_status: Optional[sd.CallbackFlags] = None

        # Callbacks
        self._on_playback_complete: Optional[Callable[[], None]] = None
        self._on_position_update: Optional[Callable[[int], None]] = None

        logger.info(
            f"AudioEngine initialized: {sample_rate} Hz, "
            f"block size {block_size}"
        )

    def load_audio(self, audio_file: AudioFile) -> None:
        """
        Load audio file for playback.

        Args:
            audio_file: Loaded audio file model
        """
        file_id = audio_file.id

        # Stop any current playback if this is the first file
        if not self._audio_files:
            self.stop()

        self._audio_files[file_id] = audio_file
        self._channels = audio_file.channel_count  # Assume all files have same channels

        # Create source reader
        self._source_readers[file_id] = SourceReader(
            audio_file.data,
            audio_file.total_frames,
            loop_enabled=self._loop_enabled
        )

        # Create block processor
        self._block_processors[file_id] = BlockProcessor(
            self._source_readers[file_id],
            self.parameter_store,
            self.sample_rate,
            self._channels,
            file_id  # Pass file_id to BlockProcessor
        )
        with self._meter_lock:
            self._track_metering[file_id] = self._empty_meter()

        logger.info(f"Loaded audio: {audio_file.filename}")

    def remove_audio(self, file_id: str) -> None:
        """
        Remove audio file from playback.

        Args:
            file_id: ID of the file to remove
        """
        if file_id in self._audio_files:
            del self._audio_files[file_id]
            del self._source_readers[file_id]
            del self._block_processors[file_id]
            with self._meter_lock:
                self._track_metering.pop(file_id, None)
            logger.info(f"Removed audio: {file_id}")

    def has_audio_loaded(self) -> bool:
        """Check if any audio files are loaded."""
        return len(self._audio_files) > 0

    def play(self) -> None:
        """Start or resume playback."""
        if not self._audio_files:
            logger.warning("Cannot play: no audio loaded")
            return

        with self._transport_lock:
            if self._transport_state == TransportState.PLAYING:
                return

            # Reset error state
            self._callback_error = None

            # Reset position if stopped
            if self._transport_state == TransportState.STOPPED:
                for processor in self._block_processors.values():
                    processor.reset()

            self._transport_state = TransportState.PLAYING

        # Ensure stream is running
        self._ensure_stream()

        logger.info("Playback started")

    def pause(self) -> None:
        """Pause playback, keeping current position."""
        with self._transport_lock:
            if self._transport_state == TransportState.PLAYING:
                self._transport_state = TransportState.PAUSED
                logger.info("Playback paused")

    def stop(self) -> None:
        """Stop playback and reset position."""
        with self._transport_lock:
            self._transport_state = TransportState.STOPPED

        for processor in self._block_processors.values():
            processor.reset()
        self._reset_metering()

        logger.info("Playback stopped")

    def set_loop(self, enabled: bool) -> None:
        """Enable or disable looping."""
        self._loop_enabled = enabled
        for source_reader in self._source_readers.values():
            source_reader.set_loop(enabled)
        logger.info(f"Loop {'enabled' if enabled else 'disabled'}")

    def seek(self, seconds: float) -> None:
        """Seek to position in seconds."""
        frame = int(seconds * self.sample_rate)
        for source_reader in self._source_readers.values():
            source_reader.set_position(frame)
        logger.info(f"Seeked to {seconds:.2f}s")

    def get_transport_info(self) -> TransportInfo:
        """Get current transport state information."""
        with self._transport_lock:
            state = self._transport_state

        if not self._audio_files:
            return TransportInfo(
                state=state,
                position_frames=0,
                position_seconds=0.0,
                total_frames=0,
                total_seconds=0.0,
                loop_enabled=self._loop_enabled,
            )

        # For multi-file, return info based on the first file
        first_file_id = next(iter(self._audio_files.keys()))
        audio_file = self._audio_files[first_file_id]

        position_frames = (
            self._source_readers[first_file_id].get_position()
            if first_file_id in self._source_readers else 0
        )
        position_seconds = position_frames / self.sample_rate

        return TransportInfo(
            state=state,
            position_frames=position_frames,
            position_seconds=position_seconds,
            total_frames=audio_file.total_frames,
            total_seconds=audio_file.duration_seconds,
            loop_enabled=self._loop_enabled,
        )

    def set_playback_complete_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for when playback completes."""
        self._on_playback_complete = callback

    def set_position_update_callback(self, callback: Callable[[int], None]) -> None:
        """Set callback for position updates."""
        self._on_position_update = callback

    def get_callback_error(self) -> Optional[Exception]:
        """Get any error that occurred in the audio callback."""
        return self._callback_error

    def get_metering_snapshot(self) -> dict[str, object]:
        """Get the latest stereo metering for tracks and the master bus."""
        with self._meter_lock:
            return {
                "master": dict(self._master_metering),
                "tracks": {
                    file_id: dict(meter)
                    for file_id, meter in self._track_metering.items()
                },
            }

    def shutdown(self) -> None:
        """Shutdown engine and release resources."""
        logger.info("Shutting down audio engine")
        self.stop()
        self._close_stream()
        self._audio_files.clear()
        self._source_readers.clear()
        self._block_processors.clear()
        self._reset_metering()

    def _ensure_stream(self) -> None:
        """Ensure output stream is open and started."""
        if self._stream is not None and self._stream.active:
            return

        self._close_stream()

        try:
            self._stream = sd.OutputStream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=self._channels,
                dtype=np.float32,
                callback=self._audio_callback,
                finished_callback=self._stream_finished_callback,
            )
            self._stream.start()
            logger.info(
                f"Started output stream: {self._channels} channels, "
                f"{self.sample_rate} Hz"
            )

        except Exception as e:
            logger.error(f"Failed to start stream: {e}")
            self._callback_error = e

    def _close_stream(self) -> None:
        """Close the output stream."""
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.warning(f"Error closing stream: {e}")
            self._stream = None

    def _audio_callback(
        self,
        outdata: np.ndarray,
        frames: int,
        time_info,
        status: sd.CallbackFlags
    ) -> None:
        """
        Audio callback for sounddevice stream.

        This runs in the audio thread - must be fast and avoid blocking.
        """
        if status:
            self._stream_status = status
            if status.output_underflow:
                logger.warning("Audio output underflow")

        # Check transport state
        with self._transport_lock:
            state = self._transport_state

        if state != TransportState.PLAYING or not self._block_processors:
            outdata.fill(0)
            self._reset_metering()
            return

        try:
            # Process audio blocks from all files and mix
            mixed_block = np.zeros((frames, self._channels), dtype=np.float32)
            track_metering: dict[str, dict[str, object]] = {}

            for file_id, processor in self._block_processors.items():
                block = processor.process(frames)
                track_metering[file_id] = self._compute_block_meter(block)
                mixed_block += block

            mixed_block = np.clip(mixed_block, -1.0, 1.0)
            master_meter = self._compute_block_meter(mixed_block)
            with self._meter_lock:
                self._track_metering.update(track_metering)
                self._master_metering = master_meter

            # Ensure correct shape
            if mixed_block.shape[0] != frames:
                # Handle size mismatch
                outdata.fill(0)
                copy_len = min(mixed_block.shape[0], frames)
                outdata[:copy_len] = mixed_block[:copy_len]
            elif mixed_block.shape[1] != outdata.shape[1]:
                # Handle channel mismatch
                outdata.fill(0)
                copy_channels = min(mixed_block.shape[1], outdata.shape[1])
                outdata[:, :copy_channels] = mixed_block[:, :copy_channels]
            else:
                outdata[:] = mixed_block

            # Check if all sources are exhausted
            all_exhausted = all(p.is_source_exhausted() for p in self._block_processors.values())
            if all_exhausted:
                with self._transport_lock:
                    self._transport_state = TransportState.STOPPED
                self._reset_metering()

        except Exception as e:
            self._callback_error = e
            outdata.fill(0)
            with self._transport_lock:
                self._transport_state = TransportState.STOPPED
            self._reset_metering()

    def _stream_finished_callback(self) -> None:
        """Called when stream finishes."""
        logger.debug("Stream finished")

        with self._transport_lock:
            if self._transport_state == TransportState.PLAYING:
                self._transport_state = TransportState.STOPPED

        if self._on_playback_complete:
            self._on_playback_complete()

    def _empty_meter(self) -> dict[str, object]:
        """Create an empty stereo meter snapshot."""
        return {"left": 0.0, "right": 0.0, "clip_left": False, "clip_right": False}

    def _reset_metering(self) -> None:
        """Reset all track and master meters to silence."""
        with self._meter_lock:
            self._master_metering = self._empty_meter()
            for file_id in list(self._track_metering.keys()):
                self._track_metering[file_id] = self._empty_meter()

    def _compute_block_meter(self, block: np.ndarray) -> dict[str, object]:
        """Compute stereo peak/clip information for an audio block."""
        if block.size == 0:
            return self._empty_meter()

        if block.ndim == 1:
            block = block[:, np.newaxis]

        left = float(np.max(np.abs(block[:, 0]))) if block.shape[0] else 0.0
        right_channel = 1 if block.shape[1] > 1 else 0
        right = float(np.max(np.abs(block[:, right_channel]))) if block.shape[0] else 0.0

        return {
            "left": min(left, 1.0),
            "right": min(right, 1.0),
            "clip_left": left >= 0.999,
            "clip_right": right >= 0.999,
        }
