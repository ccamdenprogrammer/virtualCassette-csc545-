"""
Audio device service for querying and configuring output devices.
"""

import logging
from dataclasses import dataclass
from typing import Optional, List

import sounddevice as sd

from .. import config

logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """Information about an audio device."""
    index: int
    name: str
    max_output_channels: int
    default_sample_rate: float
    is_default: bool


class DeviceService:
    """
    Service for querying audio output devices and their capabilities.
    """

    @staticmethod
    def get_default_output_device() -> Optional[DeviceInfo]:
        """
        Get information about the default output device.

        Returns:
            DeviceInfo or None if no device available
        """
        try:
            device_index = sd.default.device[1]  # Output device index
            if device_index is None:
                # Try to get any available output device
                devices = sd.query_devices()
                for i, d in enumerate(devices):
                    if d["max_output_channels"] > 0:
                        device_index = i
                        break

            if device_index is None:
                logger.error("No output device available")
                return None

            device = sd.query_devices(device_index)
            return DeviceInfo(
                index=device_index,
                name=device["name"],
                max_output_channels=device["max_output_channels"],
                default_sample_rate=device["default_samplerate"],
                is_default=True,
            )

        except Exception as e:
            logger.error(f"Failed to query default device: {e}")
            return None

    @staticmethod
    def get_output_devices() -> List[DeviceInfo]:
        """
        Get list of all available output devices.
        """
        devices = []
        try:
            default_output = sd.default.device[1]
            all_devices = sd.query_devices()

            for i, d in enumerate(all_devices):
                if d["max_output_channels"] > 0:
                    devices.append(DeviceInfo(
                        index=i,
                        name=d["name"],
                        max_output_channels=d["max_output_channels"],
                        default_sample_rate=d["default_samplerate"],
                        is_default=(i == default_output),
                    ))

        except Exception as e:
            logger.error(f"Failed to query devices: {e}")

        return devices

    @staticmethod
    def get_engine_sample_rate() -> int:
        """
        Determine the sample rate to use for the audio engine.

        Returns the default device's sample rate if available,
        otherwise falls back to config default.
        """
        device = DeviceService.get_default_output_device()
        if device is not None:
            sample_rate = int(device.default_sample_rate)
            logger.info(f"Using device sample rate: {sample_rate} Hz")
            return sample_rate

        logger.warning(
            f"Using fallback sample rate: {config.DEFAULT_SAMPLE_RATE} Hz"
        )
        return config.DEFAULT_SAMPLE_RATE

    @staticmethod
    def test_device(device_index: int, sample_rate: int, channels: int) -> bool:
        """
        Test if a device supports the given configuration.

        Returns True if configuration is supported.
        """
        try:
            sd.check_output_settings(
                device=device_index,
                samplerate=sample_rate,
                channels=channels,
            )
            return True
        except sd.PortAudioError:
            return False
