"""
Tests for the file loader service.
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from realtime_audio_fx.services.file_loader import FileLoader, FileLoaderError


class TestFileLoader:
    """Tests for FileLoader class."""

    @pytest.fixture
    def loader(self):
        """Create file loader with standard sample rate."""
        return FileLoader(engine_sample_rate=44100)

    @pytest.fixture
    def temp_wav_mono(self):
        """Create a temporary mono WAV file."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            # Generate test audio
            sr = 44100
            duration = 1.0
            t = np.linspace(0, duration, int(sr * duration))
            audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)

            sf.write(f.name, audio, sr)
            yield Path(f.name)

        # Cleanup
        Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def temp_wav_stereo(self):
        """Create a temporary stereo WAV file."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sr = 44100
            duration = 1.0
            t = np.linspace(0, duration, int(sr * duration))
            left = np.sin(2 * np.pi * 440 * t).astype(np.float32)
            right = np.sin(2 * np.pi * 550 * t).astype(np.float32)
            audio = np.column_stack([left, right])

            sf.write(f.name, audio, sr)
            yield Path(f.name)

        Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def temp_wav_different_sr(self):
        """Create a temporary WAV file at different sample rate."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sr = 48000  # Different from 44100
            duration = 1.0
            t = np.linspace(0, duration, int(sr * duration))
            audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)

            sf.write(f.name, audio, sr)
            yield Path(f.name)

        Path(f.name).unlink(missing_ok=True)

    def test_load_mono(self, loader, temp_wav_mono):
        """Test loading mono WAV file."""
        audio_file = loader.load(temp_wav_mono)

        assert audio_file.channel_count == 1
        assert audio_file.sample_rate == 44100
        assert audio_file.data.dtype == np.float32
        assert audio_file.data.ndim == 2
        assert audio_file.data.shape[1] == 1

    def test_load_stereo(self, loader, temp_wav_stereo):
        """Test loading stereo WAV file."""
        audio_file = loader.load(temp_wav_stereo)

        assert audio_file.channel_count == 2
        assert audio_file.sample_rate == 44100
        assert audio_file.data.dtype == np.float32
        assert audio_file.data.ndim == 2
        assert audio_file.data.shape[1] == 2

    def test_resampling(self, loader, temp_wav_different_sr):
        """Test that files are resampled to engine sample rate."""
        audio_file = loader.load(temp_wav_different_sr)

        assert audio_file.sample_rate == 44100
        assert audio_file.original_sample_rate == 48000
        # Data should be resampled
        assert audio_file.data.shape[0] != int(48000 * 1.0)

    def test_file_not_found(self, loader):
        """Test loading nonexistent file raises error."""
        with pytest.raises(FileLoaderError, match="not found"):
            loader.load("/nonexistent/path/file.wav")

    def test_unsupported_format(self, loader):
        """Test loading unsupported format raises error."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"not audio")
            temp_path = Path(f.name)

        try:
            with pytest.raises(FileLoaderError, match="Unsupported"):
                loader.load(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_audio_file_metadata(self, loader, temp_wav_stereo):
        """Test audio file metadata is correct."""
        audio_file = loader.load(temp_wav_stereo)

        assert audio_file.filename == temp_wav_stereo.name
        assert audio_file.path == temp_wav_stereo
        assert audio_file.duration_seconds > 0
        assert audio_file.total_frames > 0

    def test_audio_normalized(self, loader, temp_wav_mono):
        """Test audio is normalized to float32 range."""
        audio_file = loader.load(temp_wav_mono)

        # Data should be in valid range
        assert np.all(audio_file.data >= -1.0)
        assert np.all(audio_file.data <= 1.0)

    def test_metadata_string(self, loader, temp_wav_stereo):
        """Test metadata string generation."""
        audio_file = loader.load(temp_wav_stereo)
        info = audio_file.get_metadata_string()

        assert "Stereo" in info
        assert "44100 Hz" in info
        assert "s" in info  # Duration
