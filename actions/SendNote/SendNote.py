from src.backend.PluginManager.ActionBase import ActionBase
import os
import sys

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


class SendNote(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._note_on = False
        self._midi_manager = None

        # Import MidiManager dynamically using plugin path
        try:
            plugin_path = self.plugin_base.PATH
            if plugin_path not in sys.path:
                sys.path.insert(0, plugin_path)
            from internal.MidiManager import MidiManager
            self._midi_manager = MidiManager
        except Exception as e:
            print(f"Failed to load MidiManager: {e}")
            self._midi_manager = None

    def on_ready(self) -> None:
        # Set icon if available
        icon_path = os.path.join(self.plugin_base.PATH, "assets", "note.png")
        if os.path.exists(icon_path):
            self.set_media(media_path=icon_path, size=0.75)
        self.set_bottom_label("Note 60", font_size=14)

    def on_key_down(self) -> None:
        # Send MIDI Note On (hardcoded: channel 0, note 60, velocity 100)
        if self._midi_manager:
            settings = self.get_settings()
            port_name = settings.get("port", "")
            if port_name:
                self._midi_manager.send_note_on(port_name, 0, 60, 100)
                self._note_on = True
        self.set_bottom_label("ON", font_size=14)

    def on_key_up(self) -> None:
        # Send MIDI Note Off
        if self._note_on and self._midi_manager:
            settings = self.get_settings()
            port_name = settings.get("port", "")
            if port_name:
                self._midi_manager.send_note_off(port_name, 0, 60)
            self._note_on = False
        self.set_bottom_label("Note 60", font_size=14)

    def get_config_rows(self) -> list:
        """Return configuration rows for the action."""
        settings = self.get_settings()

        # MIDI Port selector
        self.port_combo = Adw.ComboRow()
        self.port_combo.set_title("MIDI Output Port")
        self.port_combo.set_subtitle("Select the MIDI device to send to")

        if self._midi_manager:
            ports = self._midi_manager.get_output_ports()
            port_list = Gtk.StringList.new(ports if ports else ["No MIDI ports found"])
            self.port_combo.set_model(port_list)

            # Set current selection
            current_port = settings.get("port", "")
            if current_port in ports:
                self.port_combo.set_selected(ports.index(current_port))
        else:
            port_list = Gtk.StringList.new(["MidiManager not available"])
            self.port_combo.set_model(port_list)

        self.port_combo.connect("notify::selected", self._on_port_changed)

        return [self.port_combo]

    def _on_port_changed(self, combo, _param) -> None:
        """Handle port selection change."""
        if self._midi_manager:
            ports = self._midi_manager.get_output_ports()
            if ports:
                selected = combo.get_selected()
                if selected < len(ports):
                    settings = self.get_settings()
                    settings["port"] = ports[selected]
                    self.set_settings(settings)
