from src.backend.PluginManager.ActionBase import ActionBase
import os


class SendNote(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_ready(self) -> None:
        # Set icon if available
        icon_path = os.path.join(self.plugin_base.PATH, "assets", "note.png")
        if os.path.exists(icon_path):
            self.set_media(media_path=icon_path, size=0.75)
        self.set_bottom_label("MIDI", font_size=14)

    def on_key_down(self) -> None:
        # Placeholder - will add MIDI functionality later
        self.set_bottom_label("Pressed", font_size=12)

    def on_key_up(self) -> None:
        self.set_bottom_label("MIDI", font_size=14)
