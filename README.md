# StreamController MIDI Plugin

A MIDI plugin for [StreamController](https://github.com/StreamController/StreamController) that allows you to send MIDI messages from your Stream Deck.

## Features

- **Send Note**: Send MIDI Note On/Off messages with configurable channel, note, and velocity
- **Send CC**: Send Control Change messages for controlling parameters like volume, pan, etc.
- **Send Program Change**: Send Program Change messages to switch patches/presets
- **MIDI Dial**: Use Stream Deck Plus knobs to control volume or any CC parameter

## Actions

### Send Note
Send MIDI note messages with multiple modes:
- **Momentary**: Note On when pressed, Note Off when released
- **Toggle**: Alternate between Note On and Note Off
- **Note On only**: Only send Note On
- **Note Off only**: Only send Note Off

### Send CC (Control Change)
Send CC messages with multiple modes:
- **Single**: Send value on press
- **Momentary**: Send value on press, different value on release
- **Toggle**: Alternate between two values

### Send Program Change
Send program/patch change messages to switch presets on your MIDI devices.

### MIDI Dial (Stream Deck Plus)
Use the rotary encoders on Stream Deck Plus to control:
- Volume (CC#7) or any CC parameter
- Configurable step size per click
- Press to mute/unmute or reset to default

## Use Cases

- Control DAW parameters (volume, pan, effects)
- Switch presets on synthesizers and virtual instruments
- Control lighting systems via MIDI
- Control Genelec GLM speakers
- Any MIDI-compatible device

## Requirements

- StreamController 1.5.0-beta or later
- Linux with ALSA or JACK MIDI support
- `mido` and `python-rtmidi` Python packages (installed automatically)

## Installation

1. Open StreamController
2. Go to the Plugin Store
3. Search for "MIDI"
4. Click Install

Or manually:
1. Clone this repository to `~/.var/app/com.core447.StreamController/data/plugins/com_github_pkern90_midi/`
2. Restart StreamController

## Configuration

Each action can be configured with:
- **MIDI Output Port**: Select your MIDI device
- **Channel**: MIDI channel (1-16)
- **Additional parameters** specific to each action type

## License

MIT License - see [LICENSE](LICENSE) for details.
