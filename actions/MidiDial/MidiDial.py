from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.EventAssigner import EventAssigner
from src.backend.DeckManagement.InputIdentifier import Input
import sys
import os

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


class MidiDial(ActionBase):
    """
    Action for Stream Deck+ dials/knobs to control MIDI CC values.
    Rotate the dial to increase/decrease the CC value (e.g., volume).
    Press the dial to reset to default or toggle mute.
    """

    # Common MIDI CC numbers for reference
    CC_VOLUME = 7
    CC_PAN = 10
    CC_EXPRESSION = 11
    CC_MODULATION = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._midi_manager = None
        self._current_value = 64  # Start at midpoint
        self._is_muted = False
        self._pre_mute_value = 64
        self._load_midi_manager()
        
        # Register dial-specific event assigners
        self._register_dial_events()

    def _register_dial_events(self):
        """Register event assigners for dial rotation events."""
        # Clear the default key event assigners from ActionBase that don't apply to dials
        self.clear_event_assigners()
        
        # Add dial-specific event assigners
        self.add_event_assigner(EventAssigner(
            id="Dial Down",
            ui_label="Dial Down",
            default_events=[Input.Dial.Events.DOWN],
            callback=self.on_dial_down
        ))
        self.add_event_assigner(EventAssigner(
            id="Dial Up",
            ui_label="Dial Up",
            default_events=[Input.Dial.Events.UP],
            callback=self.on_dial_up
        ))
        self.add_event_assigner(EventAssigner(
            id="Dial Turn CW",
            ui_label="Dial Turn CW",
            default_events=[Input.Dial.Events.TURN_CW],
            callback=self.on_dial_turn_cw
        ))
        self.add_event_assigner(EventAssigner(
            id="Dial Turn CCW",
            ui_label="Dial Turn CCW",
            default_events=[Input.Dial.Events.TURN_CCW],
            callback=self.on_dial_turn_ccw
        ))

    def _load_midi_manager(self):
        """Dynamically load the MidiManager from the plugin's internal directory."""
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
        """Called when the deck is fully loaded. Initialize the dial display."""
        # Initialize settings with defaults if not set
        self._ensure_default_settings()
        
        settings = self.get_settings()
        self._current_value = settings.get("current_value", settings.get("default_value", 64))
        self._is_muted = settings.get("is_muted", False)
        
        self._update_display()
        
        # Send initial value if configured
        if settings.get("send_on_ready", False):
            self._send_cc_value()

    def _ensure_default_settings(self):
        """Ensure settings have default values."""
        settings = self.get_settings()
        defaults = {
            "channel": 0,
            "cc_number": 7,  # Volume
            "step_size": 4,
            "default_value": 64,
            "min_value": 0,
            "max_value": 127,
            "press_action": "mute",
            "display_mode": "value",
            "send_on_ready": False,
        }
        changed = False
        for key, default in defaults.items():
            if key not in settings:
                settings[key] = default
                changed = True
        if changed:
            self.set_settings(settings)

    def on_dial_rotate(self, direction: int) -> None:
        """
        Called when the dial is rotated.
        
        Args:
            direction: Positive for clockwise, negative for counter-clockwise.
                       The magnitude indicates the number of steps.
        """
        if self._is_muted:
            # Unmute on rotation
            self._is_muted = False
            self._current_value = self._pre_mute_value
        
        settings = self.get_settings()
        step_size = settings.get("step_size", 4)
        min_value = settings.get("min_value", 0)
        max_value = settings.get("max_value", 127)
        
        # Calculate new value
        change = direction * step_size
        self._current_value = max(min_value, min(max_value, self._current_value + change))
        
        # Save current value
        settings["current_value"] = self._current_value
        settings["is_muted"] = False
        self.set_settings(settings)
        
        # Send MIDI CC
        self._send_cc_value()
        
        # Update display
        self._update_display()

    def on_dial_turn_cw(self, data=None) -> None:
        """Called when the dial is rotated clockwise."""
        self.on_dial_rotate(1)

    def on_dial_turn_ccw(self, data=None) -> None:
        """Called when the dial is rotated counter-clockwise."""
        self.on_dial_rotate(-1)

    def on_dial_down(self, data=None) -> None:
        """Called when the dial is pressed down. Toggle mute or reset to default."""
        settings = self.get_settings()
        press_action = settings.get("press_action", "mute")
        
        if press_action == "mute":
            self._toggle_mute()
        elif press_action == "reset":
            self._reset_to_default()
        elif press_action == "send_value":
            # Just send the current value (useful for some applications)
            self._send_cc_value()

    def on_dial_up(self, data=None) -> None:
        """Called when the dial is released. Currently not used."""
        pass

    def _toggle_mute(self) -> None:
        """Toggle mute state - sends 0 when muted, previous value when unmuted."""
        settings = self.get_settings()
        
        if self._is_muted:
            # Unmute - restore previous value
            self._is_muted = False
            self._current_value = self._pre_mute_value
        else:
            # Mute - save current value and set to 0
            self._pre_mute_value = self._current_value
            self._is_muted = True
            self._current_value = 0
        
        settings["is_muted"] = self._is_muted
        settings["current_value"] = self._current_value
        settings["pre_mute_value"] = self._pre_mute_value
        self.set_settings(settings)
        
        self._send_cc_value()
        self._update_display()

    def _reset_to_default(self) -> None:
        """Reset the value to the configured default."""
        settings = self.get_settings()
        self._current_value = settings.get("default_value", 64)
        self._is_muted = False
        
        settings["current_value"] = self._current_value
        settings["is_muted"] = False
        self.set_settings(settings)
        
        self._send_cc_value()
        self._update_display()

    def _send_cc_value(self) -> None:
        """Send the current CC value via MIDI."""
        if not self._midi_manager:
            self.show_error(duration=1)
            return
        
        settings = self.get_settings()
        port_name = settings.get("port", "")
        if not port_name:
            self.show_error(duration=1)
            return
        
        channel = settings.get("channel", 0)
        cc_number = settings.get("cc_number", self.CC_VOLUME)
        
        self._midi_manager.send_control_change(port_name, channel, cc_number, self._current_value)

    def _update_display(self) -> None:
        """Update the dial's visual display."""
        settings = self.get_settings()
        cc_number = settings.get("cc_number", self.CC_VOLUME)
        display_mode = settings.get("display_mode", "value")
        
        # Set icon based on state - fall back to dial.png if muted.png doesn't exist
        icon_name = "dial.png"
        if self._is_muted:
            muted_path = os.path.join(self.plugin_base.PATH, "assets", "muted.png")
            if os.path.exists(muted_path):
                icon_name = "muted.png"
        
        icon_path = os.path.join(self.plugin_base.PATH, "assets", icon_name)
        if os.path.exists(icon_path):
            self.set_media(media_path=icon_path, size=0.75)
        
        # Get CC name for display
        cc_name = self._get_cc_name(cc_number)
        
        # Set labels based on display mode
        if display_mode == "percent":
            percent = int((self._current_value / 127) * 100)
            value_text = f"{percent}%"
        else:
            value_text = str(self._current_value)
        
        if self._is_muted:
            value_text = self._lm("display.mute")
        
        self.set_top_label(cc_name, font_size=12)
        self.set_center_label(value_text, font_size=18)
        
        # Update dial indicator (if supported)
        try:
            min_val = settings.get("min_value", 0)
            max_val = settings.get("max_value", 127)
            # Normalize to 0-1 range for the dial indicator
            normalized = (self._current_value - min_val) / (max_val - min_val) if max_val > min_val else 0
            self.set_dial_indicator(normalized)
        except Exception:
            # set_dial_indicator might not be available in all versions
            pass

    def _get_cc_name(self, cc_number: int) -> str:
        """Get a human-readable name for common CC numbers."""
        cc_names = {
            0: self._lm("cc_name.bank_msb"),
            1: self._lm("cc_name.mod_wheel"),
            7: self._lm("cc_name.volume"),
            10: self._lm("cc_name.pan"),
            11: self._lm("cc_name.expression"),
            64: self._lm("cc_name.sustain"),
            91: self._lm("cc_name.reverb"),
            93: self._lm("cc_name.chorus"),
        }
        return cc_names.get(cc_number, f"CC {cc_number}")

    def get_config_rows(self) -> list:
        """Return configuration rows for the action."""
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
        active_index = 0
        for i, row in enumerate(self.port_model):
            if row[0] == current_port:
                active_index = i
                break
        self.port_row.combo_box.set_active(active_index)
        self.port_row.combo_box.connect("changed", self._on_port_changed)
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

        # -- Channel --
        self.channel_row = Adw.SpinRow.new_with_range(0, 15, 1)
        self.channel_row.set_title(self._lm("config.channel"))
        self.channel_row.set_subtitle(self._lm("config.channel.subtitle"))
        self.channel_row.set_value(settings.get("channel", 0))
        self.channel_row.connect("notify::value", self._on_channel_changed)
        rows.append(self.channel_row)

        # -- CC Number Selection --
        self.cc_model = Gtk.ListStore(str, int)  # Display name, CC number
        cc_options = [
            (self._lm("config.cc.volume"), 7),
            (self._lm("config.cc.pan"), 10),
            (self._lm("config.cc.expression"), 11),
            (self._lm("config.cc.modulation"), 1),
            (self._lm("config.cc.sustain"), 64),
            (self._lm("config.cc.reverb"), 91),
            (self._lm("config.cc.chorus"), 93),
        ]
        # Add common CCs
        for name, num in cc_options:
            self.cc_model.append([name, num])
        # Add all other CCs
        used_ccs = {num for _, num in cc_options}
        for i in range(128):
            if i not in used_ccs:
                self.cc_model.append([f"CC {i}", i])
        
        self.cc_row = ComboRow(title=self._lm("config.cc_number"), model=self.cc_model)
        cc_renderer = Gtk.CellRendererText()
        self.cc_row.combo_box.pack_start(cc_renderer, True)
        self.cc_row.combo_box.add_attribute(cc_renderer, "text", 0)
        
        current_cc = settings.get("cc_number", 7)
        cc_active_index = 0
        for i, row in enumerate(self.cc_model):
            if row[1] == current_cc:
                cc_active_index = i
                break
        self.cc_row.combo_box.set_active(cc_active_index)
        self.cc_row.combo_box.connect("changed", self._on_cc_changed)
        rows.append(self.cc_row)

        # -- Step Size --
        self.step_row = Adw.SpinRow.new_with_range(1, 32, 1)
        self.step_row.set_title(self._lm("config.step_size"))
        self.step_row.set_subtitle(self._lm("config.step_size.subtitle"))
        self.step_row.set_value(settings.get("step_size", 4))
        self.step_row.connect("notify::value", self._on_step_changed)
        rows.append(self.step_row)

        # -- Default Value --
        self.default_row = Adw.SpinRow.new_with_range(0, 127, 1)
        self.default_row.set_title(self._lm("config.default_value"))
        self.default_row.set_subtitle(self._lm("config.default_value.subtitle"))
        self.default_row.set_value(settings.get("default_value", 64))
        self.default_row.connect("notify::value", self._on_default_changed)
        rows.append(self.default_row)

        # -- Min Value --
        self.min_row = Adw.SpinRow.new_with_range(0, 127, 1)
        self.min_row.set_title(self._lm("config.min_value"))
        self.min_row.set_value(settings.get("min_value", 0))
        self.min_row.connect("notify::value", self._on_min_changed)
        rows.append(self.min_row)

        # -- Max Value --
        self.max_row = Adw.SpinRow.new_with_range(0, 127, 1)
        self.max_row.set_title(self._lm("config.max_value"))
        self.max_row.set_value(settings.get("max_value", 127))
        self.max_row.connect("notify::value", self._on_max_changed)
        rows.append(self.max_row)

        # -- Press Action --
        self.press_model = Gtk.ListStore(str, str)  # Display, internal key
        self.press_model.append([self._lm("config.press_action.mute"), "mute"])
        self.press_model.append([self._lm("config.press_action.reset"), "reset"])
        self.press_model.append([self._lm("config.press_action.send"), "send_value"])
        
        self.press_row = ComboRow(title=self._lm("config.press_action"), model=self.press_model)
        press_renderer = Gtk.CellRendererText()
        self.press_row.combo_box.pack_start(press_renderer, True)
        self.press_row.combo_box.add_attribute(press_renderer, "text", 0)
        
        current_press = settings.get("press_action", "mute")
        press_active_index = 0
        for i, row in enumerate(self.press_model):
            if row[1] == current_press:
                press_active_index = i
                break
        self.press_row.combo_box.set_active(press_active_index)
        self.press_row.combo_box.connect("changed", self._on_press_action_changed)
        rows.append(self.press_row)

        # -- Display Mode --
        self.display_model = Gtk.ListStore(str, str)
        self.display_model.append([self._lm("config.display_mode.value"), "value"])
        self.display_model.append([self._lm("config.display_mode.percent"), "percent"])
        
        self.display_row = ComboRow(title=self._lm("config.display_mode"), model=self.display_model)
        display_renderer = Gtk.CellRendererText()
        self.display_row.combo_box.pack_start(display_renderer, True)
        self.display_row.combo_box.add_attribute(display_renderer, "text", 0)
        
        current_display = settings.get("display_mode", "value")
        display_active_index = 0
        for i, row in enumerate(self.display_model):
            if row[1] == current_display:
                display_active_index = i
                break
        self.display_row.combo_box.set_active(display_active_index)
        self.display_row.combo_box.connect("changed", self._on_display_changed)
        rows.append(self.display_row)

        # -- Send on Ready --
        self.send_ready_row = Adw.SwitchRow()
        self.send_ready_row.set_title(self._lm("config.send_on_ready"))
        self.send_ready_row.set_subtitle(self._lm("config.send_on_ready.subtitle"))
        self.send_ready_row.set_active(settings.get("send_on_ready", False))
        self.send_ready_row.connect("notify::active", self._on_send_ready_changed)
        rows.append(self.send_ready_row)

        return rows

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

    def _on_port_changed(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter:
            model = combo.get_model()
            port = model[tree_iter][0]
            settings = self.get_settings()
            settings["port"] = port
            self.set_settings(settings)

    def _on_channel_changed(self, widget, param):
        settings = self.get_settings()
        settings["channel"] = int(widget.get_value())
        self.set_settings(settings)

    def _on_cc_changed(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter:
            model = combo.get_model()
            cc_number = model[tree_iter][1]
            settings = self.get_settings()
            settings["cc_number"] = cc_number
            self.set_settings(settings)
            self._update_display()

    def _on_step_changed(self, widget, param):
        settings = self.get_settings()
        settings["step_size"] = int(widget.get_value())
        self.set_settings(settings)

    def _on_default_changed(self, widget, param):
        settings = self.get_settings()
        settings["default_value"] = int(widget.get_value())
        self.set_settings(settings)

    def _on_min_changed(self, widget, param):
        settings = self.get_settings()
        settings["min_value"] = int(widget.get_value())
        self.set_settings(settings)
        self._update_display()

    def _on_max_changed(self, widget, param):
        settings = self.get_settings()
        settings["max_value"] = int(widget.get_value())
        self.set_settings(settings)
        self._update_display()

    def _on_press_action_changed(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter:
            model = combo.get_model()
            action = model[tree_iter][1]
            settings = self.get_settings()
            settings["press_action"] = action
            self.set_settings(settings)

    def _on_display_changed(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter:
            model = combo.get_model()
            mode = model[tree_iter][1]
            settings = self.get_settings()
            settings["display_mode"] = mode
            self.set_settings(settings)
            self._update_display()

    def _on_send_ready_changed(self, widget, param):
        settings = self.get_settings()
        settings["send_on_ready"] = widget.get_active()
        self.set_settings(settings)
