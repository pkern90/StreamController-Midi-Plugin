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

    def _lm(self, key: str) -> str:
        """Get localized string with fallback to key."""
        try:
            return self.plugin_base.locale_manager.get(key)
        except Exception:
            return key

    def on_ready(self) -> None:
        # Initialize settings with defaults if not set
        self._ensure_default_settings()
        
        # Set icon if available
        icon_path = os.path.join(self.plugin_base.PATH, "assets", "note.png")
        if os.path.exists(icon_path):
            self.set_media(media_path=icon_path, size=0.75)
        
        settings = self.get_settings()
        note = settings.get("note", 60)
        self.set_bottom_label(f"Note {note}", font_size=14)

    def _ensure_default_settings(self):
        """Ensure settings have default values."""
        settings = self.get_settings()
        defaults = {
            "channel": 0,
            "note": 60,
            "velocity": 100,
        }
        changed = False
        for key, default in defaults.items():
            if key not in settings:
                settings[key] = default
                changed = True
        if changed:
            self.set_settings(settings)

    def on_key_down(self) -> None:
        # Send MIDI Note On
        if not self._midi_manager:
            self.show_error(duration=1)
            return
            
        settings = self.get_settings()
        port_name = settings.get("port", "")
        channel = settings.get("channel", 0)
        note = settings.get("note", 60)
        velocity = settings.get("velocity", 100)
        
        if not port_name:
            self.show_error(duration=1)
            return
            
        self._midi_manager.send_note_on(port_name, channel, note, velocity)
        self._note_on = True
        
        # Update UI to show active state
        self.set_bottom_label(f"Note {note} ON", font_size=12)

    def on_key_up(self) -> None:
        # Send MIDI Note Off
        if self._note_on and self._midi_manager:
            settings = self.get_settings()
            port_name = settings.get("port", "")
            channel = settings.get("channel", 0)
            note = settings.get("note", 60)
            
            if port_name:
                self._midi_manager.send_note_off(port_name, channel, note)
            self._note_on = False
            
        settings = self.get_settings()
        note = settings.get("note", 60)
        self.set_bottom_label(f"Note {note}", font_size=14)

    def get_config_rows(self) -> list:
        """Return configuration rows for the action."""
        if ComboRow is None:
            return []

        settings = self.get_settings()

        # Create ListStore for Gtk.ComboBox
        # Column 0: Display Name (str)
        self.model = Gtk.ListStore(str)
        self._refresh_port_list()

        # Create ComboRow using GtkHelper
        self.port_row = ComboRow(title=self._lm("config.port"), model=self.model)
        
        # Setup CellRenderer for the internal ComboBox
        renderer = Gtk.CellRendererText()
        self.port_row.combo_box.pack_start(renderer, True)
        self.port_row.combo_box.add_attribute(renderer, "text", 0)

        # Set current selection
        current_port = settings.get("port", "")
        active_index = 0
        
        # Find index of current port
        for i, row in enumerate(self.model):
            if row[0] == current_port:
                active_index = i
                break
        
        self.port_row.combo_box.set_active(active_index)
        
        # Connect signal to save setting
        self.port_row.combo_box.connect("changed", self.on_port_changed)
        
        rows = [self.port_row]

        # -- Refresh Ports Button --
        refresh_row = Adw.ActionRow()
        refresh_row.set_title(self._lm("config.port.refresh"))
        refresh_button = Gtk.Button()
        refresh_button.set_icon_name("view-refresh-symbolic")
        refresh_button.set_valign(Gtk.Align.CENTER)
        refresh_button.connect("clicked", self._on_refresh_ports)
        refresh_row.add_suffix(refresh_button)
        rows.append(refresh_row)

        # -- Channel --
        self.channel_row = Adw.SpinRow.new_with_range(0, 15, 1)
        self.channel_row.set_title(self._lm("config.channel"))
        self.channel_row.set_value(settings.get("channel", 0))
        self.channel_row.connect("notify::value", self.on_channel_changed)
        rows.append(self.channel_row)

        # -- Note --
        self.note_row = Adw.SpinRow.new_with_range(0, 127, 1)
        self.note_row.set_title(self._lm("config.note"))
        self.note_row.set_value(settings.get("note", 60))
        self.note_row.connect("notify::value", self.on_note_changed)
        rows.append(self.note_row)

        # -- Velocity --
        self.velocity_row = Adw.SpinRow.new_with_range(0, 127, 1)
        self.velocity_row.set_title(self._lm("config.velocity"))
        self.velocity_row.set_value(settings.get("velocity", 100))
        self.velocity_row.connect("notify::value", self.on_velocity_changed)
        rows.append(self.velocity_row)

        return rows

    def _refresh_port_list(self):
        """Refresh the list of available MIDI ports."""
        self.model.clear()
        ports = []
        if self._midi_manager:
            ports = self._midi_manager.get_output_ports()
        
        if not ports:
            self.model.append([self._lm("config.port.no_ports")])
        else:
            for port in ports:
                self.model.append([port])

    def _on_refresh_ports(self, button):
        """Handle refresh ports button click."""
        settings = self.get_settings()
        current_port = settings.get("port", "")
        
        self._refresh_port_list()
        
        # Try to reselect the current port
        active_index = 0
        for i, row in enumerate(self.model):
            if row[0] == current_port:
                active_index = i
                break
        self.port_row.combo_box.set_active(active_index)

    def on_port_changed(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter:
            model = combo.get_model()
            port = model[tree_iter][0]
            settings = self.get_settings()
            settings["port"] = port
            self.set_settings(settings)

    def on_channel_changed(self, widget, param):
        settings = self.get_settings()
        settings["channel"] = int(widget.get_value())
        self.set_settings(settings)

    def on_note_changed(self, widget, param):
        settings = self.get_settings()
        settings["note"] = int(widget.get_value())
        self.set_settings(settings)
        # Update label
        self.set_bottom_label(f"Note {settings['note']}", font_size=14)

    def on_velocity_changed(self, widget, param):
        settings = self.get_settings()
        settings["velocity"] = int(widget.get_value())
        self.set_settings(settings)

