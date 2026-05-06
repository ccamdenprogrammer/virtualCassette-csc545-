import logging
import subprocess
from pathlib import Path
from typing import Optional
import sys

import config

logger = logging.getLogger(__name__)

class StemSeparator:
    def __init__(self, output_dir="separated/"):
        base_dir = Path(__file__).resolve().parent.parent
        self.output_dir = (base_dir / output_dir).resolve()
        stemenv_python = base_dir / ".stemenv" / "Scripts" / "python.exe"
        self.python_executable = str(stemenv_python if stemenv_python.exists() else Path(sys.executable))

    def separate(self, audio_path: str, two_stems: Optional[str] = None):
        """Separate audio into stems using demucs CLI."""
        try:
            self._validate_runtime()
            model = "mdx_extra_q"  # Use mdx_extra_q which works better
            args = [
                self.python_executable,
                "-m",
                "demucs.separate",
                "-n",
                model,
                "--out",
                str(self.output_dir),
            ]
            if two_stems:
                args.append(f"--two-stems={two_stems}")
            args.append(str(audio_path))
            logger.info(f"Separating stems for: {audio_path}")
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=config.STEM_SEPARATION_TIMEOUT_SECONDS,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Demucs separation failed: {result.stderr}")
            return self.get_stems(audio_path)
        except subprocess.TimeoutExpired:
            timeout_minutes = config.STEM_SEPARATION_TIMEOUT_SECONDS // 60
            raise RuntimeError(
                f"Stem separation timed out after {timeout_minutes} minutes"
            )
        except Exception as e:
            logger.error(f"Stem separation failed: {e}")
            raise RuntimeError(f"Stem separation failed: {e}")

    def _validate_runtime(self) -> None:
        """Check Demucs runtime dependencies before launching separation."""
        check_code = (
            "import torch, torchaudio; "
            "print(torch.__version__); "
            "print(torchaudio.__version__)"
        )
        try:
            result = subprocess.run(
                [self.python_executable, "-c", check_code],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except Exception as exc:
            raise RuntimeError(
                "The dedicated stem-separation Python environment could not be started."
            ) from exc

        if result.returncode != 0:
            raise RuntimeError(
                "torchaudio could not be loaded. This is usually caused by a "
                "torch/torchaudio version mismatch or an unsupported Python build. "
                f"Stem environment: {self.python_executable}. "
                "Reinstall matching torch and torchaudio versions, ideally in a "
                "Python 3.11 or 3.12 environment. "
                f"Details: {result.stderr.strip() or result.stdout.strip()}"
            )

        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        torch_version = lines[0] if lines else ""
        torchaudio_version = lines[1] if len(lines) > 1 else ""

        torch_base = self._major_minor(torch_version)
        torchaudio_base = self._major_minor(torchaudio_version)
        if torch_base and torchaudio_base and torch_base != torchaudio_base:
            raise RuntimeError(
                "torch and torchaudio versions do not match. "
                f"Detected torch {torch_version} and torchaudio {torchaudio_version}. "
                "Install matching versions before running stem separation."
            )

    @staticmethod
    def _major_minor(version: str) -> str:
        """Extract the major.minor part of a version string."""
        if not version:
            return ""
        core = version.split("+", 1)[0]
        parts = core.split(".")
        if len(parts) < 2:
            return core
        return ".".join(parts[:2])

    def get_stems(self, filename: str):
        """Return paths to separated files."""
        name = Path(filename).stem
        candidates = sorted(self.output_dir.glob(f"*/{name}"), key=lambda p: p.stat().st_mtime, reverse=True)

        for base in candidates:
            stems = {
                stem_path.stem: stem_path
                for stem_path in sorted(base.glob("*.wav"))
            }
            if stems:
                return stems

        return {}
