"""
SendProgramChange Action - Sends MIDI Program Change messages.
"""

from src.backend.PluginManager.ActionBase import ActionBase
import os

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from ...internal.MidiManager import MidiManager


class SendProgramChange(ActionBase):
    """Action to send MIDI Program Change messages."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_ready(self) -> None:
        """Initialize the action display."""
        self._update_display()

    def _update_display(self) -> None:
        """Update the button display based on current state."""
        settings = self.get_settings()
        program = settings.get("program", 0)
        channel = settings.get("channel", 0) + 1

        icon_path = os.path.join(self.plugin_base.PATH, "assets", "program.png")
        if os.path.exists(icon_path):
            self.set_media(media_path=icon_path, size=0.75)

        self.set_bottom_label(f"Ch{channel} P{program}", font_size=12)

    def on_key_down(self) -> None:
        """Handle key press - send Program Change message."""
        settings = self.get_settings()
        port_name = settings.get("port", "")
        channel = settings.get("channel", 0)
        program = settings.get("program", 0)

        MidiManager.send_program_change(port_name, channel, program)

    def on_key_up(self) -> None:
        """Handle key release - no action needed for program change."""
        pass

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

        current_port = settings.get("port", "")
        if current_port in ports:
            self.port_combo.set_selected(ports.index(current_port))

        self.port_combo.connect("notify::selected", self._on_port_changed)

        # Channel selector
        self.channel_spin = Adw.SpinRow.new_with_range(1, 16, 1)
        self.channel_spin.set_title("MIDI Channel")
        self.channel_spin.set_value(settings.get("channel", 0) + 1)
        self.channel_spin.connect("changed", self._on_channel_changed)

        # Program selector
        self.program_spin = Adw.SpinRow.new_with_range(0, 127, 1)
        self.program_spin.set_title("Program Number")
        self.program_spin.set_subtitle("Program/Patch to select (0-127)")
        self.program_spin.set_value(settings.get("program", 0))
        self.program_spin.connect("changed", self._on_program_changed)

        return [self.port_combo, self.channel_spin, self.program_spin]

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
        settings["channel"] = int(spin.get_value()) - 1
        self.set_settings(settings)
        self._update_display()

    def _on_program_changed(self, spin) -> None:
        """Handle program change."""
        settings = self.get_settings()
        settings["program"] = int(spin.get_value())
        self.set_settings(settings)
        self._update_display()
