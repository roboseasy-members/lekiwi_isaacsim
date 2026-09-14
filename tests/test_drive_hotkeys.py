from pathlib import Path
from types import SimpleNamespace as NS
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'isaac_sim'))
from drive_hotkeys import SpaceStopBinding


def test_only_space_timeline_binding_is_temporarily_removed():
    play = NS(action=NS(id='toolbar::play'))
    custom = NS(action=NS(id='user_action'))
    unbound = NS(action=None)
    keys = [play, custom, unbound]
    def remove(key):
        keys.remove(key)
        return True
    registry = NS(get_all_hotkeys_for_key=lambda key: list(keys),
                  deregister_hotkey=remove, register_hotkey=lambda key: keys.append(key))
    binding = SpaceStopBinding(registry, 'SPACE')
    assert keys == [custom, unbound]
    binding.close()
    assert keys == [custom, unbound, play]
    binding.close()
    assert len(keys) == 3


@pytest.mark.parametrize("key,action", [("F7", "toggle_ui"), ("F10", "capture")])
def test_recording_key_override_preserves_other_keys_and_restores_once(key, action):
    from drive_hotkeys import RecordingKeyBinding
    original = NS(action=NS(id=action))
    keys = {key: [original], "F11": ["other"]}
    def remove(hotkey):
        keys[key].remove(hotkey)
        return True
    registry = NS(get_all_hotkeys_for_key=lambda key: keys[key],
                  deregister_hotkey=remove, register_hotkey=lambda hotkey: keys[key].append(hotkey))
    binding = RecordingKeyBinding(registry, key)
    assert keys == {key: [], "F11": ["other"]}
    binding.close()
    binding.close()
    assert keys == {key: [original], "F11": ["other"]}
