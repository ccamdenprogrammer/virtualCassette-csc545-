"""
Animated cassette tape display widget.
"""

import tkinter as tk
from tkinter import Canvas
import math
from typing import Optional

from .theme import COLORS, FONTS, DIMENSIONS, ANIMATION


class CassetteDisplay(tk.Frame):
    """
    A visual cassette tape display with animated reels.

    Features:
    - Cassette body with transparent window
    - Two animated reels with spokes
    - Tape strip visualization
    - File name label
    - Playback time display
    """

    def __init__(self, parent, width: int = None, height: int = None):
        """
        Initialize cassette display.

        Args:
            parent: Parent widget
            width: Display width (default from theme)
            height: Display height (default from theme)
        """
        super().__init__(parent, bg=COLORS['bg_dark'])

        self.width = width or DIMENSIONS['cassette_width']
        self.height = height or DIMENSIONS['cassette_height']

        # State
        self._playing = False
        self._speed = 1.0
        self._file_name = "No file loaded"
        self._position_str = "0:00"
        self._duration_str = "0:00"

        # Reel animation state
        self._left_reel_angle = 0.0
        self._right_reel_angle = 0.0
        self._animation_id = None

        self._build_ui()
        self._draw_cassette()

    def _build_ui(self):
        """Build the widget UI."""
        # Main canvas
        self.canvas = Canvas(
            self,
            width=self.width,
            height=self.height,
            bg=COLORS['bg_dark'],
            highlightthickness=0,
        )
        self.canvas.pack(padx=10, pady=10)

    def _draw_cassette(self):
        """Draw the complete cassette."""
        self.canvas.delete('all')

        cx = self.width // 2
        cy = self.height // 2

        # Cassette body dimensions
        body_width = self.width - 40
        body_height = self.height - 30
        body_x1 = (self.width - body_width) // 2
        body_y1 = (self.height - body_height) // 2
        body_x2 = body_x1 + body_width
        body_y2 = body_y1 + body_height

        # Shadow
        self._draw_rounded_rect(
            body_x1 + 4, body_y1 + 4,
            body_x2 + 4, body_y2 + 4,
            radius=12,
            fill=COLORS['shadow'],
            outline='',
        )

        # Main cassette body
        self._draw_rounded_rect(
            body_x1, body_y1,
            body_x2, body_y2,
            radius=12,
            fill=COLORS['cassette_body'],
            outline=COLORS['border_subtle'],
            width=1,
        )

        # Tape window
        window_width = body_width - 60
        window_height = 70
        window_x1 = cx - window_width // 2
        window_y1 = body_y1 + 25
        window_x2 = window_x1 + window_width
        window_y2 = window_y1 + window_height

        self._draw_rounded_rect(
            window_x1, window_y1,
            window_x2, window_y2,
            radius=6,
            fill=COLORS['cassette_window'],
            outline=COLORS['border_subtle'],
            width=1,
        )

        # Reel positions
        reel_radius = 28
        reel_y = window_y1 + window_height // 2
        left_reel_x = window_x1 + 45
        right_reel_x = window_x2 - 45

        # Draw tape strip between reels
        tape_y = reel_y
        self.canvas.create_line(
            left_reel_x + reel_radius - 5, tape_y - 8,
            right_reel_x - reel_radius + 5, tape_y - 8,
            fill=COLORS['tape'],
            width=3,
        )
        self.canvas.create_line(
            left_reel_x + reel_radius - 5, tape_y + 8,
            right_reel_x - reel_radius + 5, tape_y + 8,
            fill=COLORS['tape'],
            width=3,
        )

        # Draw reels
        self._draw_reel(left_reel_x, reel_y, reel_radius, self._left_reel_angle)
        self._draw_reel(right_reel_x, reel_y, reel_radius, self._right_reel_angle)

        # Label area
        label_y = window_y2 + 15
        label_height = 30

        self._draw_rounded_rect(
            window_x1 + 20, label_y,
            window_x2 - 20, label_y + label_height,
            radius=4,
            fill=COLORS['cassette_label'],
            outline='',
        )

        # File name on label
        self.canvas.create_text(
            cx, label_y + label_height // 2,
            text=self._truncate_text(self._file_name, 35),
            font=FONTS['file_name'],
            fill=COLORS['text_primary'],
            anchor='center',
        )

        # Time display
        time_text = f"{self._position_str} / {self._duration_str}"
        self.canvas.create_text(
            cx, window_y1 + 12,
            text=time_text,
            font=FONTS['label_small'],
            fill=COLORS['text_secondary'],
            anchor='center',
        )

        # Playing indicator
        if self._playing:
            indicator_x = window_x2 - 15
            indicator_y = window_y1 + 12
            self.canvas.create_oval(
                indicator_x - 4, indicator_y - 4,
                indicator_x + 4, indicator_y + 4,
                fill=COLORS['accent'],
                outline='',
            )

    def _draw_reel(self, cx: int, cy: int, radius: int, angle: float):
        """Draw a single reel with spokes."""
        # Outer ring
        self.canvas.create_oval(
            cx - radius, cy - radius,
            cx + radius, cy + radius,
            fill=COLORS['reel_outer'],
            outline=COLORS['border_subtle'],
            width=1,
        )

        # Inner hub
        hub_radius = radius * 0.35
        self.canvas.create_oval(
            cx - hub_radius, cy - hub_radius,
            cx + hub_radius, cy + hub_radius,
            fill=COLORS['reel_inner'],
            outline='',
        )

        # Center hole
        hole_radius = radius * 0.15
        self.canvas.create_oval(
            cx - hole_radius, cy - hole_radius,
            cx + hole_radius, cy + hole_radius,
            fill=COLORS['cassette_window'],
            outline='',
        )

        # Spokes (6 spokes)
        num_spokes = 6
        spoke_inner = radius * 0.4
        spoke_outer = radius * 0.85

        for i in range(num_spokes):
            spoke_angle = angle + (i * 360 / num_spokes)
            angle_rad = math.radians(spoke_angle)

            x1 = cx + spoke_inner * math.cos(angle_rad)
            y1 = cy + spoke_inner * math.sin(angle_rad)
            x2 = cx + spoke_outer * math.cos(angle_rad)
            y2 = cy + spoke_outer * math.sin(angle_rad)

            self.canvas.create_line(
                x1, y1, x2, y2,
                fill=COLORS['reel_spoke'],
                width=3,
                capstyle='round',
            )

    def _draw_rounded_rect(
        self,
        x1: int, y1: int,
        x2: int, y2: int,
        radius: int = 10,
        **kwargs
    ):
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
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def _truncate_text(self, text: str, max_len: int) -> str:
        """Truncate text with ellipsis if needed."""
        if len(text) <= max_len:
            return text
        return text[:max_len - 3] + "..."

    def _animate(self):
        """Animation loop for reel rotation."""
        if not self._playing:
            self._animation_id = None
            return

        # Update reel angles
        base_speed = ANIMATION['reel_base_speed']
        speed_factor = self._speed

        # Right reel slightly faster for realism
        self._left_reel_angle += base_speed * speed_factor
        self._right_reel_angle += base_speed * speed_factor * 1.05

        # Normalize angles
        self._left_reel_angle %= 360
        self._right_reel_angle %= 360

        # Redraw
        self._draw_cassette()

        # Schedule next frame
        interval = int(1000 / ANIMATION['fps'])
        self._animation_id = self.after(interval, self._animate)

    def set_playing(self, playing: bool):
        """Set playback state."""
        was_playing = self._playing
        self._playing = playing

        if playing and not was_playing:
            # Start animation
            self._animate()
        elif not playing and was_playing:
            # Stop animation
            if self._animation_id:
                self.after_cancel(self._animation_id)
                self._animation_id = None
            self._draw_cassette()

    def set_speed(self, speed: float):
        """Set playback speed for animation."""
        self._speed = speed

    def set_file_name(self, name: str):
        """Set the displayed file name."""
        self._file_name = name
        if not self._playing:
            self._draw_cassette()

    def set_time(self, position_str: str, duration_str: str):
        """Set the time display."""
        self._position_str = position_str
        self._duration_str = duration_str
        if not self._playing:
            self._draw_cassette()

    def reset(self):
        """Reset display to initial state."""
        self._playing = False
        self._left_reel_angle = 0.0
        self._right_reel_angle = 0.0
        self._file_name = "No file loaded"
        self._position_str = "0:00"
        self._duration_str = "0:00"

        if self._animation_id:
            self.after_cancel(self._animation_id)
            self._animation_id = None

        self._draw_cassette()
