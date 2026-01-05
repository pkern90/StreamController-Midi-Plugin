"""
MIDI Manager module for handling MIDI port connections.
Provides a singleton-like interface for managing MIDI output ports.
"""

import mido
from loguru import logger


class MidiManager:
    """Manages MIDI output ports and provides utility methods for MIDI operations."""

    _instance = None
    _output_ports: dict[str, mido.ports.BaseOutput] = {}

    @classmethod
    def get_output_ports(cls) -> list[str]:
        """Get list of available MIDI output port names."""
        try:
            return mido.get_output_names()
        except Exception as e:
            logger.error(f"Failed to get MIDI output ports: {e}")
            return []

    @classmethod
    def get_input_ports(cls) -> list[str]:
        """Get list of available MIDI input port names."""
        try:
            return mido.get_input_names()
        except Exception as e:
            logger.error(f"Failed to get MIDI input ports: {e}")
            return []

    @classmethod
    def open_output(cls, port_name: str) -> mido.ports.BaseOutput | None:
        """
        Open a MIDI output port by name.
        Caches open ports for reuse.

        Args:
            port_name: Name of the MIDI port to open

        Returns:
            Open MIDI output port or None if failed
        """
        if not port_name:
            return None

        # Return cached port if already open
        if port_name in cls._output_ports:
            port = cls._output_ports[port_name]
            if not port.closed:
                return port
            # Remove closed port from cache
            del cls._output_ports[port_name]

        try:
            port = mido.open_output(port_name)
            cls._output_ports[port_name] = port
            logger.info(f"Opened MIDI output port: {port_name}")
            return port
        except Exception as e:
            logger.error(f"Failed to open MIDI output port '{port_name}': {e}")
            return None

    @classmethod
    def close_output(cls, port_name: str) -> None:
        """Close a specific MIDI output port."""
        if port_name in cls._output_ports:
            try:
                cls._output_ports[port_name].close()
                del cls._output_ports[port_name]
                logger.info(f"Closed MIDI output port: {port_name}")
            except Exception as e:
                logger.error(f"Failed to close MIDI output port '{port_name}': {e}")

    @classmethod
    def close_all_outputs(cls) -> None:
        """Close all open MIDI output ports."""
        for port_name in list(cls._output_ports.keys()):
            cls.close_output(port_name)

    @classmethod
    def send_message(cls, port_name: str, message: mido.Message) -> bool:
        """
        Send a MIDI message to the specified port.

        Args:
            port_name: Name of the MIDI port
            message: MIDI message to send

        Returns:
            True if message was sent successfully, False otherwise
        """
        port = cls.open_output(port_name)
        if port is None:
            return False

        try:
            port.send(message)
            logger.debug(f"Sent MIDI message: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to send MIDI message: {e}")
            return False

    @classmethod
    def send_note_on(cls, port_name: str, channel: int, note: int, velocity: int) -> bool:
        """Send a Note On message."""
        message = mido.Message('note_on', channel=channel, note=note, velocity=velocity)
        return cls.send_message(port_name, message)

    @classmethod
    def send_note_off(cls, port_name: str, channel: int, note: int, velocity: int = 0) -> bool:
        """Send a Note Off message."""
        message = mido.Message('note_off', channel=channel, note=note, velocity=velocity)
        return cls.send_message(port_name, message)

    @classmethod
    def send_control_change(cls, port_name: str, channel: int, control: int, value: int) -> bool:
        """Send a Control Change message."""
        message = mido.Message('control_change', channel=channel, control=control, value=value)
        return cls.send_message(port_name, message)

    @classmethod
    def send_program_change(cls, port_name: str, channel: int, program: int) -> bool:
        """Send a Program Change message."""
        message = mido.Message('program_change', channel=channel, program=program)
        return cls.send_message(port_name, message)
