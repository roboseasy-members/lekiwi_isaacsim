"""다른 단축키를 유지하며 앱 실행 중 Space를 로봇 정지에 사용한다."""


class SpaceStopBinding:
    def __init__(self, registry, key):
        self.registry = registry
        self.removed = []
        for hotkey in registry.get_all_hotkeys_for_key(key):
            if hotkey.action and hotkey.action.id == "toolbar::play":
                if registry.deregister_hotkey(hotkey):
                    self.removed.append(hotkey)

    def close(self):
        for hotkey in self.removed:
            self.registry.register_hotkey(hotkey)
        self.removed.clear()


class RecordingKeyBinding:
    """실습 키와 기본 UI 단축키의 중복 실행을 앱 안에서만 막습니다."""
    def __init__(self, registry, key):
        self.registry = registry
        self.removed = []
        for hotkey in list(registry.get_all_hotkeys_for_key(key)):
            if registry.deregister_hotkey(hotkey):
                self.removed.append(hotkey)

    def close(self):
        for hotkey in self.removed:
            self.registry.register_hotkey(hotkey)
        self.removed.clear()
