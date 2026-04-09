"""
Audio engine for real-time playback with effects.

Manages the sounddevice output stream and coordinates playback.
"""

import logging
import threading
from typing import Optional, Callable

import numpy as np
import sounddevice as sd

from ..models.parameters import ParameterStore
from ..models.transport import TransportState, TransportInfo
from ..models.audio_file import AudioFile
from .source_reader import SourceReader
from .block_processor import BlockProcessor
from .. import config

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

        # Audio data
        self._audio_file: Optional[AudioFile] = None
        self._source_reader: Optional[SourceReader] = None
        self._block_processor: Optional[BlockProcessor] = None

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
        # Stop any current playback
        self.stop()

        self._audio_file = audio_file
        self._channels = audio_file.channel_count

        # Create source reader
        self._source_reader = SourceReader(
            audio_file.data,
            audio_file.total_frames,
            loop_enabled=self._loop_enabled
        )

        # Create block processor
        self._block_processor = BlockProcessor(
            self._source_reader,
            self.parameter_store,
            self.sample_rate,
            self._channels
        )

        logger.info(f"Loaded audio: {audio_file.filename}")

    def play(self) -> None:
        """Start or resume playback."""
        if self._audio_file is None:
            logger.warning("Cannot play: no audio loaded")
            return

        with self._transport_lock:
            if self._transport_state == TransportState.PLAYING:
                return

            # Reset error state
            self._callback_error = None

            # Reset position if stopped
            if self._transport_state == TransportState.STOPPED:
                self._block_processor.reset()

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

        if self._block_processor:
            self._block_processor.reset()

        logger.info("Playback stopped")

    def set_loop(self, enabled: bool) -> None:
        """Enable or disable looping."""
        self._loop_enabled = enabled
        if self._source_reader:
            self._source_reader.set_loop(enabled)
        logger.info(f"Loop {'enabled' if enabled else 'disabled'}")

    def seek(self, seconds: float) -> None:
        """Seek to position in seconds."""
        if self._source_reader:
            frame = int(seconds * self.sample_rate)
            self._source_reader.set_position(frame)
            logger.info(f"Seeked to {seconds:.2f}s")

    def get_transport_info(self) -> TransportInfo:
        """Get current transport state information."""
        with self._transport_lock:
            state = self._transport_state

        if self._audio_file is None:
            return TransportInfo(
                state=state,
                position_frames=0,
                position_seconds=0.0,
                total_frames=0,
                total_seconds=0.0,
                loop_enabled=self._loop_enabled,
            )

        position_frames = (
            self._source_reader.get_position()
            if self._source_reader else 0
        )
        position_seconds = position_frames / self.sample_rate

        return TransportInfo(
            state=state,
            position_frames=position_frames,
            position_seconds=position_seconds,
            total_frames=self._audio_file.total_frames,
            total_seconds=self._audio_file.duration_seconds,
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

    def shutdown(self) -> None:
        """Shutdown engine and release resources."""
        logger.info("Shutting down audio engine")
        self.stop()
        self._close_stream()
        self._audio_file = None
        self._source_reader = None
        self._block_processor = None

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

        if state != TransportState.PLAYING or self._block_processor is None:
            outdata.fill(0)
            return

        try:
            # Process audio block
            block = self._block_processor.process(frames)

            # Ensure correct shape
            if block.shape[0] != frames:
                # Handle size mismatch
                outdata.fill(0)
                copy_len = min(block.shape[0], frames)
                outdata[:copy_len] = block[:copy_len]
            elif block.shape[1] != outdata.shape[1]:
                # Handle channel mismatch
                outdata.fill(0)
                copy_channels = min(block.shape[1], outdata.shape[1])
                outdata[:, :copy_channels] = block[:, :copy_channels]
            else:
                outdata[:] = block

            # Check if playback is complete
            if self._block_processor.is_source_exhausted():
                with self._transport_lock:
                    self._transport_state = TransportState.STOPPED

        except Exception as e:
            self._callback_error = e
            outdata.fill(0)
            with self._transport_lock:
                self._transport_state = TransportState.STOPPED

    def _stream_finished_callback(self) -> None:
        """Called when stream finishes."""
        logger.debug("Stream finished")

        with self._transport_lock:
            if self._transport_state == TransportState.PLAYING:
                self._transport_state = TransportState.STOPPED

        if self._on_playback_complete:
            self._on_playback_complete()
