"""Test setup: a fake AppDaemon Hass class, so the apps run without AppDaemon or Home Assistant.

Run from the repo root:  python -m pytest tests
"""
import sys
import types
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps"))


class FakeHass:
    """Records what an app does. Holds HA states, the app namespace and the log."""

    def __init__(self, *args, **kwargs):
        self.ha_states = {}  # HA entity states, as strings (like HA gives them)
        self.ha_attributes = {}  # {entity_id: {attribute: value}}, returned by get_state(..., attribute="all")
        self.namespaces = {}  # {namespace: {entity_id: state}}
        self.ha_written = {}  # {entity_id: {"state": ..., "attributes": ...}} written to HA
        self.logs = []  # [(level, message)]
        self.schedules = []  # [(callback name, time)]

    def get_state(self, entity_id, namespace=None, attribute=None, **kwargs):
        if namespace:
            return self.namespaces.get(namespace, {}).get(entity_id)
        if attribute == "all":
            if entity_id not in self.ha_states:
                return None
            return {"state": self.ha_states[entity_id], "attributes": self.ha_attributes.get(entity_id, {})}
        return self.ha_states.get(entity_id)

    def set_state(self, entity_id, state=None, attributes=None, namespace=None, **kwargs):
        if namespace:
            self.namespaces.setdefault(namespace, {})[entity_id] = state
        else:
            self.ha_written[entity_id] = {"state": state, "attributes": attributes or {}}

    def get_entity(self, entity_id, namespace=None):
        return SimpleNamespace(state=self.namespaces.get(namespace, {}).get(entity_id))

    def log(self, msg, level="INFO", **kwargs):
        self.logs.append((level, msg))

    def run_daily(self, callback, start, **kwargs):
        self.schedules.append((callback.__name__, start))


hassapi = types.ModuleType("appdaemon.plugins.hass.hassapi")
hassapi.Hass = FakeHass
for name in ("appdaemon", "appdaemon.plugins", "appdaemon.plugins.hass"):
    sys.modules.setdefault(name, types.ModuleType(name))
sys.modules["appdaemon.plugins.hass.hassapi"] = hassapi


@pytest.fixture
def freeze_today(monkeypatch):
    """Return a function that sets 'today' (date.today and datetime.now) in a module."""

    def freeze(module, year, month, day):
        class FrozenDate(date):
            @classmethod
            def today(cls):
                return cls(year, month, day)

        class FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(year, month, day, 16, 0, 1)

        monkeypatch.setattr(module, "date", FrozenDate)
        monkeypatch.setattr(module, "datetime", FrozenDateTime)

    return freeze
