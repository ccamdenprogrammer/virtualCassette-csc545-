"""
Cassette Player main application window.

A minimal, sleek cassette player-themed UI for the audio effects application.
"""

import logging
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

from .. import config
from ..models.transport import TransportState
from .theme import COLORS, FONTS, DIMENSIONS
from .cassette_display import CassetteDisplay
from .knob_widget import create_knob
from .transport_bar import TransportBar, UtilityBar

if TYPE_CHECKING:
    from ..app import App

logger = logging.getLogger(__name__)


class MainWindow:
    """
    Cassette player-themed main application window.

    Features:
    - Animated cassette tape display
    - Rotary knob controls for all parameters
    - Transport controls (play/pause/stop/loop)
    - File loading and export
    """

    def __init__(self, root: tk.Tk, app: "App"):
        """
        Initialize main window.

        Args:
            root: Tkinter root window
            app: Application instance for callbacks
        """
        self.root = root
        self.app = app

        # Window setup
        self.root.title("Cassette Player")
        self.root.geometry(f"{DIMENSIONS['window_width']}x{DIMENSIONS['window_height']}")
        self.root.minsize(550, 480)
        self.root.configure(bg=COLORS['bg_dark'])
        self.root.resizable(True, True)

        # Build UI
        self._build_ui()

        # Start UI update timer
        self._update_interval = 100  # ms
        self._schedule_update()

        logger.info("Cassette player window initialized")

    def _build_ui(self):
        """Build the complete UI."""
        # Main container
        self.main_frame = tk.Frame(self.root, bg=COLORS['bg_dark'])
        self.main_frame.pack(fill='both', expand=True, padx=15, pady=15)

        # === Section 1: Cassette Display ===
        self._create_cassette_section()

        # === Section 2: Knob Controls ===
        self._create_knobs_section()

        # === Section 3: Transport Controls ===
        self._create_transport_section()

        # === Section 4: Utility Bar ===
        self._create_utility_section()

    def _create_cassette_section(self):
        """Create the cassette display section."""
        self.cassette_frame = tk.Frame(self.main_frame, bg=COLORS['bg_dark'])
        self.cassette_frame.pack(fill='x', pady=(0, 10))

        # Center the cassette display
        self.cassette = CassetteDisplay(self.cassette_frame)
        self.cassette.pack(anchor='center')

    def _create_knobs_section(self):
        """Create the knob controls section."""
        # Panel background
        self.knobs_panel = tk.Frame(
            self.main_frame,
            bg=COLORS['bg_panel'],
            padx=20,
            pady=15,
        )
        self.knobs_panel.pack(fill='x', pady=10)

        # Row 1: Speed (large, centered)
        speed_row = tk.Frame(self.knobs_panel, bg=COLORS['bg_panel'])
        speed_row.pack(fill='x', pady=(0, 10))

        self.speed_knob = create_knob(
            speed_row,
            label="SPEED",
            min_val=config.SPEED_MIN,
            max_val=config.SPEED_MAX,
            initial_val=config.DEFAULT_SPEED,
            callback=self._on_speed_change,
            unit="x",
            size=DIMENSIONS['knob_size_large'],
            decimals=2,
        )
        self.speed_knob.pack(anchor='center')

        # Divider
        tk.Frame(
            self.knobs_panel,
            height=1,
            bg=COLORS['border_subtle'],
        ).pack(fill='x', pady=10)

        # Row 2: Echo controls
        echo_row = tk.Frame(self.knobs_panel, bg=COLORS['bg_panel'])
        echo_row.pack(fill='x', pady=5)

        # Echo label
        tk.Label(
            echo_row,
            text="ECHO",
            font=FONTS['label_small'],
            fg=COLORS['text_muted'],
            bg=COLORS['bg_panel'],
        ).pack(anchor='center', pady=(0, 5))

        # Echo knobs container
        echo_knobs = tk.Frame(echo_row, bg=COLORS['bg_panel'])
        echo_knobs.pack(anchor='center')

        self.echo_mix_knob = create_knob(
            echo_knobs,
            label="MIX",
            min_val=0.0,
            max_val=1.0,
            initial_val=config.DEFAULT_ECHO_MIX,
            callback=self._on_echo_mix_change,
            unit="%",
            size=DIMENSIONS['knob_size_small'],
            decimals=0,
        )
        self.echo_mix_knob.pack(side='left', padx=15)
        # Override formatter for percentage
        self.echo_mix_knob.formatter = lambda v: f"{int(v * 100)}%"
        self.echo_mix_knob._update_display()

        self.echo_delay_knob = create_knob(
            echo_knobs,
            label="DELAY",
            min_val=config.ECHO_DELAY_MIN_MS,
            max_val=config.ECHO_DELAY_MAX_MS,
            initial_val=config.DEFAULT_ECHO_DELAY_MS,
            callback=self._on_echo_delay_change,
            unit="ms",
            size=DIMENSIONS['knob_size_small'],
            decimals=0,
        )
        self.echo_delay_knob.pack(side='left', padx=15)

        self.echo_feedback_knob = create_knob(
            echo_knobs,
            label="FEEDBACK",
            min_val=0.0,
            max_val=config.ECHO_FEEDBACK_MAX,
            initial_val=config.DEFAULT_ECHO_FEEDBACK,
            callback=self._on_echo_feedback_change,
            unit="%",
            size=DIMENSIONS['knob_size_small'],
            decimals=0,
        )
        self.echo_feedback_knob.pack(side='left', padx=15)
        # Override formatter for percentage
        self.echo_feedback_knob.formatter = lambda v: f"{int(v * 100)}%"
        self.echo_feedback_knob._update_display()

        # Divider
        tk.Frame(
            self.knobs_panel,
            height=1,
            bg=COLORS['border_subtle'],
        ).pack(fill='x', pady=10)

        # Row 3: Output gain
        gain_row = tk.Frame(self.knobs_panel, bg=COLORS['bg_panel'])
        gain_row.pack(fill='x', pady=5)

        self.gain_knob = create_knob(
            gain_row,
            label="OUTPUT",
            min_val=config.OUTPUT_GAIN_MIN_DB,
            max_val=config.OUTPUT_GAIN_MAX_DB,
            initial_val=config.DEFAULT_OUTPUT_GAIN_DB,
            callback=self._on_gain_change,
            unit=" dB",
            size=DIMENSIONS['knob_size_medium'],
            decimals=1,
        )
        self.gain_knob.pack(anchor='center')

    def _create_transport_section(self):
        """Create the transport controls section."""
        self.transport_bar = TransportBar(
            self.main_frame,
            on_play=self._on_play,
            on_pause=self._on_pause,
            on_stop=self._on_stop,
            on_loop=self._on_loop_toggle,
        )
        self.transport_bar.pack(fill='x', pady=5)

    def _create_utility_section(self):
        """Create the utility bar section."""
        self.utility_bar = UtilityBar(
            self.main_frame,
            on_load=self._on_open_file,
            on_export=self._on_export,
        )
        self.utility_bar.pack(fill='x', pady=(5, 0))

    # === Event Handlers ===

    def _on_open_file(self):
        """Handle file open."""
        filetypes = [
            ("Audio Files", "*.wav *.flac *.ogg *.mp3 *.aiff *.aif"),
            ("WAV Files", "*.wav"),
            ("FLAC Files", "*.flac"),
            ("All Files", "*.*"),
        ]
        path = filedialog.askopenfilename(
            title="Load Audio File",
            filetypes=filetypes
        )
        if path:
            try:
                self.app.load_file(path)
                # Update cassette display with file info
                info = self.app.get_file_info()
                # Extract just filename for display
                filename = path.split('/')[-1].split('\\')[-1]
                self.cassette.set_file_name(filename)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file:\n{e}")

    def _on_play(self):
        """Handle play button."""
        self.app.play()

    def _on_pause(self):
        """Handle pause button."""
        self.app.pause()

    def _on_stop(self):
        """Handle stop button."""
        self.app.stop()

    def _on_loop_toggle(self):
        """Handle loop toggle."""
        transport = self.app.get_transport_info()
        self.app.set_loop(not transport.loop_enabled)

    def _on_speed_change(self, value: float):
        """Handle speed knob change."""
        self.app.set_parameter("speed", value)
        self.cassette.set_speed(value)

    def _on_echo_mix_change(self, value: float):
        """Handle echo mix knob change."""
        self.app.set_parameter("echo_mix", value)

    def _on_echo_delay_change(self, value: float):
        """Handle echo delay knob change."""
        self.app.set_parameter("echo_delay_ms", value)

    def _on_echo_feedback_change(self, value: float):
        """Handle echo feedback knob change."""
        self.app.set_parameter("echo_feedback", value)

    def _on_gain_change(self, value: float):
        """Handle output gain knob change."""
        self.app.set_parameter("output_gain_db", value)

    def _on_export(self):
        """Handle export button."""
        if not self.app.has_audio_loaded():
            messagebox.showwarning("Warning", "No audio file loaded")
            return

        path = filedialog.asksaveasfilename(
            title="Export Processed Audio",
            defaultextension=".wav",
            filetypes=[("WAV Files", "*.wav")],
        )
        if not path:
            return

        try:
            self.app.export(path)
            messagebox.showinfo("Success", f"Audio exported to:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed:\n{e}")

    def _reset_knobs(self):
        """Reset all knobs to default values."""
        self.speed_knob.set_value(config.DEFAULT_SPEED)
        self.echo_mix_knob.set_value(config.DEFAULT_ECHO_MIX)
        self.echo_delay_knob.set_value(config.DEFAULT_ECHO_DELAY_MS)
        self.echo_feedback_knob.set_value(config.DEFAULT_ECHO_FEEDBACK)
        self.gain_knob.set_value(config.DEFAULT_OUTPUT_GAIN_DB)

    # === UI Update Loop ===

    def _schedule_update(self):
        """Schedule periodic UI update."""
        self._update_ui()
        self.root.after(self._update_interval, self._schedule_update)

    def _update_ui(self):
        """Update UI with current playback state."""
        transport = self.app.get_transport_info()

        # Update cassette animation state
        is_playing = transport.state == TransportState.PLAYING
        self.cassette.set_playing(is_playing)

        # Update time display
        pos = transport.position_seconds
        total = transport.total_seconds
        pos_str = f"{int(pos // 60)}:{int(pos % 60):02d}"
        total_str = f"{int(total // 60)}:{int(total % 60):02d}"
        self.cassette.set_time(pos_str, total_str)

        # Update transport button states
        self.transport_bar.set_state(
            playing=(transport.state == TransportState.PLAYING),
            paused=(transport.state == TransportState.PAUSED),
            loop_enabled=transport.loop_enabled,
        )

        # Check for callback errors
        error = self.app.get_engine_error()
        if error:
            messagebox.showerror("Audio Error", f"Audio engine error:\n{error}")

    def run(self):
        """Start the main event loop."""
        self.root.mainloop()
