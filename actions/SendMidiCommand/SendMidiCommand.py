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

    def on_ready(self) -> None:
        self.update_key_image()

    def update_key_image(self):
        # Default icon
        icon_path = os.path.join(self.plugin_base.PATH, "assets", "midi.png")
        if not os.path.exists(icon_path):
             icon_path = os.path.join(self.plugin_base.PATH, "assets", "note.png")
        
        if os.path.exists(icon_path):
            self.set_media(media_path=icon_path, size=0.75)
        
        settings = self.get_settings()
        msg_type = settings.get("msg_type", "note_on")
        data1 = settings.get("data1", 0)
        
        label = "MIDI"
        if msg_type == "note_on":
            label = f"Note {data1}"
        elif msg_type == "control_change":
            label = f"CC {data1}"
        elif msg_type == "program_change":
            label = f"PC {data1}"
            
        self.set_bottom_label(label, font_size=10)

    def on_key_down(self) -> None:
        if not self._midi_manager:
            return

        settings = self.get_settings()
        port_name = settings.get("port", "")
        if not port_name:
            return

        msg_type = settings.get("msg_type", "note_on")
        channel = settings.get("channel", 0)
        data1 = settings.get("data1", 0)
        data2 = settings.get("data2", 0)

        # Map UI 0-16 (if user sees 1-16) generally MIDI channels are 0-15 in mido
        # I'll assume 0-indexed for now to be safe, typically devs prefer 0-15.
        
        if msg_type == "note_on":
            self._midi_manager.send_note_on(port_name, channel, data1, data2)
        elif msg_type == "control_change":
             self._midi_manager.send_control_change(port_name, channel, data1, data2)
        elif msg_type == "program_change":
             self._midi_manager.send_program_change(port_name, channel, data1)
        elif msg_type == "pitchwheel":
             # Mido pitchwheel takes 'pitch' argument, usually -8192 to 8191. 
             # Let's map data1 (coarse) + data2 (fine) or just a single value? 
             # Simpler: just use data1 as value? Or maybe create a combined value.
             # Standard pitchwheel is often tricky. 
             # Let's support data1 as the pitch value if manageable, 
             # but SpinRow typically has a range. Pitch is large.
             # Maybe skip pitchwheel for "basic" custom commands or implement properly.
             # I'll stick to Note, CC, PC for now as they are most requested.
             pass
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
        ports = []
        if self._midi_manager:
            ports = self._midi_manager.get_output_ports()
        
        if not ports:
            self.port_model.append(["No MIDI ports found"])
        else:
            for port in ports:
                self.port_model.append([port])
        
        port_row = ComboRow(title="MIDI Output Port", model=self.port_model)
        
        renderer = Gtk.CellRendererText()
        port_row.combo_box.pack_start(renderer, True)
        port_row.combo_box.add_attribute(renderer, "text", 0)
        
        current_port = settings.get("port", "")
        # Find index
        active_index = 0
        for i, row in enumerate(self.port_model):
            if row[0] == current_port:
                active_index = i
                break
        port_row.combo_box.set_active(active_index)
        
        port_row.combo_box.connect("changed", self.on_port_changed)
        rows.append(port_row)

        # -- Message Type --
        self.type_model = Gtk.ListStore(str, str) # Display, Internal Key
        self.type_model.append(["Note On/Off", "note_on"])
        self.type_model.append(["Control Change", "control_change"])
        self.type_model.append(["Program Change", "program_change"])
        self.type_model.append(["Note Off (Only)", "note_off"])

        type_row = ComboRow(title="Message Type", model=self.type_model)
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
        self.channel_row.set_title("Channel")
        self.channel_row.set_value(settings.get("channel", 0))
        self.channel_row.connect("notify::value", self.on_channel_changed)
        rows.append(self.channel_row)

        # -- Data 1 (Note/Control/Program) --
        self.data1_row = Adw.SpinRow.new_with_range(0, 127, 1)
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

        return rows

    def on_port_changed(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter:
            model = combo.get_model()
            port = model[tree_iter][0]
            settings = self.get_settings()
            settings["port"] = port
            self.set_settings(settings)

    def on_type_changed(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter:
            model = combo.get_model()
            msg_type = model[tree_iter][1]
            settings = self.get_settings()
            settings["msg_type"] = msg_type
            self.set_settings(settings)
            self.update_labels(msg_type)
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
            self.data1_row.set_title("Note Number")
            self.data2_row.set_title("Velocity")
            self.data2_row.set_visible(True)
        elif msg_type == "control_change":
            self.data1_row.set_title("Control Number")
            self.data2_row.set_title("Value")
            self.data2_row.set_visible(True)
        elif msg_type == "program_change":
            self.data1_row.set_title("Program Number")
            self.data2_row.set_visible(False)
