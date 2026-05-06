"""
Portastudio-style main application window.
"""

import logging
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

import config
from models.transport import TransportState
from .cassette_display import CassetteDisplay
from .knob_widget import create_knob
from .theme import COLORS, DIMENSIONS, FONTS

if TYPE_CHECKING:
    from app import App

logger = logging.getLogger(__name__)


class MainWindow:
    """Main application window styled like a multitrack tape recorder."""

    def __init__(self, root: tk.Tk, app: "App"):
        self.root = root
        self.app = app

        self._update_interval = 100
        self._last_track_signature: tuple[tuple[str, str], ...] = ()
        self._track_strips: dict[str, dict[str, object]] = {}
        self._suspend_master_callbacks = False
        self._updating_tracks = False

        self.root.title("CSC545 Project")
        self.root.geometry(
            f"{DIMENSIONS['window_width']}x{DIMENSIONS['window_height']}"
        )
        self.root.minsize(1320, 760)
        self.root.configure(bg=COLORS["bg_dark"])
        self.root.resizable(True, True)

        self._build_ui()
        self._bind_scroll_events()
        self._schedule_update()

        logger.info("Portastudio window initialized")

    def _build_ui(self):
        self.main_frame = tk.Frame(self.root, bg=COLORS["bg_dark"])
        self.main_frame.pack(fill="both", expand=True, padx=18, pady=16)

        self._create_header()
        self._create_deck_surface()
        self._create_status_bar()

    def _create_header(self):
        self.header = tk.Frame(
            self.main_frame,
            bg=COLORS["machine_top"],
            padx=18,
            pady=14,
            relief="raised",
            bd=2,
        )
        self.header.pack(fill="x", pady=(0, 14))

        title_wrap = tk.Frame(self.header, bg=COLORS["machine_top"])
        title_wrap.pack(side="left")

        tk.Label(
            title_wrap,
            text="CSC545 PROJECT",
            font=FONTS["display"],
            fg=COLORS["text_bright"],
            bg=COLORS["machine_top"],
        ).pack(anchor="w")

        self.selection_badge = tk.Label(
            title_wrap,
            text="No tracks loaded",
            font=FONTS["label_small"],
            fg=COLORS["text_muted"],
            bg=COLORS["machine_top"],
        )
        self.selection_badge.pack(anchor="w", pady=(4, 0))

        button_wrap = tk.Frame(self.header, bg=COLORS["machine_top"])
        button_wrap.pack(side="right")

        button_specs = [
            ("Load", self._on_open_file, False),
            ("Export", self._on_export, False),
            ("Separate", self._on_separate_stems, False),
            ("Load Stems", self._on_load_stems, False),
            ("Load Existing", self._on_load_existing_stems, False),
            ("Select All", self._on_select_all, True),
            ("Clear Sel", self._on_deselect_all, True),
            ("Remove Sel", self._on_remove_selected, True),
        ]
        for text, command, subtle in button_specs:
            self._make_button(
                button_wrap,
                text=text,
                command=command,
                width=11 if len(text) > 8 else 9,
                subtle=subtle,
            ).pack(side="left", padx=4)

    def _create_deck_surface(self):
        self.deck = tk.Frame(
            self.main_frame,
            bg=COLORS["machine_body"],
            relief="raised",
            bd=3,
            padx=18,
            pady=18,
        )
        self.deck.pack(fill="both", expand=True)

        self.track_area = tk.Frame(self.deck, bg=COLORS["machine_body"])
        self.track_area.pack(side="left", fill="both", expand=True, padx=(0, 18))

        self.machine_area = tk.Frame(
            self.deck,
            bg=COLORS["machine_side"],
            width=DIMENSIONS["machine_right_width"],
            padx=14,
            pady=14,
            relief="sunken",
            bd=2,
        )
        self.machine_area.pack(side="right", fill="y")
        self.machine_area.pack_propagate(False)

        self._create_track_scroller()
        self._create_machine_area()

    def _create_track_scroller(self):
        header = tk.Frame(self.track_area, bg=COLORS["machine_body"])
        header.pack(fill="x", pady=(0, 10))

        tk.Label(
            header,
            text="CHANNEL STRIPS",
            font=FONTS["title"],
            fg=COLORS["text_bright"],
            bg=COLORS["machine_body"],
        ).pack(side="left")

        tk.Label(
            header,
            text="Scroll horizontally as tracks are added",
            font=FONTS["label_small"],
            fg=COLORS["text_muted"],
            bg=COLORS["machine_body"],
        ).pack(side="right")

        self.track_canvas = tk.Canvas(
            self.track_area,
            bg=COLORS["machine_body"],
            highlightthickness=0,
            bd=0,
            height=DIMENSIONS["track_strip_height"],
        )
        self.track_canvas.pack(fill="both", expand=True)

        self.track_scrollbar = tk.Scrollbar(
            self.track_area,
            orient="horizontal",
            command=self.track_canvas.xview,
        )
        self.track_scrollbar.pack(fill="x", pady=(8, 0))
        self.track_canvas.configure(xscrollcommand=self.track_scrollbar.set)

        self.track_strip_frame = tk.Frame(self.track_canvas, bg=COLORS["machine_body"])
        self.track_canvas_window = self.track_canvas.create_window(
            (0, 0),
            window=self.track_strip_frame,
            anchor="nw",
        )

        self.track_strip_frame.bind("<Configure>", self._on_track_frame_configure)
        self.track_canvas.bind("<Configure>", self._on_track_canvas_configure)

    def _create_machine_area(self):
        top_info = tk.Frame(self.machine_area, bg=COLORS["machine_side"])
        top_info.pack(fill="x", pady=(0, 12))

        tk.Label(
            top_info,
            text="MASTER SECTION",
            font=FONTS["title"],
            fg=COLORS["text_bright"],
            bg=COLORS["machine_side"],
        ).pack(anchor="w")

        tk.Label(
            top_info,
            text="Selected-track controls plus cassette transport",
            font=FONTS["label_small"],
            fg=COLORS["text_muted"],
            bg=COLORS["machine_side"],
        ).pack(anchor="w", pady=(4, 0))

        lower_machine = tk.Frame(self.machine_area, bg=COLORS["machine_side"])
        lower_machine.pack(side="bottom", fill="x")

        self.master_strip = tk.Frame(
            lower_machine,
            bg=COLORS["strip_bg"],
            padx=12,
            pady=14,
            relief="raised",
            bd=2,
        )
        self.master_strip.pack(side="left", fill="y", padx=(0, 14))

        self.cassette_section = tk.Frame(
            lower_machine,
            bg=COLORS["cassette_section_bg"],
            padx=12,
            pady=12,
            relief="sunken",
            bd=2,
        )
        self.cassette_section.pack(side="right", fill="y")

        self._create_master_strip()
        self._create_cassette_section()

    def _create_master_strip(self):
        tk.Label(
            self.master_strip,
            text="MASTER FX",
            font=FONTS["title"],
            fg=COLORS["text_bright"],
            bg=COLORS["strip_bg"],
        ).pack(anchor="center", pady=(0, 8))

        self.master_target_label = tk.Label(
            self.master_strip,
            text="Affects selected tracks",
            font=FONTS["label_small"],
            fg=COLORS["text_muted"],
            bg=COLORS["strip_bg"],
        )
        self.master_target_label.pack(anchor="center", pady=(0, 10))

        control_cluster = tk.Frame(self.master_strip, bg=COLORS["strip_bg"], height=390)
        control_cluster.pack(fill="x", pady=(0, 10))
        control_cluster.pack_propagate(False)

        knob_column = tk.Frame(control_cluster, bg=COLORS["strip_bg"])
        knob_column.pack(side="left", fill="y")

        self.master_meter_canvas, self.master_meter_ids = self._create_stereo_meter(
            control_cluster,
            height=300,
        )
        self.master_meter_canvas.pack(side="right", fill="y", padx=(10, 2))

        knob_specs = [
            (
                "SPEED",
                config.SPEED_MIN,
                config.SPEED_MAX,
                config.DEFAULT_SPEED,
                self._on_speed_change,
                "x",
                2,
            ),
            (
                "ECHO MIX",
                0.0,
                1.0,
                config.DEFAULT_ECHO_MIX,
                self._on_echo_mix_change,
                "%",
                0,
            ),
            (
                "DELAY",
                config.ECHO_DELAY_MIN_MS,
                config.ECHO_DELAY_MAX_MS,
                config.DEFAULT_ECHO_DELAY_MS,
                self._on_echo_delay_change,
                "ms",
                0,
            ),
            (
                "FEEDBACK",
                0.0,
                config.ECHO_FEEDBACK_MAX,
                config.DEFAULT_ECHO_FEEDBACK,
                self._on_echo_feedback_change,
                "%",
                0,
            ),
        ]

        self.master_knobs: dict[str, object] = {}
        for label, min_val, max_val, initial, callback, unit, decimals in knob_specs:
            knob = create_knob(
                knob_column,
                label=label,
                min_val=min_val,
                max_val=max_val,
                initial_val=initial,
                callback=callback,
                unit=unit,
                size=DIMENSIONS["knob_size_master"],
                decimals=decimals,
            )
            if label in {"ECHO MIX", "FEEDBACK"}:
                knob.formatter = lambda v: f"{int(v * 100)}%"
                knob._update_display()
            knob.pack(pady=2, anchor="w")
            self.master_knobs[label] = knob

        slider_block = tk.Frame(self.master_strip, bg=COLORS["strip_bg"])
        slider_block.pack(side="bottom", fill="x", pady=(6, 0))

        tk.Label(
            slider_block,
            text="LEVEL L / R",
            font=FONTS["label_small"],
            fg=COLORS["text_muted"],
            bg=COLORS["strip_bg"],
        ).pack()

        value_row = tk.Frame(slider_block, bg=COLORS["strip_bg"])
        value_row.pack(pady=(2, 6))

        self.master_level_left_value = tk.Label(
            value_row,
            text="L 0.0 dB",
            font=FONTS["value_small"],
            fg=COLORS["text_bright"],
            bg=COLORS["strip_bg"],
        )
        self.master_level_left_value.pack(side="left", padx=4)

        self.master_level_right_value = tk.Label(
            value_row,
            text="R 0.0 dB",
            font=FONTS["value_small"],
            fg=COLORS["text_bright"],
            bg=COLORS["strip_bg"],
        )
        self.master_level_right_value.pack(side="left", padx=4)

        slider_row = tk.Frame(slider_block, bg=COLORS["strip_bg"])
        slider_row.pack()

        self.master_volume_left = tk.Scale(
            slider_row,
            from_=config.OUTPUT_GAIN_MAX_DB,
            to=config.OUTPUT_GAIN_MIN_DB,
            resolution=0.5,
            showvalue=False,
            length=180,
            sliderlength=28,
            width=20,
            highlightthickness=0,
            bd=0,
            troughcolor=COLORS["fader_slot"],
            bg=COLORS["strip_bg"],
            fg=COLORS["text_primary"],
            activebackground=COLORS["fader_cap"],
            command=lambda value: self._on_gain_left_change(float(value)),
        )
        self.master_volume_left.pack(side="left", padx=6)

        self.master_volume_right = tk.Scale(
            slider_row,
            from_=config.OUTPUT_GAIN_MAX_DB,
            to=config.OUTPUT_GAIN_MIN_DB,
            resolution=0.5,
            showvalue=False,
            length=180,
            sliderlength=28,
            width=20,
            highlightthickness=0,
            bd=0,
            troughcolor=COLORS["fader_slot"],
            bg=COLORS["strip_bg"],
            fg=COLORS["text_primary"],
            activebackground=COLORS["fader_cap"],
            command=lambda value: self._on_gain_right_change(float(value)),
        )
        self.master_volume_right.pack(side="left", padx=6)

    def _create_cassette_section(self):
        tk.Label(
            self.cassette_section,
            text="TAPE WELL",
            font=FONTS["title"],
            fg=COLORS["text_bright"],
            bg=COLORS["cassette_section_bg"],
        ).pack(anchor="w")

        self.cassette_subtitle = tk.Label(
            self.cassette_section,
            text="No tape loaded",
            font=FONTS["label_small"],
            fg=COLORS["text_muted"],
            bg=COLORS["cassette_section_bg"],
        )
        self.cassette_subtitle.pack(anchor="w", pady=(2, 10))

        self.cassette_display = CassetteDisplay(
            self.cassette_section,
            width=DIMENSIONS["cassette_width"],
            height=DIMENSIONS["cassette_height"],
        )
        self.cassette_display.pack(anchor="e", pady=(0, 10))

        self.transport_status = tk.Label(
            self.cassette_section,
            text="Stopped",
            font=FONTS["label"],
            fg=COLORS["text_bright"],
            bg=COLORS["cassette_section_bg"],
        )
        self.transport_status.pack(anchor="center", pady=(0, 8))

        self.transport_buttons = tk.Frame(
            self.cassette_section,
            bg=COLORS["cassette_section_bg"],
        )
        self.transport_buttons.pack(anchor="center", pady=(0, 8))

        self.play_btn = self._make_transport_button("PLAY", self._on_play)
        self.pause_btn = self._make_transport_button("PAUSE", self._on_pause)
        self.stop_btn = self._make_transport_button("STOP", self._on_stop)
        self.loop_btn = self._make_transport_button("LOOP", self._on_loop_toggle)

        for button in (self.play_btn, self.pause_btn, self.stop_btn, self.loop_btn):
            button.pack(side="left", padx=6)

    def _create_status_bar(self):
        self.status_bar = tk.Frame(
            self.main_frame,
            bg=COLORS["machine_top"],
            padx=16,
            pady=8,
            relief="raised",
            bd=2,
        )
        self.status_bar.pack(fill="x", pady=(14, 0))

        self.status_label = tk.Label(
            self.status_bar,
            text="Ready",
            font=FONTS["label"],
            fg=COLORS["text_bright"],
            bg=COLORS["machine_top"],
        )
        self.status_label.pack(side="left")

    def _make_button(
        self,
        parent,
        text: str,
        command,
        width: int = 9,
        subtle: bool = False,
    ):
        bg = COLORS["button_bg_subtle"] if subtle else COLORS["button_bg"]
        return tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            bg=bg,
            fg=COLORS["button_text"],
            activebackground=COLORS["button_active"],
            activeforeground=COLORS["text_bright"],
            font=FONTS["label"],
            relief="raised",
            bd=2,
            padx=4,
            pady=4,
        )

    def _make_transport_button(self, text: str, command):
        return tk.Button(
            self.transport_buttons,
            text=text,
            command=command,
            width=8,
            height=2,
            bg=COLORS["transport_key"],
            fg=COLORS["transport_text"],
            activebackground=COLORS["transport_key_active"],
            font=FONTS["label"],
            relief="raised",
            bd=3,
        )

    def _create_stereo_meter(self, parent, height: int):
        """Create a stereo meter canvas and return its item ids."""
        canvas = tk.Canvas(
            parent,
            width=38,
            height=height,
            bg=COLORS["meter_bg"],
            highlightthickness=0,
            bd=0,
        )
        left_x1, left_x2 = 6, 14
        right_x1, right_x2 = 22, 30
        clip_size = 6
        clip_left = canvas.create_rectangle(
            left_x1, 4, left_x2, 4 + clip_size,
            fill=COLORS["meter_clip_off"],
            outline="",
        )
        clip_right = canvas.create_rectangle(
            right_x1, 4, right_x2, 4 + clip_size,
            fill=COLORS["meter_clip_off"],
            outline="",
        )
        meter_top = 14
        meter_bottom = height - 4
        canvas.create_rectangle(left_x1, meter_top, left_x2, meter_bottom, fill=COLORS["meter_slot"], outline="")
        canvas.create_rectangle(right_x1, meter_top, right_x2, meter_bottom, fill=COLORS["meter_slot"], outline="")
        left_fill = canvas.create_rectangle(
            left_x1, meter_bottom, left_x2, meter_bottom,
            fill=COLORS["meter_fill"],
            outline="",
        )
        right_fill = canvas.create_rectangle(
            right_x1, meter_bottom, right_x2, meter_bottom,
            fill=COLORS["meter_fill_right"],
            outline="",
        )
        return canvas, {
            "left_fill": left_fill,
            "right_fill": right_fill,
            "clip_left": clip_left,
            "clip_right": clip_right,
            "meter_top": meter_top,
            "meter_bottom": meter_bottom,
            "left_x1": left_x1,
            "left_x2": left_x2,
            "right_x1": right_x1,
            "right_x2": right_x2,
        }

    def _update_stereo_meter(self, canvas, meter_ids, meter_data: dict[str, object]):
        """Update a stereo meter from the latest peak/clip snapshot."""
        left = float(meter_data.get("left", 0.0))
        right = float(meter_data.get("right", 0.0))
        clip_left = bool(meter_data.get("clip_left", False))
        clip_right = bool(meter_data.get("clip_right", False))

        meter_top = meter_ids["meter_top"]
        meter_bottom = meter_ids["meter_bottom"]
        meter_height = meter_bottom - meter_top

        left_top = meter_bottom - int(max(0.0, min(1.0, left)) * meter_height)
        right_top = meter_bottom - int(max(0.0, min(1.0, right)) * meter_height)

        canvas.coords(
            meter_ids["left_fill"],
            meter_ids["left_x1"], left_top,
            meter_ids["left_x2"], meter_bottom,
        )
        canvas.coords(
            meter_ids["right_fill"],
            meter_ids["right_x1"], right_top,
            meter_ids["right_x2"], meter_bottom,
        )
        canvas.itemconfigure(
            meter_ids["clip_left"],
            fill=COLORS["meter_clip"] if clip_left else COLORS["meter_clip_off"],
        )
        canvas.itemconfigure(
            meter_ids["clip_right"],
            fill=COLORS["meter_clip"] if clip_right else COLORS["meter_clip_off"],
        )

    def _bind_scroll_events(self):
        self.track_canvas.bind("<MouseWheel>", self._on_track_mousewheel)
        self.track_canvas.bind("<Shift-MouseWheel>", self._on_track_mousewheel)
        self.track_canvas.bind("<Button-4>", self._on_track_mousewheel)
        self.track_canvas.bind("<Button-5>", self._on_track_mousewheel)

    def _on_track_mousewheel(self, event):
        if hasattr(event, "delta") and event.delta:
            self.track_canvas.xview_scroll(int(-event.delta / 120), "units")
        elif getattr(event, "num", None) == 4:
            self.track_canvas.xview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            self.track_canvas.xview_scroll(1, "units")

    def _on_track_frame_configure(self, event):
        self.track_canvas.configure(scrollregion=self.track_canvas.bbox("all"))

    def _on_track_canvas_configure(self, event):
        self.track_canvas.itemconfigure(self.track_canvas_window, height=event.height)

    def _set_status(self, text: str):
        self.status_label.config(text=text)

    def _format_time(self, seconds: float) -> str:
        total = max(0, int(seconds))
        minutes = total // 60
        secs = total % 60
        return f"{minutes}:{secs:02d}"

    def _truncate_name(self, name: str, max_len: int = 18) -> str:
        if len(name) <= max_len:
            return name
        return name[: max_len - 3] + "..."

    def _is_selected(self, file_id: str) -> bool:
        return file_id in self.app.get_selected_files()

    def _toggle_track_selection(self, file_id: str):
        if self._is_selected(file_id):
            self.app.deselect_file(file_id)
        else:
            self.app.select_file(file_id)
        self._sync_master_controls()
        self._refresh_selection_badge()
        self._update_track_strip_values()

    def _create_track_strip(self, audio_file, index: int):
        strip = tk.Frame(
            self.track_strip_frame,
            bg=COLORS["strip_bg"],
            width=DIMENSIONS["track_strip_width"],
            padx=8,
            pady=10,
            relief="raised",
            bd=2,
        )
        strip.pack(side="left", fill="y", padx=(0, 10))
        strip.pack_propagate(False)

        track_num = tk.Label(
            strip,
            text=f"{index + 1}",
            font=FONTS["display"],
            fg=COLORS["text_bright"],
            bg=COLORS["strip_bg"],
        )
        track_num.pack(anchor="center")

        name_label = tk.Label(
            strip,
            text=self._truncate_name(audio_file.filename),
            font=FONTS["label_small"],
            fg=COLORS["text_primary"],
            bg=COLORS["strip_bg"],
            wraplength=DIMENSIONS["track_strip_width"] - 18,
            justify="center",
        )
        name_label.pack(fill="x", pady=(4, 6))

        select_btn = tk.Button(
            strip,
            text="SELECT",
            command=lambda fid=audio_file.id: self._toggle_track_selection(fid),
            width=10,
            bg=COLORS["button_bg_subtle"],
            fg=COLORS["button_text"],
            activebackground=COLORS["button_active"],
            font=FONTS["label_small"],
            relief="raised",
            bd=2,
        )
        select_btn.pack(pady=(0, 8))

        control_cluster = tk.Frame(strip, bg=COLORS["strip_bg"], height=380)
        control_cluster.pack(fill="x", pady=(0, 8))
        control_cluster.pack_propagate(False)

        knob_column = tk.Frame(control_cluster, bg=COLORS["strip_bg"])
        knob_column.pack(side="left", fill="y")

        meter, meter_ids = self._create_stereo_meter(control_cluster, height=300)
        meter.pack(side="right", fill="y", padx=(8, 2))

        fader_block = tk.Frame(strip, bg=COLORS["strip_bg"])
        fader_block.pack(side="bottom", fill="both", expand=True, pady=(2, 0))

        tk.Label(
            fader_block,
            text="LEVEL",
            font=FONTS["label_small"],
            fg=COLORS["text_muted"],
            bg=COLORS["strip_bg"],
        ).pack()

        volume_value = tk.Label(
            fader_block,
            text="100%",
            font=FONTS["value_small"],
            fg=COLORS["text_bright"],
            bg=COLORS["strip_bg"],
        )
        volume_value.pack(pady=(2, 4))

        volume_scale = tk.Scale(
            fader_block,
            from_=config.TRACK_VOLUME_MAX,
            to=config.TRACK_VOLUME_MIN,
            resolution=0.01,
            showvalue=False,
            length=220,
            sliderlength=22,
            width=24,
            highlightthickness=0,
            bd=0,
            troughcolor=COLORS["fader_slot"],
            bg=COLORS["strip_bg"],
            activebackground=COLORS["fader_cap"],
            command=lambda value, fid=audio_file.id: self._on_track_change(
                fid, "track_volume", float(value)
            ),
        )
        volume_scale.pack()

        knob_specs = [
            ("speed", "SPD", config.SPEED_MIN, config.SPEED_MAX, config.DEFAULT_SPEED, "x", 2),
            ("echo_mix", "MIX", 0.0, 1.0, config.DEFAULT_ECHO_MIX, "%", 0),
            (
                "echo_delay_ms",
                "DLY",
                config.ECHO_DELAY_MIN_MS,
                config.ECHO_DELAY_MAX_MS,
                config.DEFAULT_ECHO_DELAY_MS,
                "ms",
                0,
            ),
            (
                "echo_feedback",
                "FBK",
                0.0,
                config.ECHO_FEEDBACK_MAX,
                config.DEFAULT_ECHO_FEEDBACK,
                "%",
                0,
            ),
        ]

        strip_controls: dict[str, object] = {
            "frame": strip,
            "select_btn": select_btn,
            "name_label": name_label,
            "track_num": track_num,
            "meter": meter,
            "meter_ids": meter_ids,
            "track_volume_scale": volume_scale,
            "track_volume_label": volume_value,
        }

        for param_name, label, min_val, max_val, initial, unit, decimals in knob_specs:
            knob = create_knob(
                knob_column,
                label=label,
                min_val=min_val,
                max_val=max_val,
                initial_val=initial,
                callback=lambda value, fid=audio_file.id, name=param_name: self._on_track_change(
                    fid, name, value
                ),
                unit=unit,
                size=DIMENSIONS["knob_size_track"],
                decimals=decimals,
            )
            if param_name in {"echo_mix", "echo_feedback"}:
                knob.formatter = lambda v: f"{int(v * 100)}%"
                knob._update_display()
            knob.pack(pady=2, anchor="w")
            strip_controls[f"{param_name}_knob"] = knob

        self._track_strips[audio_file.id] = strip_controls

    def _rebuild_track_strips_if_needed(self):
        files = self.app.get_audio_files()
        signature = tuple((audio_file.id, audio_file.filename) for audio_file in files)
        if signature == self._last_track_signature:
            return

        for child in self.track_strip_frame.winfo_children():
            child.destroy()
        self._track_strips.clear()

        if not files:
            empty = tk.Label(
                self.track_strip_frame,
                text="Load audio to populate channel strips.",
                font=FONTS["title"],
                fg=COLORS["text_muted"],
                bg=COLORS["machine_body"],
            )
            empty.pack(anchor="center", padx=40, pady=160)
        else:
            for index, audio_file in enumerate(files):
                self._create_track_strip(audio_file, index)

        self._last_track_signature = signature

    def _format_track_value(self, name: str, value: float) -> str:
        if name == "track_volume":
            return f"{int(value * 100)}%"
        if name == "speed":
            return f"{value:.2f}x"
        if name == "echo_mix":
            return f"{int(value * 100)}%"
        if name == "echo_delay_ms":
            return f"{int(value)} ms"
        if name == "echo_feedback":
            return f"{int(value * 100)}%"
        return f"{value:.2f}"

    def _update_track_strip_values(self, metering_snapshot: dict[str, object] | None = None):
        self._updating_tracks = True
        try:
            selected = self.app.get_selected_files()
            track_metering = (metering_snapshot or {}).get("tracks", {})
            for index, audio_file in enumerate(self.app.get_audio_files()):
                strip = self._track_strips.get(audio_file.id)
                if not strip:
                    continue
                params = self.app.get_file_parameters(audio_file.id)

                is_selected = audio_file.id in selected
                strip["frame"].configure(
                    bg=COLORS["strip_selected"] if is_selected else COLORS["strip_bg"]
                )
                strip["select_btn"].configure(
                    text="SELECTED" if is_selected else "SELECT",
                    bg=COLORS["accent"] if is_selected else COLORS["button_bg_subtle"],
                    fg=COLORS["text_bright"] if is_selected else COLORS["button_text"],
                )
                strip["name_label"].configure(
                    bg=COLORS["strip_selected"] if is_selected else COLORS["strip_bg"]
                )
                strip["track_num"].configure(
                    bg=COLORS["strip_selected"] if is_selected else COLORS["strip_bg"]
                )
                strip["track_volume_scale"].configure(
                    bg=COLORS["strip_selected"] if is_selected else COLORS["strip_bg"]
                )
                strip["track_volume_label"].configure(
                    bg=COLORS["strip_selected"] if is_selected else COLORS["strip_bg"],
                    text=self._format_track_value("track_volume", params.track_volume),
                )
                strip["track_volume_scale"].set(params.track_volume)
                self._update_stereo_meter(
                    strip["meter"],
                    strip["meter_ids"],
                    track_metering.get(audio_file.id, {}),
                )

                for name in ("speed", "echo_mix", "echo_delay_ms", "echo_feedback"):
                    knob = strip[f"{name}_knob"]
                    knob.set_value(getattr(params, name))
                    knob.value_label.config(
                        text=self._format_track_value(name, getattr(params, name))
                    )
        finally:
            self._updating_tracks = False

    def _refresh_selection_badge(self):
        files = self.app.get_audio_files()
        selected_count = len(self.app.get_selected_files())
        if not files:
            self.selection_badge.config(text="No tracks loaded")
            return
        self.selection_badge.config(
            text=f"{len(files)} tracks loaded • {selected_count} selected"
        )

    def _sync_master_controls(self):
        file_id = self._get_primary_selected_file_id()
        if not file_id:
            self.master_target_label.config(text="Load tracks to use master controls")
            self.cassette_subtitle.config(text="No tape loaded")
            return

        selected_count = len(self.app.get_selected_files())
        self.master_target_label.config(
            text=f"Affects {selected_count or len(self.app.get_audio_files())} selected track(s)"
        )

        params = self.app.get_file_parameters(file_id)
        self._suspend_master_callbacks = True
        try:
            self.master_volume_left.set(params.output_gain_left_db)
            self.master_volume_right.set(params.output_gain_right_db)
            self.master_level_left_value.config(text=f"L {params.output_gain_left_db:.1f} dB")
            self.master_level_right_value.config(text=f"R {params.output_gain_right_db:.1f} dB")
            self.master_knobs["SPEED"].set_value(params.speed)
            self.master_knobs["ECHO MIX"].set_value(params.echo_mix)
            self.master_knobs["DELAY"].set_value(params.echo_delay_ms)
            self.master_knobs["FEEDBACK"].set_value(params.echo_feedback)
        finally:
            self._suspend_master_callbacks = False

    def _sync_cassette(self, transport):
        files = self.app.get_audio_files()
        if not files:
            self.cassette_display.reset()
            self.cassette_subtitle.config(text="No tape loaded")
            self.transport_status.config(text="Stopped")
            return

        first_file = files[0]
        selected_count = len(self.app.get_selected_files())
        title = first_file.filename if len(files) == 1 else f"{first_file.filename} + {len(files) - 1} more"
        self.cassette_display.set_file_name(title)
        self.cassette_display.set_time(
            self._format_time(transport.position_seconds),
            self._format_time(transport.total_seconds),
        )

        primary_file_id = self._get_primary_selected_file_id()
        if primary_file_id:
            params = self.app.get_file_parameters(primary_file_id)
            self.cassette_display.set_speed(params.speed)

        is_playing = transport.state == TransportState.PLAYING
        self.cassette_display.set_playing(is_playing)
        self.cassette_subtitle.config(
            text=f"{selected_count or len(files)} active track(s) • {first_file.sample_rate} Hz"
        )

        if transport.state == TransportState.PLAYING:
            status = "Playing"
        elif transport.state == TransportState.PAUSED:
            status = "Paused"
        else:
            status = "Stopped"
        self.transport_status.config(text=status)

        self.play_btn.config(relief="sunken" if is_playing else "raised")
        self.pause_btn.config(
            relief="sunken" if transport.state == TransportState.PAUSED else "raised"
        )
        self.stop_btn.config(
            relief="sunken"
            if transport.state == TransportState.STOPPED
            else "raised"
        )
        self.loop_btn.config(
            bg=COLORS["accent"] if transport.loop_enabled else COLORS["transport_key"],
            fg=COLORS["text_bright"] if transport.loop_enabled else COLORS["transport_text"],
        )

    def _get_primary_selected_file_id(self):
        files = self.app.get_audio_files()
        selected = self.app.get_selected_files()
        for audio_file in files:
            if audio_file.id in selected:
                return audio_file.id
        return files[0].id if files else None

    def _apply_selected_parameter(self, name: str, value: float):
        if self._suspend_master_callbacks:
            return
        self.app.set_parameter(name, value)
        if name == "output_gain_left_db":
            self.master_level_left_value.config(text=f"L {value:.1f} dB")
        elif name == "output_gain_right_db":
            self.master_level_right_value.config(text=f"R {value:.1f} dB")
        self._update_track_strip_values()

    def _on_open_file(self):
        filetypes = [
            ("Audio Files", "*.wav *.flac *.ogg *.mp3 *.aiff *.aif"),
            ("WAV Files", "*.wav"),
            ("FLAC Files", "*.flac"),
            ("All Files", "*.*"),
        ]
        paths = filedialog.askopenfilenames(
            title="Load Audio Files",
            filetypes=filetypes,
        )
        if not paths:
            return

        for path in paths:
            try:
                self.app.load_file(path)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file {path}:\n{e}")

        self._rebuild_track_strips_if_needed()
        self._update_track_strip_values()
        self._refresh_selection_badge()
        self._sync_master_controls()
        self._set_status(f"Loaded {len(paths)} file(s)")

    def _on_select_all(self):
        self.app.select_all_files()
        self._refresh_selection_badge()
        self._sync_master_controls()
        self._update_track_strip_values()

    def _on_deselect_all(self):
        self.app.deselect_all_files()
        self._refresh_selection_badge()
        self._sync_master_controls()
        self._update_track_strip_values()

    def _on_remove_selected(self):
        selected_ids = list(self.app.get_selected_files())
        if not selected_ids:
            return
        for file_id in selected_ids:
            self.app.remove_file(file_id)
        self._rebuild_track_strips_if_needed()
        self._refresh_selection_badge()
        self._sync_master_controls()
        self._update_track_strip_values()
        self._set_status(f"Removed {len(selected_ids)} selected track(s)")

    def _on_play(self):
        self.app.play()

    def _on_pause(self):
        self.app.pause()

    def _on_stop(self):
        self.app.stop()

    def _on_loop_toggle(self):
        transport = self.app.get_transport_info()
        self.app.set_loop(not transport.loop_enabled)

    def _on_speed_change(self, value: float):
        self._apply_selected_parameter("speed", value)

    def _on_echo_mix_change(self, value: float):
        self._apply_selected_parameter("echo_mix", value)

    def _on_echo_delay_change(self, value: float):
        self._apply_selected_parameter("echo_delay_ms", value)

    def _on_echo_feedback_change(self, value: float):
        self._apply_selected_parameter("echo_feedback", value)

    def _on_gain_left_change(self, value: float):
        self._apply_selected_parameter("output_gain_left_db", value)

    def _on_gain_right_change(self, value: float):
        self._apply_selected_parameter("output_gain_right_db", value)

    def _on_track_change(self, file_id: str, name: str, value: float):
        if self._updating_tracks:
            return
        self.app.set_file_parameter(file_id, name, value)
        strip = self._track_strips.get(file_id)
        if not strip:
            return
        if name == "track_volume":
            strip["track_volume_label"].config(text=self._format_track_value(name, value))
        else:
            knob = strip[f"{name}_knob"]
            knob.value_label.config(text=self._format_track_value(name, value))

        if file_id in self.app.get_selected_files():
            self._sync_master_controls()

    def _on_export(self):
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

    def _on_separate_stems(self):
        if not self.app.has_audio_loaded():
            messagebox.showwarning("Warning", "No audio file loaded")
            return

        def run_separation():
            try:
                stems = self.app.separate_stems()
                stem_names = ", ".join(sorted(stems.keys()))
                self.root.after(0, lambda: self._set_status("Stem separation complete"))
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Stem Separation Complete",
                        "Created stems:\n"
                        f"{stem_names}\n\n"
                        "Click 'Load Stems' to add them as tracks.",
                    ),
                )
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: self._set_status("Stem separation failed"))
                if "FFmpeg" in error_msg or "torchcodec" in error_msg:
                    self.root.after(
                        0,
                        lambda: messagebox.showerror(
                            "Stem Separation Error",
                            "Stem separation requires FFmpeg to be installed.\n\n"
                            "Download FFmpeg from https://ffmpeg.org/download.html, "
                            "extract it, and add its bin folder to your PATH.\n\n"
                            f"Error details: {error_msg}",
                        ),
                    )
                elif "torchaudio could not be loaded" in error_msg or "versions do not match" in error_msg:
                    self.root.after(
                        0,
                        lambda: messagebox.showerror(
                            "Stem Separation Error",
                            "Stem separation dependencies are installed, but the "
                            "PyTorch audio runtime is broken on this machine.\n\n"
                            "What to fix:\n"
                            "1. Use Python 3.11 or 3.12.\n"
                            "2. Install matching torch and torchaudio versions.\n"
                            "3. Reinstall demucs in that same environment.\n\n"
                            f"Error details: {error_msg}",
                        ),
                    )
                else:
                    self.root.after(
                        0,
                        lambda: messagebox.showerror(
                            "Error", f"Separation failed:\n{error_msg}"
                        ),
                    )

        self._set_status(
            "Separating stems... first run may take several minutes while Demucs downloads its model."
        )
        thread = threading.Thread(target=run_separation, daemon=True)
        thread.start()

    def _on_load_stems(self):
        try:
            self.app.load_stems_as_tracks()
            self._rebuild_track_strips_if_needed()
            self._update_track_strip_values()
            self._refresh_selection_badge()
            self._sync_master_controls()
            self._set_status("Separated stems loaded as tracks")
            messagebox.showinfo(
                "Stems Loaded",
                "Separated stems have been loaded as individual tracks.",
            )
        except Exception as e:
            self._set_status("")
            messagebox.showerror("Load Stems Error", f"Failed to load stems:\n{e}")

    def _on_load_existing_stems(self):
        directory = filedialog.askdirectory(title="Select Separated Stem Directory")
        if not directory:
            return

        try:
            self.app.load_stems_from_directory(directory)
            self._rebuild_track_strips_if_needed()
            self._update_track_strip_values()
            self._refresh_selection_badge()
            self._sync_master_controls()
            self._set_status("Existing stems loaded as tracks")
            messagebox.showinfo(
                "Stems Loaded",
                "Existing separated stems have been loaded as individual tracks.",
            )
        except Exception as e:
            self._set_status("")
            messagebox.showerror("Load Stems Error", f"Failed to load stems:\n{e}")

    def _schedule_update(self):
        self._update_ui()
        self.root.after(self._update_interval, self._schedule_update)

    def _update_ui(self):
        transport = self.app.get_transport_info()
        metering_snapshot = self.app.get_metering_snapshot()

        self._rebuild_track_strips_if_needed()
        self._update_track_strip_values(metering_snapshot)
        self._refresh_selection_badge()
        self._sync_master_controls()
        self._sync_cassette(transport)
        self._update_stereo_meter(
            self.master_meter_canvas,
            self.master_meter_ids,
            metering_snapshot.get("master", {}),
        )

        error = self.app.get_engine_error()
        if error:
            messagebox.showerror("Audio Error", f"Audio engine error:\n{error}")

    def run(self):
        self.root.mainloop()
