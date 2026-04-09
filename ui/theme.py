"""
Theme constants for the cassette player UI.
"""

# Color palette - dark matte industrial
COLORS = {
    # Backgrounds
    'bg_dark': '#1a1a1a',
    'bg_panel': '#252525',
    'bg_elevated': '#2d2d2d',

    # Cassette colors
    'cassette_body': '#2a2a2a',
    'cassette_window': '#1a1a1a',
    'cassette_label': '#3a3a3a',
    'reel_outer': '#333333',
    'reel_inner': '#1a1a1a',
    'reel_spoke': '#444444',
    'tape': '#1a1a1a',

    # Text
    'text_primary': '#e0e0e0',
    'text_secondary': '#808080',
    'text_muted': '#606060',

    # Accent
    'accent': '#5a9fcf',
    'accent_dim': '#3d6d8f',
    'accent_glow': '#7ab8e8',

    # Controls
    'knob_body': '#3a3a3a',
    'knob_ring': '#4a4a4a',
    'knob_pointer': '#e0e0e0',
    'knob_active': '#5a9fcf',

    # Buttons
    'button_bg': '#333333',
    'button_hover': '#404040',
    'button_active': '#5a9fcf',
    'button_text': '#e0e0e0',

    # Borders and shadows
    'border_subtle': '#3a3a3a',
    'shadow': '#0a0a0a',
}

# Typography
FONTS = {
    'label': ('Segoe UI', 9),
    'label_small': ('Segoe UI', 8),
    'value': ('Consolas', 10),
    'title': ('Segoe UI', 11, 'bold'),
    'file_name': ('Segoe UI', 10),
}

# Dimensions
DIMENSIONS = {
    'window_width': 600,
    'window_height': 520,
    'padding': 15,
    'knob_size_large': 80,
    'knob_size_medium': 65,
    'knob_size_small': 55,
    'button_height': 36,
    'button_width': 70,
    'cassette_width': 380,
    'cassette_height': 180,
}

# Animation
ANIMATION = {
    'fps': 30,
    'reel_base_speed': 3.0,  # degrees per frame at 1.0x speed
}
