"""
Configuration defaults for the Real-Time Audio FX application.
"""

# Audio engine settings
DEFAULT_BLOCK_SIZE = 1024  # Larger block size for better real-time performance
DEFAULT_SAMPLE_RATE = 44100  # Fallback if device query fails

# Effect parameter defaults
DEFAULT_SPEED = 1.0
SPEED_MIN = 0.5
SPEED_MAX = 2.0

DEFAULT_PITCH = 0.0
PITCH_MIN = -12.0
PITCH_MAX = 12.0

DEFAULT_ECHO_MIX = 0.0
DEFAULT_ECHO_DELAY_MS = 250.0
DEFAULT_ECHO_FEEDBACK = 0.25
ECHO_DELAY_MIN_MS = 1.0
ECHO_DELAY_MAX_MS = 1000.0
ECHO_FEEDBACK_MAX = 0.9
MAX_ECHO_BUFFER_MS = 2000.0

DEFAULT_REVERB_MIX = 0.0
DEFAULT_REVERB_ROOM_SIZE = 0.5
DEFAULT_REVERB_DAMPING = 0.5

DEFAULT_OUTPUT_GAIN_DB = 0.0
OUTPUT_GAIN_MIN_DB = -24.0
OUTPUT_GAIN_MAX_DB = 12.0

# Parameter smoothing
PARAM_SMOOTHING_ALPHA = 0.15

# Pitch processor settings
PITCH_CONTEXT_SAMPLES = 512

# Export settings
SUPPORTED_EXPORT_FORMATS = ["wav"]
EXPORT_TAIL_SECONDS = 3.0

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"
