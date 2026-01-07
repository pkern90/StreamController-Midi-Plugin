"""
MidiManager - Handles MIDI communication.
"""
import mido


class MidiManager:
    """Static class for managing MIDI connections and sending messages."""

    _output_ports = {}

    @classmethod
    def get_output_ports(cls):
        """Get list of available MIDI output port names."""
        try:
            return mido.get_output_names()
        except Exception as e:
            print(f"Error getting MIDI ports: {e}")
            return []

    @classmethod
    def _get_or_create_port(cls, port_name):
        """Get or create a MIDI output port."""
        if not port_name:
            return None

        if port_name not in cls._output_ports:
            try:
                cls._output_ports[port_name] = mido.open_output(port_name)
            except Exception as e:
                print(f"Error opening MIDI port {port_name}: {e}")
                return None

        return cls._output_ports.get(port_name)

    @classmethod
    def send_note_on(cls, port_name, channel, note, velocity):
        """Send a MIDI Note On message."""
        cls.send_message(port_name, 'note_on', channel=int(channel), note=int(note), velocity=int(velocity))

    @classmethod
    def send_note_off(cls, port_name, channel, note):
        """Send a MIDI Note Off message."""
        cls.send_message(port_name, 'note_off', channel=int(channel), note=int(note), velocity=0)

    @classmethod
    def send_control_change(cls, port_name, channel, control, value):
        """Send a MIDI Control Change message."""
        cls.send_message(port_name, 'control_change', channel=int(channel), control=int(control), value=int(value))

    @classmethod
    def send_program_change(cls, port_name, channel, program):
        """Send a MIDI Program Change message."""
        cls.send_message(port_name, 'program_change', channel=int(channel), program=int(program))

    @classmethod
    def send_message(cls, port_name, msg_type, **kwargs):
        """Send a generic MIDI message.
        
        Args:
            port_name (str): The name of the MIDI output port.
            msg_type (str): The type of MIDI message (e.g., 'note_on', 'control_change').
            **kwargs: Additional arguments for the message (e.g., channel, note, velocity, control, value, program).
        """
        port = cls._get_or_create_port(port_name)
        if port:
            try:
                # Filter out None values from kwargs to avoid mido errors if optional args are passed as None
                clean_kwargs = {k: v for k, v in kwargs.items() if v is not None}
                msg = mido.Message(msg_type, **clean_kwargs)
                port.send(msg)
            except Exception as e:
                print(f"Error sending {msg_type}: {e}")
