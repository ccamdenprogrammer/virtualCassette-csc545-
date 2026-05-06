"""
Theme constants for the cassette player UI.
"""

# Color palette inspired by vintage multitrack cassette recorders
COLORS = {
    # Backgrounds and chassis
    'bg_dark': '#132334',
    'bg_panel': '#35506a',
    'bg_elevated': '#47657f',
    'machine_top': '#506f8d',
    'machine_body': '#405e7c',
    'machine_side': '#314b63',
    'cassette_section_bg': '#284158',
    'strip_bg': '#5f7e9a',
    'strip_selected': '#7697b4',

    # Cassette colors
    'cassette_body': '#1d2b38',
    'cassette_window': '#0f1720',
    'cassette_label': '#6d879d',
    'reel_outer': '#9ea7b2',
    'reel_inner': '#2a333d',
    'reel_spoke': '#56606b',
    'tape': '#11161c',

    # Text
    'text_primary': '#edf4fb',
    'text_secondary': '#b7c5d4',
    'text_muted': '#cfdae5',
    'text_bright': '#ffffff',

    # Accent
    'accent': '#f1b84c',
    'accent_dim': '#c18f34',
    'accent_glow': '#ffd67f',
    'meter_fill': '#ff7c70',
    'meter_fill_right': '#ffd36b',
    'meter_bg': '#2b3948',
    'meter_slot': '#101820',
    'meter_clip': '#ff4d4d',
    'meter_clip_off': '#4f1f1f',

    # Controls
    'knob_body': '#c7c7c2',
    'knob_ring': '#8e8d8a',
    'knob_pointer': '#5ba0d6',
    'knob_active': '#f2c770',
    'fader_slot': '#172433',
    'fader_cap': '#f3efe6',

    # Buttons
    'button_bg': '#233243',
    'button_bg_subtle': '#31475d',
    'button_hover': '#415d77',
    'button_active': '#f1b84c',
    'button_text': '#f3f7fb',
    'transport_key': '#ece7dc',
    'transport_key_active': '#d8b66c',
    'transport_text': '#263241',

    # Borders and shadows
    'border_subtle': '#21354a',
    'shadow': '#09131d',
}

# Typography
FONTS = {
    'label': ('Segoe UI Semibold', 9),
    'label_small': ('Segoe UI', 8),
    'value': ('Consolas', 10),
    'value_small': ('Consolas', 9),
    'title': ('Segoe UI Semibold', 11, 'bold'),
    'display': ('Bahnschrift SemiBold', 15, 'bold'),
    'file_name': ('Segoe UI Semibold', 10),
}

# Dimensions
DIMENSIONS = {
    'window_width': 1580,
    'window_height': 880,
    'padding': 15,
    'knob_size_large': 80,
    'knob_size_medium': 65,
    'knob_size_small': 55,
    'knob_size_master': 36,
    'knob_size_track': 34,
    'button_height': 36,
    'button_width': 70,
    'cassette_width': 332,
    'cassette_height': 210,
    'track_strip_width': 148,
    'track_strip_height': 760,
    'machine_right_width': 690,
}

# Animation
ANIMATION = {
    'fps': 30,
    'reel_base_speed': 3.0,  # degrees per frame at 1.0x speed
}
