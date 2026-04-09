"""
Rotary knob widget for parameter control.
"""

import tkinter as tk
from tkinter import Canvas
import math
from typing import Callable, Optional

from .theme import COLORS, FONTS


class KnobWidget(tk.Frame):
    """
    A rotary knob control widget.

    Features:
    - Circular knob with pointer indicator
    - Drag to change value (vertical motion)
    - Label and value display
    - Hover and active states
    """

    def __init__(
        self,
        parent,
        label: str,
        min_val: float,
        max_val: float,
        initial_val: float,
        callback: Callable[[float], None],
        formatter: Callable[[float], str] = None,
        size: int = 65,
        sensitivity: float = 0.005,
    ):
        """
        Initialize knob widget.

        Args:
            parent: Parent widget
            label: Label text
            min_val: Minimum value
            max_val: Maximum value
            initial_val: Initial value
            callback: Function called when value changes
            formatter: Function to format value for display
            size: Knob diameter in pixels
            sensitivity: Drag sensitivity multiplier
        """
        super().__init__(parent, bg=COLORS['bg_panel'])

        self.min_val = min_val
        self.max_val = max_val
        self.value = initial_val
        self.callback = callback
        self.formatter = formatter or (lambda v: f"{v:.2f}")
        self.size = size
        self.sensitivity = sensitivity

        # Angle range (in degrees)
        self.start_angle = 135  # Bottom-left
        self.end_angle = 405    # Bottom-right (wrap around)
        self.angle_range = self.end_angle - self.start_angle

        # State
        self._dragging = False
        self._drag_start_y = 0
        self._drag_start_value = 0
        self._hover = False

        self._build_ui()
        self._draw_knob()

    def _build_ui(self):
        """Build the widget UI."""
        # Label above knob
        self.label = tk.Label(
            self,
            text=self.formatter(self.value),
            font=FONTS['label_small'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel'],
        )
        self.label.pack(pady=(0, 3))

        # Canvas for knob
        canvas_size = self.size + 10
        self.canvas = Canvas(
            self,
            width=canvas_size,
            height=canvas_size,
            bg=COLORS['bg_panel'],
            highlightthickness=0,
        )
        self.canvas.pack()

        # Value display below knob
        self.value_label = tk.Label(
            self,
            text=self.formatter(self.value),
            font=FONTS['value'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_panel'],
        )
        self.value_label.pack(pady=(3, 0))

        # Update label to show parameter name, value label shows value
        self.label.config(text=self._get_label_text())

        # Bind events
        self.canvas.bind('<Button-1>', self._on_mouse_down)
        self.canvas.bind('<B1-Motion>', self._on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_mouse_up)
        self.canvas.bind('<Enter>', self._on_enter)
        self.canvas.bind('<Leave>', self._on_leave)

    def _get_label_text(self) -> str:
        """Get the label text."""
        # Extract label from formatter or use generic
        return getattr(self, '_label_text', 'PARAM')

    def _draw_knob(self):
        """Draw the knob on canvas."""
        self.canvas.delete('all')

        cx = (self.size + 10) // 2
        cy = (self.size + 10) // 2
        radius = self.size // 2

        # Outer ring (shadow effect)
        self.canvas.create_oval(
            cx - radius - 2, cy - radius - 2,
            cx + radius + 2, cy + radius + 2,
            fill=COLORS['shadow'],
            outline='',
        )

        # Main knob body
        body_color = COLORS['knob_active'] if self._dragging else COLORS['knob_body']
        ring_color = COLORS['accent'] if self._hover or self._dragging else COLORS['knob_ring']

        self.canvas.create_oval(
            cx - radius, cy - radius,
            cx + radius, cy + radius,
            fill=body_color,
            outline=ring_color,
            width=2,
        )

        # Inner circle
        inner_radius = radius * 0.6
        self.canvas.create_oval(
            cx - inner_radius, cy - inner_radius,
            cx + inner_radius, cy + inner_radius,
            fill=COLORS['bg_elevated'],
            outline='',
        )

        # Pointer line
        angle = self._value_to_angle(self.value)
        angle_rad = math.radians(angle)

        pointer_inner = radius * 0.3
        pointer_outer = radius * 0.85

        x1 = cx + pointer_inner * math.cos(angle_rad)
        y1 = cy - pointer_inner * math.sin(angle_rad)
        x2 = cx + pointer_outer * math.cos(angle_rad)
        y2 = cy - pointer_outer * math.sin(angle_rad)

        pointer_color = COLORS['accent'] if self._hover or self._dragging else COLORS['knob_pointer']
        self.canvas.create_line(
            x1, y1, x2, y2,
            fill=pointer_color,
            width=3,
            capstyle='round',
        )

        # Pointer dot
        dot_radius = 3
        self.canvas.create_oval(
            x2 - dot_radius, y2 - dot_radius,
            x2 + dot_radius, y2 + dot_radius,
            fill=pointer_color,
            outline='',
        )

    def _value_to_angle(self, value: float) -> float:
        """Convert value to angle in degrees."""
        normalized = (value - self.min_val) / (self.max_val - self.min_val)
        # Map to angle range (note: canvas Y is inverted, so we go clockwise)
        angle = self.start_angle + (1 - normalized) * self.angle_range
        return angle

    def _on_mouse_down(self, event):
        """Handle mouse button press."""
        self._dragging = True
        self._drag_start_y = event.y
        self._drag_start_value = self.value
        self._draw_knob()

    def _on_mouse_drag(self, event):
        """Handle mouse drag."""
        if not self._dragging:
            return

        # Calculate value change based on vertical drag
        dy = self._drag_start_y - event.y  # Inverted: up = increase
        value_range = self.max_val - self.min_val
        delta = dy * self.sensitivity * value_range

        new_value = self._drag_start_value + delta
        new_value = max(self.min_val, min(self.max_val, new_value))

        if new_value != self.value:
            self.value = new_value
            self._update_display()
            self.callback(self.value)

    def _on_mouse_up(self, event):
        """Handle mouse button release."""
        self._dragging = False
        self._draw_knob()

    def _on_enter(self, event):
        """Handle mouse enter."""
        self._hover = True
        self._draw_knob()
        self.canvas.config(cursor='hand2')

    def _on_leave(self, event):
        """Handle mouse leave."""
        self._hover = False
        if not self._dragging:
            self._draw_knob()
        self.canvas.config(cursor='')

    def _update_display(self):
        """Update the value display."""
        self.value_label.config(text=self.formatter(self.value))
        self._draw_knob()

    def set_value(self, value: float):
        """Set the knob value programmatically."""
        self.value = max(self.min_val, min(self.max_val, value))
        self._update_display()

    def get_value(self) -> float:
        """Get the current value."""
        return self.value


def create_knob(
    parent,
    label: str,
    min_val: float,
    max_val: float,
    initial_val: float,
    callback: Callable[[float], None],
    unit: str = '',
    size: int = 65,
    decimals: int = 2,
) -> KnobWidget:
    """
    Factory function to create a knob with common formatting.

    Args:
        parent: Parent widget
        label: Parameter label
        min_val: Minimum value
        max_val: Maximum value
        initial_val: Initial value
        callback: Value change callback
        unit: Unit suffix (e.g., 'ms', '%', 'dB')
        size: Knob size
        decimals: Decimal places for display

    Returns:
        Configured KnobWidget
    """
    def formatter(v):
        if decimals == 0:
            return f"{int(v)}{unit}"
        else:
            return f"{v:.{decimals}f}{unit}"

    knob = KnobWidget(
        parent,
        label=label,
        min_val=min_val,
        max_val=max_val,
        initial_val=initial_val,
        callback=callback,
        formatter=formatter,
        size=size,
    )
    knob._label_text = label
    knob.label.config(text=label)

    return knob
