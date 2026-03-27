"""Generate @register_parser plugin code from a protocol spec."""


TYPE_MAP = {
    "uint8": "B",
    "uint16": "H",
    "uint32": "I",
    "int8": "b",
    "int16": "h",
    "int32": "i",
    "float32": "f",
}


def _to_pascal(name: str) -> str:
    if not name:
        return "UnnamedParser"
    return "".join(word.capitalize() for word in name.split("_")) if "_" in name else name[0].upper() + name[1:]


def generate_parser(spec: dict) -> str:
    name = spec["name"]
    class_name = _to_pascal(name)
    fields = spec.get("fields") or []
    data_source = spec.get("data_source", "mfr")

    # Decorator args
    dec_args = []
    if spec.get("company_id") is not None:
        dec_args.append(f"company_id={spec['company_id']}")
    if spec.get("service_uuid") is not None:
        dec_args.append(f"service_uuid={repr(spec['service_uuid'])}")
    if spec.get("local_name_pattern") is not None:
        pat = spec["local_name_pattern"]
        # Use raw string to preserve regex backslashes; pick quote delimiter to avoid escaping
        if '"' not in pat:
            dec_args.append(f'local_name_pattern=r"{pat}"')
        elif "'" not in pat:
            dec_args.append(f"local_name_pattern=r'{pat}'")
        else:
            # Both quote types present — fall back to repr
            dec_args.append(f"local_name_pattern={repr(pat)}")
    # Always include required decorator arguments
    dec_args.append(f"name={repr(name)}")
    dec_args.append(f'description="Auto-generated parser for {name}"')
    dec_args.append(f'version="0.1.0"')
    dec_args.append(f"core=False")
    dec_str = ", ".join(dec_args)

    # Min data length
    if fields:
        min_len = max(f["offset"] + f["length"] for f in fields)
    else:
        min_len = 0

    # Data variable
    if data_source == "service":
        data_var = "service_data"
        data_access = "ad.service_data"
    else:
        data_var = "manufacturer_data"
        data_access = "ad.manufacturer_data"

    lines = [
        '"""Auto-generated parser for %s.' % name,
        "",
        "To use this parser, save this file as:",
        "    src/adwatch/plugins/%s.py" % name,
        "",
        "It will be auto-discovered on next restart.",
        '"""',
        "",
        "import struct",
        "",
        "from adwatch.models import ParseResult",
        "from adwatch.registry import register_parser",
        "",
        "",
        f"@register_parser({dec_str})",
        f"class {class_name}:",
        f'    """Parser for {name}."""',
        "",
        "    def parse(self, ad):",
        f"        data = {data_access}",
        "        if not data:",
        "            return None",
    ]

    if min_len > 0:
        lines.append(f"        if len(data) < {min_len}:")
        lines.append("            return None")

    lines.append("        parsed = {}")

    for field in fields:
        fname = field["name"]
        offset = field["offset"]
        length = field["length"]
        ftype = field["field_type"]
        endian = field.get("endian", "LE")
        endian_char = "<" if endian == "LE" else ">"
        fname_repr = repr(fname)

        if ftype == "utf8":
            lines.append(f'        parsed[{fname_repr}] = data[{offset}:{offset + length}].decode("utf-8", errors="replace")')
        elif ftype == "mac_addr":
            lines.append(f'        parsed[{fname_repr}] = ":".join(f"{{b:02x}}" for b in data[{offset}:{offset + length}])')
        elif ftype == "raw_hex":
            lines.append(f'        parsed[{fname_repr}] = data[{offset}:{offset + length}].hex()')
        elif ftype in TYPE_MAP:
            fmt = f"{endian_char}{TYPE_MAP[ftype]}"
            lines.append(f'        parsed[{fname_repr}] = struct.unpack("{fmt}", data[{offset}:{offset + length}])[0]')
        else:
            lines.append(f'        parsed[{fname_repr}] = data[{offset}:{offset + length}].hex()')

    lines.append("")
    lines.append(f'        return ParseResult(parser_name={repr(name)}, beacon_type={repr(name)}, device_class="unknown", identifier_hash="", raw_payload_hex=data.hex(), metadata=parsed)')
    lines.append("")

    return "\n".join(lines)
