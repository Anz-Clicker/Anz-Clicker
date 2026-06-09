from __future__ import annotations

import json
from pathlib import Path

from actions import Action


class PresetStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.defaults: dict[str, dict] = {}
        self.custom_actions: dict[str, dict] = {}
        self.action_catalog: list[str] = []
        self.hidden_actions: list[str] = []
        self.settings: dict[str, str] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.defaults = {}
            self.custom_actions = {}
            self.action_catalog = []
            self.hidden_actions = []
            self.settings = {}
            return
        with self.path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.defaults = payload.get("defaults", {})
        self.custom_actions = payload.get("custom_actions", {})
        self.action_catalog = payload.get("action_catalog", [])
        self.hidden_actions = payload.get("hidden_actions", [])
        self.settings = payload.get("settings", {})

    def save(self) -> None:
        payload = {
            "defaults": self.defaults,
            "custom_actions": self.custom_actions,
            "action_catalog": self.action_catalog,
            "hidden_actions": self.hidden_actions,
            "settings": self.settings,
        }
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def default_for(self, action_type: str) -> Action | None:
        data = self.defaults.get(action_type)
        return Action.from_dict(data) if data else None

    def set_default(self, action: Action) -> None:
        stored = action.to_dict()
        stored["preset_name"] = ""
        self.defaults[action.action_type] = stored
        self.save()

    def reset_defaults(self) -> None:
        self.defaults = {}
        self.save()

    def delete_custom_action(self, name: str) -> None:
        self.custom_actions.pop(name, None)
        custom_label = f"Custom: {name}"
        self.action_catalog = [item for item in self.action_catalog if item != custom_label]
        self.hidden_actions = [item for item in self.hidden_actions if item != custom_label]
        self.save()

    def custom_names(self) -> list[str]:
        return sorted(self.custom_actions.keys(), key=str.lower)

    def custom_action(self, name: str) -> Action | None:
        data = self.custom_actions.get(name)
        return Action.from_dict(data) if data else None

    def save_custom_action(self, name: str, action: Action) -> None:
        stored = action.to_dict()
        stored["preset_name"] = name
        self.custom_actions[name] = stored
        self.save()

    def get_setting(self, key: str, default: str = "") -> str:
        return self.settings.get(key, default)

    def set_setting(self, key: str, value: str) -> None:
        self.settings[key] = value
        self.save()

    def ordered_action_names(self, built_in_names: list[str]) -> list[str]:
        available = built_in_names + [f"Custom: {name}" for name in self.custom_names()]
        ordered: list[str] = []
        for name in self.action_catalog:
            if name in available and name not in ordered:
                ordered.append(name)
        for name in available:
            if name not in ordered:
                ordered.append(name)
        return ordered

    def visible_action_names(self, built_in_names: list[str]) -> list[str]:
        return [name for name in self.ordered_action_names(built_in_names) if name not in self.hidden_actions]

    def set_action_catalog(self, ordered_names: list[str], hidden_names: list[str]) -> None:
        self.action_catalog = ordered_names
        self.hidden_actions = hidden_names
        self.save()

    def delete_or_hide_action(self, display_name: str, built_in_names: list[str]) -> None:
        if display_name.startswith("Custom: "):
            self.delete_custom_action(display_name.removeprefix("Custom: "))
            return

        self.defaults.pop(display_name, None)
        if display_name not in self.hidden_actions:
            self.hidden_actions.append(display_name)
        if display_name not in self.action_catalog:
            self.action_catalog = self.ordered_action_names(built_in_names)
        self.save()

    def reset_all_actions_to_default(self, built_in_names: list[str]) -> None:
        self.defaults = {}
        built_in_hidden = {name for name in self.hidden_actions if name in built_in_names}
        if built_in_hidden:
            self.hidden_actions = [name for name in self.hidden_actions if name not in built_in_hidden]
        custom_names = [name for name in self.action_catalog if name.startswith("Custom: ")]
        self.action_catalog = list(built_in_names)
        for name in custom_names:
            if name not in self.action_catalog and name in [f"Custom: {custom}" for custom in self.custom_names()]:
                self.action_catalog.append(name)
        self.save()
