from src.backend.PluginManager.ActionBase import ActionBase
import os

try:
    from ...internal.MidiManager import MidiManager
except ImportError:
    # Fallback if relative import fails
    MidiManager = None


class SendNote(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._note_on = False

    def on_ready(self) -> None:
        # Set icon if available
        icon_path = os.path.join(self.plugin_base.PATH, "assets", "note.png")
        if os.path.exists(icon_path):
            self.set_media(media_path=icon_path, size=0.75)
        self.set_bottom_label("Note 60", font_size=14)

    def on_key_down(self) -> None:
        # Send MIDI Note On (hardcoded: channel 0, note 60, velocity 100)
        if MidiManager:
            ports = MidiManager.get_output_ports()
            if ports:
                MidiManager.send_note_on(ports[0], 0, 60, 100)
                self._note_on = True
        self.set_bottom_label("ON", font_size=14)

    def on_key_up(self) -> None:
        # Send MIDI Note Off
        if self._note_on and MidiManager:
            ports = MidiManager.get_output_ports()
            if ports:
                MidiManager.send_note_off(ports[0], 0, 60)
            self._note_on = False
        self.set_bottom_label("Note 60", font_size=14)
