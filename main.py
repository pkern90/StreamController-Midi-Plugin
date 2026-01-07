from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.PluginManager.ActionHolder import ActionHolder
from src.backend.PluginManager.ActionInputSupport import ActionInputSupport
from src.backend.DeckManagement.InputIdentifier import Input

from .actions.SendNote.SendNote import SendNote
from .actions.SendMidiCommand.SendMidiCommand import SendMidiCommand


class MidiPlugin(PluginBase):
    def __init__(self):
        super().__init__()

        # Register one basic action
        self.send_note_holder = ActionHolder(
            plugin_base=self,
            action_base=SendNote,
            action_id="com_github_pkern90_midi::SendNote",
            action_name="Send MIDI Note",
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.UNSUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNSUPPORTED,
            }
        )
        self.add_action_holder(self.send_note_holder)

        # Register custom command action
        self.send_command_holder = ActionHolder(
            plugin_base=self,
            action_base=SendMidiCommand,
            action_id="com_github_pkern90_midi::SendMidiCommand",
            action_name="Send MIDI Command",
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.UNSUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNSUPPORTED,
            }
        )
        self.add_action_holder(self.send_command_holder)

        # Register plugin
        self.register(
            plugin_name="MIDI",
            github_repo="https://github.com/pkern90/StreamController-Midi-Plugin",
            plugin_version="1.0.0",
            app_version="1.5.0-beta"
        )
