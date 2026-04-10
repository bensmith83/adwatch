"""Plugin registry and @register_parser decorator for adwatch."""

import re
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
                 local_name_pattern=None, mac_prefix=None, description,
                 version, core, instance):
        compiled_pattern = re.compile(local_name_pattern) if local_name_pattern else None
        # Normalize mac_prefix to a tuple of uppercase strings
        if mac_prefix is not None:
            if isinstance(mac_prefix, str):
                mac_prefix = (mac_prefix.upper(),)
            else:
                mac_prefix = tuple(p.upper() for p in mac_prefix)
        self._parsers.append({
            "name": name,
            "company_id": company_id,
            "service_uuid": service_uuid,
            "local_name_pattern": local_name_pattern,
            "mac_prefix": mac_prefix,
            "_compiled_pattern": compiled_pattern,
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
            suuid = entry["service_uuid"]
            if isinstance(suuid, (list, tuple)):
                for u in suuid:
                    if u in (raw.service_uuids or []):
                        return True
                    if raw.service_data and u in raw.service_data:
                        return True
            else:
                if suuid in (raw.service_uuids or []):
                    return True
                if raw.service_data and suuid in raw.service_data:
                    return True

        if entry["mac_prefix"] is not None:
            mac_upper = raw.mac_address.upper()
            for prefix in entry["mac_prefix"]:
                if mac_upper.startswith(prefix):
                    return True

        if entry["_compiled_pattern"] is not None:
            if raw.local_name is not None and entry["_compiled_pattern"].search(raw.local_name):
                return True

        return False

    def get_all(self):
        return [ParserInfo(
            name=e["name"], description=e["description"],
            version=e["version"], core=e["core"], instance=e["instance"],
            enabled=e["enabled"],
        ) for e in self._parsers]

    def get_entries(self):
        """Return raw parser entries (for copying between registries)."""
        return list(self._parsers)

    def get_by_name(self, name):
        for e in self._parsers:
            if e["name"] == name:
                return ParserInfo(
                    name=e["name"], description=e["description"],
                    version=e["version"], core=e["core"], instance=e["instance"],
                    enabled=e["enabled"],
                )
        return None


def register_parser(*, name, company_id=None, service_uuid=None,
                    local_name_pattern=None, mac_prefix=None, description,
                    version, core, registry=None):
    def decorator(cls):
        reg = registry or _default_registry
        instance = cls()
        reg.register(
            name=name, company_id=company_id, service_uuid=service_uuid,
            local_name_pattern=local_name_pattern, mac_prefix=mac_prefix,
            description=description, version=version, core=core,
            instance=instance,
        )
        return cls
    return decorator


_default_registry = ParserRegistry()
