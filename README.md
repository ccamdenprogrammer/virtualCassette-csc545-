# Cassette Player

A sleek desktop audio player with real-time effects, styled as a modern cassette deck.

## Features

- **Cassette-themed UI**: Animated tape reels that spin during playback
- **Real-time effects**: Speed control and echo that respond immediately
- **Rotary knob controls**: All parameters controlled via drag-to-adjust knobs
- **Live playback**: Effects applied in real-time without interruption
- **Export**: Save processed audio to WAV with current effect settings

## Screenshot

```
┌─────────────────────────────────────────┐
│           ╭─────────────────╮           │
│           │  ◉           ◉  │           │
│           │    ═══════════  │           │
│           │   [file name]   │           │
│           ╰─────────────────╯           │
│                                         │
│              ┌─────────┐                │
│              │  SPEED  │                │
│              │  1.00x  │                │
│              └─────────┘                │
│                                         │
│    ┌─────┐   ┌─────┐   ┌─────┐         │
│    │ MIX │   │DELAY│   │FDBK │         │
│    │ 25% │   │250ms│   │ 40% │         │
│    └─────┘   └─────┘   └─────┘         │
│                                         │
│   ▶ Play  ⏸ Pause  ⏹ Stop  ⟲ Loop     │
│                                         │
│        [ Load ]    [ Export ]           │
└─────────────────────────────────────────┘
```

## Installation

1. Create a virtual environment and install dependencies:

```bash
cd realtime_audio_fx
python -m venv venv
venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
```

2. Run the application:

```bash
python -m realtime_audio_fx.main
```

## Controls

### Transport
| Control | Action |
|---------|--------|
| **Play** | Start/resume playback |
| **Pause** | Pause playback |
| **Stop** | Stop and reset to beginning |
| **Loop** | Toggle looping mode |

### Effect Knobs
| Knob | Range | Description |
|------|-------|-------------|
| **Speed** | 0.5x - 2.0x | Playback speed |
| **Echo Mix** | 0% - 100% | Dry/wet balance |
| **Echo Delay** | 1 - 1000 ms | Delay time |
| **Echo Feedback** | 0% - 90% | Repeat intensity |
| **Output Gain** | -24 dB to +12 dB | Master volume |

### Knob Interaction
- Click and drag **up** to increase value
- Click and drag **down** to decrease value

## Supported Formats

- WAV
- FLAC
- OGG
- MP3
- AIFF

## Requirements

- Python 3.10+
- soundfile
- sounddevice
- numpy
- scipy

## Architecture

```
realtime_audio_fx/
├── main.py              # Entry point
├── app.py               # Application coordinator
├── config.py            # Configuration constants
│
├── ui/                  # Cassette player interface
│   ├── main_window.py   # Main window
│   ├── cassette_display.py  # Animated tape display
│   ├── knob_widget.py   # Rotary knob control
│   ├── transport_bar.py # Transport buttons
│   └── theme.py         # Visual styling
│
├── engine/              # Audio processing
│   ├── audio_engine.py  # Real-time I/O
│   ├── block_processor.py   # Effect chain
│   └── source_reader.py # Playback with speed control
│
├── dsp/                 # Digital signal processing
│   ├── echo.py          # Echo/delay effect
│   └── utils.py         # dB conversion
│
├── models/              # Data models
│   ├── audio_file.py    # Audio file metadata
│   ├── parameters.py    # Thread-safe parameter store
│   └── transport.py     # Playback state
│
└── services/            # File I/O
    ├── file_loader.py   # Load and resample audio
    ├── exporter.py      # Render to WAV
    └── device_service.py # Audio device queries
```

### Processing Chain

```
Audio File → Speed Control → Echo → Gain → Output
```

### Real-time Design

- Audio processed in 1024-sample blocks (~23ms at 44.1kHz)
- Thread-safe parameter store for UI ↔ audio communication
- Parameter smoothing prevents clicks on value changes
- Cassette animation synced to playback state and speed

## Testing

```bash
pytest realtime_audio_fx/tests/ -v
```

## License

MIT License
