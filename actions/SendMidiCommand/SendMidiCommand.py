from src.backend.PluginManager.ActionBase import ActionBase
import sys
import os

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GLib

# Import GtkHelper for ComboRow
try:
    from GtkHelper.GtkHelper import ComboRow
except ImportError:
    print("Failed to import GtkHelper. Using fallback or failing.")
    ComboRow = None

class SendMidiCommand(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._midi_manager = None
        self._load_midi_manager()

    def _load_midi_manager(self):
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
        self.update_key_image()

    def _ensure_default_settings(self):
        """Ensure settings have default values."""
        settings = self.get_settings()
        defaults = {
            "msg_type": "note_on",
            "channel": 0,
            "data1": 60,
            "data2": 100,
        }
        changed = False
        for key, default in defaults.items():
            if key not in settings:
                settings[key] = default
                changed = True
        if changed:
            self.set_settings(settings)

    def update_key_image(self):
        # Default icon
        icon_path = os.path.join(self.plugin_base.PATH, "assets", "midi.png")
        if not os.path.exists(icon_path):
             icon_path = os.path.join(self.plugin_base.PATH, "assets", "note.png")
        
        if os.path.exists(icon_path):
            self.set_media(media_path=icon_path, size=0.75)
        
        settings = self.get_settings()
        msg_type = settings.get("msg_type", "note_on")
        data1 = settings.get("data1", 60)
        
        label = "MIDI"
        if msg_type == "note_on":
            label = f"Note {data1}"
        elif msg_type == "control_change":
            label = f"CC {data1}"
        elif msg_type == "program_change":
            label = f"PC {data1}"
        elif msg_type == "pitchwheel":
            label = f"PW {data1}"
            
        self.set_bottom_label(label, font_size=10)

    def on_key_down(self) -> None:
        if not self._midi_manager:
            self.show_error(duration=1)
            return

        settings = self.get_settings()
        port_name = settings.get("port", "")
        if not port_name:
            self.show_error(duration=1)
            return

        msg_type = settings.get("msg_type", "note_on")
        channel = settings.get("channel", 0)
        data1 = settings.get("data1", 60)
        data2 = settings.get("data2", 100)

        # Map UI 0-16 (if user sees 1-16) generally MIDI channels are 0-15 in mido
        # I'll assume 0-indexed for now to be safe, typically devs prefer 0-15.
        
        if msg_type == "note_on":
            self._midi_manager.send_note_on(port_name, channel, data1, data2)
        elif msg_type == "control_change":
             self._midi_manager.send_control_change(port_name, channel, data1, data2)
        elif msg_type == "program_change":
             self._midi_manager.send_program_change(port_name, channel, data1)
        elif msg_type == "pitchwheel":
             # data1 is the pitch value (-8192 to 8191)
             self._midi_manager.send_pitchwheel(port_name, channel, data1)
        elif msg_type == "note_off":
            self._midi_manager.send_note_off(port_name, channel, data1)

    def on_key_up(self) -> None:
        # If type is Note On, send Note Off?
        settings = self.get_settings()
        msg_type = settings.get("msg_type", "note_on")
        
        if msg_type == "note_on":
            port_name = settings.get("port", "")
            channel = settings.get("channel", 0)
            data1 = settings.get("data1", 0)
            if self._midi_manager and port_name:
                self._midi_manager.send_note_off(port_name, channel, data1)

    def get_config_rows(self) -> list:
        if ComboRow is None:
            return []

        settings = self.get_settings()
        
        rows = []

        # -- Port Selection --
        self.port_model = Gtk.ListStore(str)
        self._refresh_port_list()
        
        self.port_row = ComboRow(title=self._lm("config.port"), model=self.port_model)
        
        renderer = Gtk.CellRendererText()
        self.port_row.combo_box.pack_start(renderer, True)
        self.port_row.combo_box.add_attribute(renderer, "text", 0)
        
        current_port = settings.get("port", "")
        # Find index
        active_index = 0
        for i, row in enumerate(self.port_model):
            if row[0] == current_port:
                active_index = i
                break
        self.port_row.combo_box.set_active(active_index)
        
        self.port_row.combo_box.connect("changed", self.on_port_changed)
        rows.append(self.port_row)

        # -- Refresh Ports Button --
        refresh_row = Adw.ActionRow()
        refresh_row.set_title(self._lm("config.port.refresh"))
        refresh_button = Gtk.Button()
        refresh_button.set_icon_name("view-refresh-symbolic")
        refresh_button.set_valign(Gtk.Align.CENTER)
        refresh_button.connect("clicked", self._on_refresh_ports)
        refresh_row.add_suffix(refresh_button)
        rows.append(refresh_row)

        # -- Message Type --
        self.type_model = Gtk.ListStore(str, str) # Display, Internal Key
        self.type_model.append([self._lm("config.msg_type.note_on"), "note_on"])
        self.type_model.append([self._lm("config.msg_type.control_change"), "control_change"])
        self.type_model.append([self._lm("config.msg_type.program_change"), "program_change"])
        self.type_model.append([self._lm("config.msg_type.pitchwheel"), "pitchwheel"])
        self.type_model.append([self._lm("config.msg_type.note_off"), "note_off"])

        type_row = ComboRow(title=self._lm("config.msg_type"), model=self.type_model)
        renderer_type = Gtk.CellRendererText()
        type_row.combo_box.pack_start(renderer_type, True)
        type_row.combo_box.add_attribute(renderer_type, "text", 0)
        
        current_type = settings.get("msg_type", "note_on")
        active_type_index = 0
        for i, row in enumerate(self.type_model):
            if row[1] == current_type:
                active_type_index = i
                break
        type_row.combo_box.set_active(active_type_index)
        type_row.combo_box.connect("changed", self.on_type_changed)
        rows.append(type_row)
        
        # -- Channel --
        self.channel_row = Adw.SpinRow.new_with_range(0, 15, 1)
        self.channel_row.set_title(self._lm("config.channel"))
        self.channel_row.set_value(settings.get("channel", 0))
        self.channel_row.connect("notify::value", self.on_channel_changed)
        rows.append(self.channel_row)

        # -- Data 1 (Note/Control/Program/Pitch) --
        # Default range 0-127, will be updated for pitchwheel
        self.data1_row = Adw.SpinRow.new_with_range(-8192, 8191, 1)
        self.data1_row.set_value(settings.get("data1", 60))
        self.data1_row.connect("notify::value", self.on_data1_changed)
        rows.append(self.data1_row)

        # -- Data 2 (Velocity/Value) --
        self.data2_row = Adw.SpinRow.new_with_range(0, 127, 1)
        self.data2_row.set_value(settings.get("data2", 100))
        self.data2_row.connect("notify::value", self.on_data2_changed)
        rows.append(self.data2_row)

        # Initial Label Update
        self.update_labels(current_type)
        self._update_data1_range(current_type)

        return rows

    def _update_data1_range(self, msg_type):
        """Update the data1 spin row range based on message type."""
        adjustment = self.data1_row.get_adjustment()
        if msg_type == "pitchwheel":
            adjustment.set_lower(-8192)
            adjustment.set_upper(8191)
        else:
            adjustment.set_lower(0)
            adjustment.set_upper(127)
            # Clamp current value to new range
            current = self.data1_row.get_value()
            if current < 0:
                self.data1_row.set_value(0)
            elif current > 127:
                self.data1_row.set_value(127)

    def on_port_changed(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter:
            model = combo.get_model()
            port = model[tree_iter][0]
            settings = self.get_settings()
            settings["port"] = port
            self.set_settings(settings)

    def _refresh_port_list(self):
        """Refresh the list of available MIDI ports."""
        self.port_model.clear()
        ports = []
        if self._midi_manager:
            ports = self._midi_manager.get_output_ports()
        
        if not ports:
            self.port_model.append([self._lm("config.port.no_ports")])
        else:
            for port in ports:
                self.port_model.append([port])

    def _on_refresh_ports(self, button):
        """Handle refresh ports button click."""
        settings = self.get_settings()
        current_port = settings.get("port", "")
        
        self._refresh_port_list()
        
        # Try to reselect the current port
        active_index = 0
        for i, row in enumerate(self.port_model):
            if row[0] == current_port:
                active_index = i
                break
        self.port_row.combo_box.set_active(active_index)

    def on_type_changed(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter:
            model = combo.get_model()
            msg_type = model[tree_iter][1]
            settings = self.get_settings()
            settings["msg_type"] = msg_type
            self.set_settings(settings)
            self.update_labels(msg_type)
            self._update_data1_range(msg_type)
            self.update_key_image()

    def on_channel_changed(self, widget, param):
        settings = self.get_settings()
        settings["channel"] = int(widget.get_value())
        self.set_settings(settings)

    def on_data1_changed(self, widget, param):
        settings = self.get_settings()
        settings["data1"] = int(widget.get_value())
        self.set_settings(settings)
        self.update_key_image()

    def on_data2_changed(self, widget, param):
        settings = self.get_settings()
        settings["data2"] = int(widget.get_value())
        self.set_settings(settings)

    def update_labels(self, msg_type):
        if msg_type == "note_on" or msg_type == "note_off":
            self.data1_row.set_title(self._lm("config.note"))
            self.data2_row.set_title(self._lm("config.velocity"))
            self.data2_row.set_visible(True)
        elif msg_type == "control_change":
            self.data1_row.set_title(self._lm("config.control_number"))
            self.data2_row.set_title(self._lm("config.value"))
            self.data2_row.set_visible(True)
        elif msg_type == "program_change":
            self.data1_row.set_title(self._lm("config.program_number"))
            self.data2_row.set_visible(False)
        elif msg_type == "pitchwheel":
            self.data1_row.set_title(self._lm("config.pitch_value"))
            self.data2_row.set_visible(False)
