# Import StreamController modules
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.PluginManager.ActionHolder import ActionHolder
from src.backend.PluginManager.ActionInputSupport import ActionInputSupport
from src.backend.DeckManagement.InputIdentifier import Input

# Import actions
from .actions.SendNote.SendNote import SendNote
from .actions.SendCC.SendCC import SendCC
from .actions.SendProgramChange.SendProgramChange import SendProgramChange
from .actions.MidiDial.MidiDial import MidiDial


class MidiPlugin(PluginBase):
    """
    MIDI Plugin for StreamController.

    Provides general MIDI control functionality including:
    - Send MIDI Note On/Off messages
    - Send MIDI Control Change (CC) messages
    - Send MIDI Program Change messages
    - Dial/Knob control for volume and other CC parameters (Stream Deck Plus)
    """

    def __init__(self):
        super().__init__()

        # Send Note action - for MIDI note on/off
        self.send_note_holder = ActionHolder(
            plugin_base=self,
            action_base=SendNote,
            action_id="com_github_pkern90_midi::SendNote",
            action_name="Send Note",
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.UNSUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNSUPPORTED,
            }
        )
        self.add_action_holder(self.send_note_holder)

        # Send CC action - for Control Change messages
        self.send_cc_holder = ActionHolder(
            plugin_base=self,
            action_base=SendCC,
            action_id="com_github_pkern90_midi::SendCC",
            action_name="Send CC",
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.UNSUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNSUPPORTED,
            }
        )
        self.add_action_holder(self.send_cc_holder)

        # Send Program Change action
        self.send_program_holder = ActionHolder(
            plugin_base=self,
            action_base=SendProgramChange,
            action_id="com_github_pkern90_midi::SendProgramChange",
            action_name="Send Program Change",
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.UNSUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNSUPPORTED,
            }
        )
        self.add_action_holder(self.send_program_holder)

        # MIDI Dial action - for Stream Deck Plus knobs
        self.midi_dial_holder = ActionHolder(
            plugin_base=self,
            action_base=MidiDial,
            action_id="com_github_pkern90_midi::MidiDial",
            action_name="MIDI Dial",
            action_support={
                Input.Key: ActionInputSupport.UNSUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNSUPPORTED,
            }
        )
        self.add_action_holder(self.midi_dial_holder)

        # Register plugin
        self.register(
            plugin_name="MIDI",
            github_repo="https://github.com/pkern90/StreamController-Midi-Plugin",
            plugin_version="1.0.0",
            app_version="1.5.0-beta"
        )
