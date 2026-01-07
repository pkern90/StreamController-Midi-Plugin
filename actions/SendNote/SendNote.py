from src.backend.PluginManager.ActionBase import ActionBase
import os
import sys

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

# Import GtkHelper for ComboRow
try:
    from GtkHelper.GtkHelper import ComboRow
except ImportError:
    print("Failed to import GtkHelper. Using fallback or failing.")
    ComboRow = None


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
        if ComboRow is None:
            return []

        settings = self.get_settings()

        # Create ListStore for Gtk.ComboBox
        # Column 0: Display Name (str)
        self.model = Gtk.ListStore(str)
        
        ports = []
        if self._midi_manager:
            ports = self._midi_manager.get_output_ports()
        
        if not ports:
            self.model.append(["No MIDI ports found"])
        else:
            for port in ports:
                self.model.append([port])

        # Create ComboRow using GtkHelper
        self.port_row = ComboRow(title="MIDI Output Port", model=self.model)
        
        # Setup CellRenderer for the internal ComboBox
        renderer = Gtk.CellRendererText()
        self.port_row.combo_box.pack_start(renderer, True)
        self.port_row.combo_box.add_attribute(renderer, "text", 0)

        # Set current selection
        current_port = settings.get("port", "")
        active_index = 0
        found = False
        
        # Find index of current port
        for i, row in enumerate(self.model):
            if row[0] == current_port:
                active_index = i
                found = True
                break
        
        if not found and ports:
             # Default to first valid port if saved one not found
             settings["port"] = ports[0]
             self.set_settings(settings)
             active_index = 0
             
        self.port_row.combo_box.set_active(active_index)
        self.port_row.combo_box.connect("changed", self._on_port_changed)

        return [self.port_row]

    def _on_port_changed(self, combo, _param=None) -> None:
        """Handle port selection change."""
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            port_name = model[tree_iter][0]
            
            # Ignore placeholder
            if port_name == "No MIDI ports found":
                return

            settings = self.get_settings()
            settings["port"] = port_name
            self.set_settings(settings)
            print(f"MIDI Plugin: Selected port '{port_name}'")
