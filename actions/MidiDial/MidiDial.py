"""
MidiDial Action - Dial/knob control for MIDI CC (e.g., volume control).
Designed for Stream Deck Plus encoders.
"""

from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.DeckManagement.InputIdentifier import Input
import os

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from plugins.com_github_pkern90_midi.internal.MidiManager import MidiManager


class MidiDial(ActionBase):
    """
    Dial action for controlling MIDI CC values with Stream Deck Plus knobs.

    Features:
    - Turn clockwise: Increase CC value
    - Turn counter-clockwise: Decrease CC value
    - Press dial: Toggle mute or send specific value
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_value = 100  # Track current value (0-127)
        self._muted = False
        self._pre_mute_value = 100

    def on_ready(self) -> None:
        """Initialize the action display."""
        # Load saved value if exists
        settings = self.get_settings()
        self._current_value = settings.get("current_value", 100)
        self._muted = settings.get("muted", False)
        self._pre_mute_value = settings.get("pre_mute_value", 100)

        self._update_display()

    def _update_display(self) -> None:
        """Update the dial display with current value."""
        settings = self.get_settings()
        channel = settings.get("channel", 0) + 1
        cc = settings.get("cc", 7)  # Default to volume

        icon_path = os.path.join(self.plugin_base.PATH, "assets", "dial.png")
        if os.path.exists(icon_path):
            self.set_media(media_path=icon_path, size=0.6)

        # Show current value and mute status
        if self._muted:
            self.set_top_label("MUTED", font_size=12, color=[255, 100, 100])
            self.set_bottom_label(f"Ch{channel} CC{cc}", font_size=10)
        else:
            # Calculate percentage (0-127 -> 0-100%)
            percent = int((self._current_value / 127) * 100)
            self.set_top_label(f"{percent}%", font_size=14)
            self.set_bottom_label(f"Ch{channel} CC{cc}", font_size=10)

    def event_callback(self, event, data: dict = None) -> None:
        """Handle dial events (rotation and press)."""
        settings = self.get_settings()
        port_name = settings.get("port", "")
        channel = settings.get("channel", 0)
        cc = settings.get("cc", 7)
        step = settings.get("step", 4)

        # Handle rotation events
        if event == Input.Dial.Events.TURN_CW:
            # Clockwise - increase value
            self._current_value = min(127, self._current_value + step)
            self._muted = False
            self._send_cc(port_name, channel, cc, self._current_value)
            self._save_state()
            self._update_display()

        elif event == Input.Dial.Events.TURN_CCW:
            # Counter-clockwise - decrease value
            self._current_value = max(0, self._current_value - step)
            self._muted = False
            self._send_cc(port_name, channel, cc, self._current_value)
            self._save_state()
            self._update_display()

        elif event == Input.Dial.Events.SHORT_UP:
            # Short press - toggle mute
            press_action = settings.get("press_action", "mute")

            if press_action == "mute":
                if self._muted:
                    # Unmute - restore previous value
                    self._current_value = self._pre_mute_value
                    self._muted = False
                else:
                    # Mute - save current value and set to 0
                    self._pre_mute_value = self._current_value
                    self._current_value = 0
                    self._muted = True

                self._send_cc(port_name, channel, cc, self._current_value)
                self._save_state()
                self._update_display()

            elif press_action == "reset":
                # Reset to default value
                default_value = settings.get("default_value", 100)
                self._current_value = default_value
                self._muted = False
                self._send_cc(port_name, channel, cc, self._current_value)
                self._save_state()
                self._update_display()

            elif press_action == "send_value":
                # Send a specific value
                press_value = settings.get("press_value", 127)
                self._send_cc(port_name, channel, cc, press_value)

    def _send_cc(self, port_name: str, channel: int, cc: int, value: int) -> None:
        """Send a CC message."""
        MidiManager.send_control_change(port_name, channel, cc, value)

    def _save_state(self) -> None:
        """Save current state to settings."""
        settings = self.get_settings()
        settings["current_value"] = self._current_value
        settings["muted"] = self._muted
        settings["pre_mute_value"] = self._pre_mute_value
        self.set_settings(settings)

    def on_key_down(self) -> None:
        """Handle key press (for compatibility with key placement)."""
        pass

    def on_key_up(self) -> None:
        """Handle key release."""
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

        # CC Number selector
        self.cc_spin = Adw.SpinRow.new_with_range(0, 127, 1)
        self.cc_spin.set_title("CC Number")
        self.cc_spin.set_subtitle("7 = Volume, 10 = Pan, etc.")
        self.cc_spin.set_value(settings.get("cc", 7))
        self.cc_spin.connect("changed", self._on_cc_changed)

        # Step size for rotation
        self.step_spin = Adw.SpinRow.new_with_range(1, 20, 1)
        self.step_spin.set_title("Step Size")
        self.step_spin.set_subtitle("Value change per rotation click")
        self.step_spin.set_value(settings.get("step", 4))
        self.step_spin.connect("changed", self._on_step_changed)

        # Press action selector
        self.press_combo = Adw.ComboRow()
        self.press_combo.set_title("Press Action")
        self.press_combo.set_subtitle("What happens when dial is pressed")

        actions = ["Mute/Unmute", "Reset to default", "Send specific value"]
        action_values = ["mute", "reset", "send_value"]
        action_list = Gtk.StringList.new(actions)
        self.press_combo.set_model(action_list)

        current_action = settings.get("press_action", "mute")
        if current_action in action_values:
            self.press_combo.set_selected(action_values.index(current_action))

        self.press_combo.connect("notify::selected", self._on_press_action_changed)
        self._action_values = action_values

        # Default value (for reset action)
        self.default_spin = Adw.SpinRow.new_with_range(0, 127, 1)
        self.default_spin.set_title("Default Value")
        self.default_spin.set_subtitle("Value used for reset (100 = ~80%)")
        self.default_spin.set_value(settings.get("default_value", 100))
        self.default_spin.connect("changed", self._on_default_changed)

        # Press value (for send_value action)
        self.press_value_spin = Adw.SpinRow.new_with_range(0, 127, 1)
        self.press_value_spin.set_title("Press Value")
        self.press_value_spin.set_subtitle("Value sent on press (if 'Send specific value')")
        self.press_value_spin.set_value(settings.get("press_value", 127))
        self.press_value_spin.connect("changed", self._on_press_value_changed)

        return [self.port_combo, self.channel_spin, self.cc_spin,
                self.step_spin, self.press_combo, self.default_spin,
                self.press_value_spin]

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

    def _on_step_changed(self, spin) -> None:
        """Handle step size change."""
        settings = self.get_settings()
        settings["step"] = int(spin.get_value())
        self.set_settings(settings)

    def _on_press_action_changed(self, combo, _param) -> None:
        """Handle press action change."""
        selected = combo.get_selected()
        settings = self.get_settings()
        settings["press_action"] = self._action_values[selected]
        self.set_settings(settings)

    def _on_default_changed(self, spin) -> None:
        """Handle default value change."""
        settings = self.get_settings()
        settings["default_value"] = int(spin.get_value())
        self.set_settings(settings)

    def _on_press_value_changed(self, spin) -> None:
        """Handle press value change."""
        settings = self.get_settings()
        settings["press_value"] = int(spin.get_value())
        self.set_settings(settings)
