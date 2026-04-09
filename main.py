"""
Entry point for the Real-Time Audio FX application.
"""

import logging
import sys
import tkinter as tk
from pathlib import Path

# Add parent directory to path for imports when running directly
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from realtime_audio_fx import config
from realtime_audio_fx.app import App
from realtime_audio_fx.ui.main_window import MainWindow


def setup_logging() -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )


def main() -> None:
    """Main entry point."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Real-Time Audio FX application")

    # Create Tkinter root
    root = tk.Tk()

    # Create application
    app = App()

    # Create main window
    window = MainWindow(root, app)

    # Setup shutdown handler
    def on_closing():
        logger.info("Application closing")
        app.shutdown()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Run application
    try:
        window.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
    finally:
        app.shutdown()

    logger.info("Application terminated")


if __name__ == "__main__":
    main()
