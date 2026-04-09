"""
Transport control bar widget.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from .theme import COLORS, FONTS, DIMENSIONS


class TransportButton(tk.Canvas):
    """A styled transport button."""

    def __init__(
        self,
        parent,
        text: str,
        icon: str,
        command: Callable[[], None],
        width: int = 70,
        height: int = 36,
        toggle: bool = False,
    ):
        """
        Initialize transport button.

        Args:
            parent: Parent widget
            text: Button text
            icon: Icon character
            command: Click callback
            width: Button width
            height: Button height
            toggle: Whether this is a toggle button
        """
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=COLORS['bg_panel'],
            highlightthickness=0,
        )

        self.text = text
        self.icon = icon
        self.command = command
        self.width = width
        self.height = height
        self.toggle = toggle

        self._hover = False
        self._active = False
        self._pressed = False

        self._draw()

        self.bind('<Button-1>', self._on_press)
        self.bind('<ButtonRelease-1>', self._on_release)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)

    def _draw(self):
        """Draw the button."""
        self.delete('all')

        # Determine colors based on state
        if self._active:
            bg_color = COLORS['button_active']
            text_color = COLORS['bg_dark']
        elif self._pressed:
            bg_color = COLORS['accent_dim']
            text_color = COLORS['text_primary']
        elif self._hover:
            bg_color = COLORS['button_hover']
            text_color = COLORS['text_primary']
        else:
            bg_color = COLORS['button_bg']
            text_color = COLORS['text_primary']

        # Button shape
        radius = 8
        self._draw_rounded_rect(
            2, 2,
            self.width - 2, self.height - 2,
            radius=radius,
            fill=bg_color,
            outline=COLORS['border_subtle'] if not self._active else '',
        )

        # Icon and text
        cx = self.width // 2
        cy = self.height // 2

        # Just show text (icon included in text)
        display_text = f"{self.icon} {self.text}" if self.icon else self.text
        self.create_text(
            cx, cy,
            text=display_text,
            font=FONTS['label'],
            fill=text_color,
            anchor='center',
        )

    def _draw_rounded_rect(self, x1, y1, x2, y2, radius=10, **kwargs):
        """Draw a rounded rectangle."""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
            x1 + radius, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _on_press(self, event):
        """Handle mouse press."""
        self._pressed = True
        self._draw()

    def _on_release(self, event):
        """Handle mouse release."""
        self._pressed = False
        if self._hover:
            self.command()
        self._draw()

    def _on_enter(self, event):
        """Handle mouse enter."""
        self._hover = True
        self.config(cursor='hand2')
        self._draw()

    def _on_leave(self, event):
        """Handle mouse leave."""
        self._hover = False
        self._pressed = False
        self.config(cursor='')
        self._draw()

    def set_active(self, active: bool):
        """Set the active state."""
        self._active = active
        self._draw()


class TransportBar(tk.Frame):
    """
    Transport control bar with play/pause/stop/loop buttons.
    """

    def __init__(
        self,
        parent,
        on_play: Callable[[], None],
        on_pause: Callable[[], None],
        on_stop: Callable[[], None],
        on_loop: Callable[[], None],
    ):
        """
        Initialize transport bar.

        Args:
            parent: Parent widget
            on_play: Play callback
            on_pause: Pause callback
            on_stop: Stop callback
            on_loop: Loop toggle callback
        """
        super().__init__(parent, bg=COLORS['bg_panel'])

        self.on_play = on_play
        self.on_pause = on_pause
        self.on_stop = on_stop
        self.on_loop = on_loop

        self._build_ui()

    def _build_ui(self):
        """Build the transport bar UI."""
        # Center container
        container = tk.Frame(self, bg=COLORS['bg_panel'])
        container.pack(pady=10)

        # Transport buttons
        self.play_btn = TransportButton(
            container,
            text="Play",
            icon="\u25B6",  # Play triangle
            command=self.on_play,
        )
        self.play_btn.pack(side='left', padx=5)

        self.pause_btn = TransportButton(
            container,
            text="Pause",
            icon="\u23F8",  # Pause
            command=self.on_pause,
        )
        self.pause_btn.pack(side='left', padx=5)

        self.stop_btn = TransportButton(
            container,
            text="Stop",
            icon="\u23F9",  # Stop
            command=self.on_stop,
        )
        self.stop_btn.pack(side='left', padx=5)

        # Spacer
        tk.Frame(container, width=20, bg=COLORS['bg_panel']).pack(side='left')

        self.loop_btn = TransportButton(
            container,
            text="Loop",
            icon="\u27F2",  # Loop arrow
            command=self._on_loop_click,
            toggle=True,
        )
        self.loop_btn.pack(side='left', padx=5)

        self._loop_enabled = False

    def _on_loop_click(self):
        """Handle loop button click."""
        self._loop_enabled = not self._loop_enabled
        self.loop_btn.set_active(self._loop_enabled)
        self.on_loop()

    def set_state(self, playing: bool, paused: bool, loop_enabled: bool):
        """Update button states based on transport state."""
        self.play_btn.set_active(playing and not paused)
        self.pause_btn.set_active(paused)
        self.stop_btn.set_active(not playing and not paused)
        self._loop_enabled = loop_enabled
        self.loop_btn.set_active(loop_enabled)


class UtilityBar(tk.Frame):
    """
    Utility bar with file/export buttons.
    """

    def __init__(
        self,
        parent,
        on_load: Callable[[], None],
        on_export: Callable[[], None],
    ):
        """
        Initialize utility bar.

        Args:
            parent: Parent widget
            on_load: Load file callback
            on_export: Export callback
        """
        super().__init__(parent, bg=COLORS['bg_panel'])

        self.on_load = on_load
        self.on_export = on_export

        self._build_ui()

    def _build_ui(self):
        """Build the utility bar UI."""
        container = tk.Frame(self, bg=COLORS['bg_panel'])
        container.pack(pady=8)

        self.load_btn = TransportButton(
            container,
            text="Load",
            icon="",
            command=self.on_load,
            width=80,
        )
        self.load_btn.pack(side='left', padx=8)

        self.export_btn = TransportButton(
            container,
            text="Export",
            icon="",
            command=self.on_export,
            width=80,
        )
        self.export_btn.pack(side='left', padx=8)

    def set_export_enabled(self, enabled: bool):
        """Enable or disable the export button."""
        # Visual indication could be added here
        pass
