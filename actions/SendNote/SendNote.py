"""
SendNote Action - Sends MIDI Note On/Off messages.
"""

from src.backend.PluginManager.ActionBase import ActionBase
import os

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from ...internal.MidiManager import MidiManager


class SendNote(ActionBase):
    """Action to send MIDI Note On/Off messages."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._note_on = False

    def on_ready(self) -> None:
        """Initialize the action display."""
        self._update_display()

    def _update_display(self) -> None:
        """Update the button display based on current state."""
        settings = self.get_settings()
        note = settings.get("note", 60)
        channel = settings.get("channel", 0) + 1  # Display 1-based

        icon_path = os.path.join(self.plugin_base.PATH, "assets", "note.png")
        if os.path.exists(icon_path):
            self.set_media(media_path=icon_path, size=0.75)

        self.set_bottom_label(f"Ch{channel} N{note}", font_size=12)

    def on_key_down(self) -> None:
        """Handle key press - send Note On."""
        settings = self.get_settings()
        port_name = settings.get("port", "")
        channel = settings.get("channel", 0)
        note = settings.get("note", 60)
        velocity = settings.get("velocity", 100)
        mode = settings.get("mode", "momentary")

        if mode == "momentary":
            # Momentary mode: Note On when pressed
            MidiManager.send_note_on(port_name, channel, note, velocity)
            self._note_on = True
        elif mode == "toggle":
            # Toggle mode: Alternate between Note On and Note Off
            if self._note_on:
                MidiManager.send_note_off(port_name, channel, note)
                self._note_on = False
            else:
                MidiManager.send_note_on(port_name, channel, note, velocity)
                self._note_on = True
        elif mode == "note_on_only":
            # Only send Note On
            MidiManager.send_note_on(port_name, channel, note, velocity)
        elif mode == "note_off_only":
            # Only send Note Off
            MidiManager.send_note_off(port_name, channel, note)

    def on_key_up(self) -> None:
        """Handle key release - send Note Off for momentary mode."""
        settings = self.get_settings()
        mode = settings.get("mode", "momentary")

        if mode == "momentary" and self._note_on:
            port_name = settings.get("port", "")
            channel = settings.get("channel", 0)
            note = settings.get("note", 60)
            MidiManager.send_note_off(port_name, channel, note)
            self._note_on = False

    def get_config_rows(self) -> list:
        """Return configuration rows for the action."""
        settings = self.get_settings()

        # MIDI Port selector
        self.port_combo = Adw.ComboRow()
        self.port_combo.set_title("MIDI Output Port")
        self.port_combo.set_subtitle("Select the MIDI device to send to")

        ports = MidiManager.get_output_ports()
        port_list = Gtk.StringList.new(ports if ports else ["No MIDI ports found"])
        self.port_combo.set_model(port_list)

        # Set current selection
        current_port = settings.get("port", "")
        if current_port in ports:
            self.port_combo.set_selected(ports.index(current_port))

        self.port_combo.connect("notify::selected", self._on_port_changed)

        # Channel selector (0-15, displayed as 1-16)
        self.channel_spin = Adw.SpinRow.new_with_range(1, 16, 1)
        self.channel_spin.set_title("MIDI Channel")
        self.channel_spin.set_value(settings.get("channel", 0) + 1)
        self.channel_spin.connect("changed", self._on_channel_changed)

        # Note selector (0-127)
        self.note_spin = Adw.SpinRow.new_with_range(0, 127, 1)
        self.note_spin.set_title("Note Number")
        self.note_spin.set_subtitle("0-127 (Middle C = 60)")
        self.note_spin.set_value(settings.get("note", 60))
        self.note_spin.connect("changed", self._on_note_changed)

        # Velocity selector (0-127)
        self.velocity_spin = Adw.SpinRow.new_with_range(0, 127, 1)
        self.velocity_spin.set_title("Velocity")
        self.velocity_spin.set_value(settings.get("velocity", 100))
        self.velocity_spin.connect("changed", self._on_velocity_changed)

        # Mode selector
        self.mode_combo = Adw.ComboRow()
        self.mode_combo.set_title("Mode")
        self.mode_combo.set_subtitle("How the note message is triggered")

        modes = ["Momentary (hold)", "Toggle", "Note On only", "Note Off only"]
        mode_values = ["momentary", "toggle", "note_on_only", "note_off_only"]
        mode_list = Gtk.StringList.new(modes)
        self.mode_combo.set_model(mode_list)

        current_mode = settings.get("mode", "momentary")
        if current_mode in mode_values:
            self.mode_combo.set_selected(mode_values.index(current_mode))

        self.mode_combo.connect("notify::selected", self._on_mode_changed)

        # Store mode values for reference
        self._mode_values = mode_values

        return [self.port_combo, self.channel_spin, self.note_spin,
                self.velocity_spin, self.mode_combo]

    def _on_port_changed(self, combo, _param) -> None:
        """Handle port selection change."""
        ports = MidiManager.get_output_ports()
        if ports:
            selected = combo.get_selected()
            if selected < len(ports):
                settings = self.get_settings()
                settings["port"] = ports[selected]
                self.set_settings(settings)

    def _on_channel_changed(self, spin) -> None:
        """Handle channel change."""
        settings = self.get_settings()
        settings["channel"] = int(spin.get_value()) - 1  # Store 0-based
        self.set_settings(settings)
        self._update_display()

    def _on_note_changed(self, spin) -> None:
        """Handle note change."""
        settings = self.get_settings()
        settings["note"] = int(spin.get_value())
        self.set_settings(settings)
        self._update_display()

    def _on_velocity_changed(self, spin) -> None:
        """Handle velocity change."""
        settings = self.get_settings()
        settings["velocity"] = int(spin.get_value())
        self.set_settings(settings)

    def _on_mode_changed(self, combo, _param) -> None:
        """Handle mode change."""
        selected = combo.get_selected()
        settings = self.get_settings()
        settings["mode"] = self._mode_values[selected]
        self.set_settings(settings)
