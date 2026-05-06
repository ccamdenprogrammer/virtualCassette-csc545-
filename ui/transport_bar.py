"""
Transport bar UI components for the cassette player.

Contains transport controls (play/pause/stop) and utility buttons.
"""

import tkinter as tk
from typing import Callable

from .theme import COLORS, FONTS


class TransportBar(tk.Frame):
    """Transport control bar with clear play/pause/stop controls."""

    def __init__(
        self,
        parent,
        on_play: Callable,
        on_pause: Callable,
        on_stop: Callable,
        on_loop_toggle: Callable,
    ):
        super().__init__(parent, bg=COLORS["bg_panel"])

        self.on_play = on_play
        self.on_pause = on_pause
        self.on_stop = on_stop
        self.on_loop_toggle = on_loop_toggle

        self._create_widgets()

    def _create_widgets(self):
        """Create transport control buttons."""
        self.status_label = tk.Label(
            self,
            text="Stopped",
            bg=COLORS["bg_panel"],
            fg=COLORS["text_muted"],
            font=FONTS["label_small"],
            width=14,
            anchor="w",
        )
        self.status_label.pack(side="left", padx=(8, 12), pady=5)

        self.play_btn = tk.Button(
            self,
            text="Play",
            command=self.on_play,
            bg=COLORS["button_bg"],
            fg=COLORS["button_text"],
            font=FONTS["label"],
            width=8,
        )
        self.play_btn.pack(side="left", padx=5, pady=5)

        self.pause_btn = tk.Button(
            self,
            text="Pause",
            command=self.on_pause,
            bg=COLORS["button_bg"],
            fg=COLORS["button_text"],
            font=FONTS["label"],
            width=8,
        )
        self.pause_btn.pack(side="left", padx=5, pady=5)

        self.stop_btn = tk.Button(
            self,
            text="Stop",
            command=self.on_stop,
            bg=COLORS["button_bg"],
            fg=COLORS["button_text"],
            font=FONTS["label"],
            width=8,
        )
        self.stop_btn.pack(side="left", padx=5, pady=5)

        self.loop_btn = tk.Button(
            self,
            text="Loop Off",
            command=self.on_loop_toggle,
            bg=COLORS["button_bg"],
            fg=COLORS["button_text"],
            font=FONTS["label"],
            width=10,
        )
        self.loop_btn.pack(side="left", padx=5, pady=5)

    def set_state(self, playing: bool, paused: bool, loop_enabled: bool):
        """Update button states based on transport state."""
        if playing:
            self.status_label.config(text="Playing")
        elif paused:
            self.status_label.config(text="Paused")
        else:
            self.status_label.config(text="Stopped")

        self.play_btn.config(relief="sunken" if playing else "raised")
        self.pause_btn.config(relief="sunken" if paused else "raised")
        self.stop_btn.config(
            relief="sunken" if (not playing and not paused) else "raised"
        )

        if loop_enabled:
            self.loop_btn.config(
                text="Loop On",
                relief="sunken",
                bg=COLORS["accent"],
            )
        else:
            self.loop_btn.config(
                text="Loop Off",
                relief="raised",
                bg=COLORS["button_bg"],
            )


class UtilityBar(tk.Frame):
    """Utility bar with file, export, and stem actions."""

    def __init__(
        self,
        parent,
        on_load: Callable,
        on_export: Callable,
        on_separate_stems: Callable,
        on_load_stems: Callable,
        on_load_existing_stems: Callable,
    ):
        super().__init__(parent, bg=COLORS["bg_panel"])

        self.on_load = on_load
        self.on_export = on_export
        self.on_separate_stems = on_separate_stems
        self.on_load_stems = on_load_stems
        self.on_load_existing_stems = on_load_existing_stems

        self._create_widgets()

    def _create_widgets(self):
        """Create utility buttons."""
        self.load_btn = tk.Button(
            self,
            text="Load",
            command=self.on_load,
            bg=COLORS["button_bg"],
            fg=COLORS["button_text"],
            font=FONTS["label"],
        )
        self.load_btn.pack(side="left", padx=5, pady=5)

        self.export_btn = tk.Button(
            self,
            text="Export",
            command=self.on_export,
            bg=COLORS["button_bg"],
            fg=COLORS["button_text"],
            font=FONTS["label"],
        )
        self.export_btn.pack(side="left", padx=5, pady=5)

        self.separate_btn = tk.Button(
            self,
            text="Separate Stems",
            command=self.on_separate_stems,
            bg=COLORS["button_bg"],
            fg=COLORS["button_text"],
            font=FONTS["label"],
        )
        self.separate_btn.pack(side="left", padx=5, pady=5)

        self.load_stems_btn = tk.Button(
            self,
            text="Load Stems",
            command=self.on_load_stems,
            bg=COLORS["button_bg"],
            fg=COLORS["button_text"],
            font=FONTS["label"],
        )
        self.load_stems_btn.pack(side="left", padx=5, pady=5)

        self.load_existing_stems_btn = tk.Button(
            self,
            text="Load Existing Stems",
            command=self.on_load_existing_stems,
            bg=COLORS["button_bg"],
            fg=COLORS["button_text"],
            font=FONTS["label"],
        )
        self.load_existing_stems_btn.pack(side="left", padx=5, pady=5)
