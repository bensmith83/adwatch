"""Plugin registry and @register_parser decorator for adwatch."""

import re
import struct
from dataclasses import dataclass


@dataclass
class ParserInfo:
    name: str
    description: str
    version: str
    core: bool
    instance: object
    enabled: bool = True


class ParserRegistry:
    def __init__(self):
        self._parsers: list[dict] = []

    def register(self, *, name, company_id=None, service_uuid=None,
                 local_name_pattern=None, description, version, core, instance):
        self._parsers.append({
            "name": name,
            "company_id": company_id,
            "service_uuid": service_uuid,
            "local_name_pattern": local_name_pattern,
            "description": description,
            "version": version,
            "core": core,
            "instance": instance,
            "enabled": True,
        })

    def match(self, raw):
        matched = []
        for entry in self._parsers:
            if entry["enabled"] and self._entry_matches(entry, raw):
                matched.append(entry["instance"])
        return matched

    def set_enabled(self, name: str, enabled: bool):
        for entry in self._parsers:
            if entry["name"] == name:
                entry["enabled"] = enabled
                return
        raise ValueError(f"Parser '{name}' not found")

    def _entry_matches(self, entry, raw):
        # OR logic: any criterion matching is sufficient
        if entry["company_id"] is not None:
            if raw.manufacturer_data and len(raw.manufacturer_data) >= 2:
                ad_company = int.from_bytes(raw.manufacturer_data[:2], "little")
                cid = entry["company_id"]
                if isinstance(cid, (list, tuple)):
                    if ad_company in cid:
                        return True
                elif ad_company == cid:
                    return True

        if entry["service_uuid"] is not None:
            uuid = entry["service_uuid"]
            if uuid in (raw.service_uuids or []):
                return True
            if raw.service_data and uuid in raw.service_data:
                return True

        if entry["local_name_pattern"] is not None:
            if raw.local_name is not None and re.search(entry["local_name_pattern"], raw.local_name):
                return True

        return False

    def get_all(self):
        return [ParserInfo(
            name=e["name"], description=e["description"],
            version=e["version"], core=e["core"], instance=e["instance"],
            enabled=e["enabled"],
        ) for e in self._parsers]

    def get_by_name(self, name):
        for e in self._parsers:
            if e["name"] == name:
                return ParserInfo(
                    name=e["name"], description=e["description"],
                    version=e["version"], core=e["core"], instance=e["instance"],
                    enabled=e["enabled"],
                )
        return None

    def load_core_parsers(self):
        pass

    def load_plugins(self):
        pass


def register_parser(*, name, company_id=None, service_uuid=None,
                    local_name_pattern=None, description, version, core,
                    registry=None):
    def decorator(cls):
        reg = registry or _default_registry
        instance = cls()
        reg.register(
            name=name, company_id=company_id, service_uuid=service_uuid,
            local_name_pattern=local_name_pattern, description=description,
            version=version, core=core, instance=instance,
        )
        return cls
    return decorator


_default_registry = ParserRegistry()
