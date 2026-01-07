# StreamController Plugin Development Instructions

You are an expert developer for the StreamController application, specifically working on the **StreamController-Midi-Plugin**.

## Project Architecture

This is a Python-based plugin for StreamController 1.5.0-beta+. It follows the standard StreamController plugin architecture:

- **Entry Point**: `main.py` defines the plugin class which inherits from `src.backend.PluginManager.PluginBase.PluginBase`.
- **Actions**: Individual actions (like "Send Note") reside in `actions/<ActionName>/<ActionName>.py` and inherit from `src.backend.PluginManager.ActionBase.ActionBase`.
- **Internal Logic**: Shared logic (like MIDI handling) is placed in `internal/` and imported dynamically.
- **Metadata**: `manifest.json` defines plugin identity, version, and capabilities.

## Code Patterns & Conventions

### 1. Core Imports

The environment provides the `src.backend` package. **Do not** attempt to install this; it is part of the host application.

```python
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.ActionHolder import ActionHolder
from src.backend.PluginManager.ActionInputSupport import ActionInputSupport
from src.backend.DeckManagement.InputIdentifier import Input
from src.Signals import Signals
```

### 2. Internal Module Imports

To import modules from `internal/` or other plugin directories, you must modify `sys.path` dynamically within each class that needs them.

**Pattern:**

```python
# In Action.__init__ or methods
try:
    plugin_path = self.plugin_base.PATH
    if plugin_path not in sys.path:
        sys.path.insert(0, plugin_path)
    from internal.MidiManager import MidiManager
    self._manager = MidiManager
except Exception as e:
    self.log_error(f"Failed to import manager: {e}")
```

### 3. Action Lifecycle & Threading

Override `ActionBase` methods to handle events. Note the threading model:

- `on_ready()`: Called when deck is fully loaded. **Use this for initial UI update** (images/labels), not `__init__`.
- `on_key_down()` / `on_key_up()`: **Dedicated Thread**. You can perform time-consuming tasks here without blocking the UI.
- `on_tick()`: Called every second. **Shared Thread**. Must be extremely fast; do not block here.
- `on_dial_rotate(steps)`, `on_dial_down()`, `on_dial_up()`: Stream Deck Plus interactions.

### 4. UI Feedback Methods

- `self.set_center_label(text)`: Set text in center.
- `self.set_bottom_label(text)`: Set text at bottom.
- `self.set_media(media_path=path)`: Set the icon.
- `self.show_error(message)`: Display error to user.

### 5. Configuration UI (`get_config_rows`)

Configuration UI is built using GTK 4 and Libadwaita.

- **Return Type**: `list` of GTK/Adw widgets.
- **Persistence**: Use `self.get_settings()` (dict) to read/write config.
- **Helper**: Use `GtkHelper.ComboRow` if available, otherwise fall back to `Adw.ActionRow` or `Adw.SpinRow`.

**Example (SpinRow):**

```python
def get_config_rows(self) -> list:
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw

    spinner = Adw.SpinRow.new_with_range(0, 127, 1)
    spinner.set_title("Value")
    spinner.set_subtitle("MIDI value to send")

    # Bind to settings manually or via signal handlers
    # ...
    return [spinner]
```

### 6. Signal Handling

Subscribe to global app events (like page changes) using `connect`.

```python
# In __init__ or on_ready
self.connect(signal=Signals.PageRename, callback=self.on_page_rename)

def on_page_rename(self, old_path, new_path):
    pass
```

### 7. Localization

All user-visible strings usually support localization.

- **File**: `locales/en_US.json` (keys must be flat, no nested dicts).
- **Usage**: `self.plugin_base.locale_manager.get("my.key")`.

## Manifest & ID Rules

- **Plugin ID**: Reverse domain ID with **underscores only** (no dots). Example: `com_github_pkern90_midi`.
- **Action ID**: `<PluginID>::<ActionName>`. Example: `com_github_pkern90_midi::SendNote`.

## Development Workflow

1.  **Modify Code**: Edits in `actions/` or `internal/` take effect after restarting StreamController.
2.  **Manifest**: Update `manifest.json` versions and descriptions.
3.  **Logs**: Use `print()` for debugging (visible in StreamController terminal/logs).
