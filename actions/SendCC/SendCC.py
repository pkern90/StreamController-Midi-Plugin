"""
SendCC Action - Sends MIDI Control Change messages.
"""

from src.backend.PluginManager.ActionBase import ActionBase
import os

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from plugins.com_github_pkern90_midi.internal.MidiManager import MidiManager


# Common CC names for display
CC_NAMES = {
    0: "Bank Select",
    1: "Modulation",
    7: "Volume",
    10: "Pan",
    11: "Expression",
    64: "Sustain Pedal",
    91: "Reverb",
    93: "Chorus",
}


class SendCC(ActionBase):
    """Action to send MIDI Control Change messages."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._toggle_state = False

    def on_ready(self) -> None:
        """Initialize the action display."""
        self._update_display()

    def _update_display(self) -> None:
        """Update the button display based on current state."""
        settings = self.get_settings()
        cc = settings.get("cc", 7)
        channel = settings.get("channel", 0) + 1
        value = settings.get("value", 127)

        icon_path = os.path.join(self.plugin_base.PATH, "assets", "cc.png")
        if os.path.exists(icon_path):
            self.set_media(media_path=icon_path, size=0.75)

        # Show CC name if known, otherwise just the number
        cc_name = CC_NAMES.get(cc, f"CC{cc}")
        if cc in CC_NAMES:
            self.set_bottom_label(f"Ch{channel} {cc_name}", font_size=10)
        else:
            self.set_bottom_label(f"Ch{channel} CC{cc}", font_size=12)

    def on_key_down(self) -> None:
        """Handle key press - send CC message."""
        settings = self.get_settings()
        port_name = settings.get("port", "")
        channel = settings.get("channel", 0)
        cc = settings.get("cc", 7)
        value = settings.get("value", 127)
        value_off = settings.get("value_off", 0)
        mode = settings.get("mode", "single")

        if mode == "single":
            # Send single CC value
            MidiManager.send_control_change(port_name, channel, cc, value)
        elif mode == "momentary":
            # Momentary: send value on press, value_off on release
            MidiManager.send_control_change(port_name, channel, cc, value)
        elif mode == "toggle":
            # Toggle between value and value_off
            if self._toggle_state:
                MidiManager.send_control_change(port_name, channel, cc, value_off)
            else:
                MidiManager.send_control_change(port_name, channel, cc, value)
            self._toggle_state = not self._toggle_state

    def on_key_up(self) -> None:
        """Handle key release - for momentary mode."""
        settings = self.get_settings()
        mode = settings.get("mode", "single")

        if mode == "momentary":
            port_name = settings.get("port", "")
            channel = settings.get("channel", 0)
            cc = settings.get("cc", 7)
            value_off = settings.get("value_off", 0)
            MidiManager.send_control_change(port_name, channel, cc, value_off)

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

        # CC Number selector
        self.cc_spin = Adw.SpinRow.new_with_range(0, 127, 1)
        self.cc_spin.set_title("CC Number")
        self.cc_spin.set_subtitle("Control Change number (0-127)")
        self.cc_spin.set_value(settings.get("cc", 7))
        self.cc_spin.connect("changed", self._on_cc_changed)

        # Value selector (for "on" state)
        self.value_spin = Adw.SpinRow.new_with_range(0, 127, 1)
        self.value_spin.set_title("Value (On)")
        self.value_spin.set_subtitle("Value sent when pressed or 'on'")
        self.value_spin.set_value(settings.get("value", 127))
        self.value_spin.connect("changed", self._on_value_changed)

        # Value Off selector (for toggle/momentary modes)
        self.value_off_spin = Adw.SpinRow.new_with_range(0, 127, 1)
        self.value_off_spin.set_title("Value (Off)")
        self.value_off_spin.set_subtitle("Value sent when released or 'off'")
        self.value_off_spin.set_value(settings.get("value_off", 0))
        self.value_off_spin.connect("changed", self._on_value_off_changed)

        # Mode selector
        self.mode_combo = Adw.ComboRow()
        self.mode_combo.set_title("Mode")

        modes = ["Single (send on press)", "Momentary (hold)", "Toggle"]
        mode_values = ["single", "momentary", "toggle"]
        mode_list = Gtk.StringList.new(modes)
        self.mode_combo.set_model(mode_list)

        current_mode = settings.get("mode", "single")
        if current_mode in mode_values:
            self.mode_combo.set_selected(mode_values.index(current_mode))

        self.mode_combo.connect("notify::selected", self._on_mode_changed)
        self._mode_values = mode_values

        return [self.port_combo, self.channel_spin, self.cc_spin,
                self.value_spin, self.value_off_spin, self.mode_combo]

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

    def _on_cc_changed(self, spin) -> None:
        """Handle CC number change."""
        settings = self.get_settings()
        settings["cc"] = int(spin.get_value())
        self.set_settings(settings)
        self._update_display()

    def _on_value_changed(self, spin) -> None:
        """Handle value change."""
        settings = self.get_settings()
        settings["value"] = int(spin.get_value())
        self.set_settings(settings)

    def _on_value_off_changed(self, spin) -> None:
        """Handle value_off change."""
        settings = self.get_settings()
        settings["value_off"] = int(spin.get_value())
        self.set_settings(settings)

    def _on_mode_changed(self, combo, _param) -> None:
        """Handle mode change."""
        selected = combo.get_selected()
        settings = self.get_settings()
        settings["mode"] = self._mode_values[selected]
        self.set_settings(settings)
