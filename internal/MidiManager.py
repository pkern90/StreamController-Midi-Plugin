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
        port = cls._get_or_create_port(port_name)
        if port:
            try:
                msg = mido.Message('note_on', channel=channel, note=note, velocity=velocity)
                port.send(msg)
            except Exception as e:
                print(f"Error sending note on: {e}")

    @classmethod
    def send_note_off(cls, port_name, channel, note):
        """Send a MIDI Note Off message."""
        port = cls._get_or_create_port(port_name)
        if port:
            try:
                msg = mido.Message('note_off', channel=channel, note=note, velocity=0)
                port.send(msg)
            except Exception as e:
                print(f"Error sending note off: {e}")
