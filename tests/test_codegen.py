"""Tests for Protocol Specs code generation."""

import ast

import pytest

from adwatch.codegen import generate_parser


def _make_spec(
    name="my_protocol",
    description=None,
    company_id=None,
    service_uuid=None,
    local_name_pattern=None,
    data_source="mfr",
    fields=None,
):
    return {
        "id": 1,
        "name": name,
        "description": description,
        "company_id": company_id,
        "service_uuid": service_uuid,
        "local_name_pattern": local_name_pattern,
        "data_source": data_source,
        "fields": fields or [],
    }


# ===================================================================
# Valid Python output
# ===================================================================

class TestGenerateParserSyntax:
    def test_output_is_valid_python(self):
        spec = _make_spec(company_id=76, fields=[
            {"name": "temperature", "offset": 0, "length": 2, "field_type": "uint16", "endian": "LE", "description": None, "sort_order": 0},
        ])
        code = generate_parser(spec)
        ast.parse(code)  # Should not raise

    def test_output_is_string(self):
        spec = _make_spec(company_id=76)
        code = generate_parser(spec)
        assert isinstance(code, str)


# ===================================================================
# @register_parser decorator
# ===================================================================

class TestRegisterParserDecorator:
    def test_contains_register_parser(self):
        spec = _make_spec(company_id=76)
        code = generate_parser(spec)
        assert "@register_parser" in code

    def test_company_id_in_decorator(self):
        spec = _make_spec(company_id=76)
        code = generate_parser(spec)
        assert "company_id=76" in code

    def test_service_uuid_in_decorator(self):
        spec = _make_spec(service_uuid="0000fe2c-0000-1000-8000-00805f9b34fb")
        code = generate_parser(spec)
        assert "service_uuid=" in code
        assert "0000fe2c-0000-1000-8000-00805f9b34fb" in code

    def test_local_name_pattern_in_decorator(self):
        spec = _make_spec(local_name_pattern=r"^TP\d+")
        code = generate_parser(spec)
        assert "local_name_pattern=" in code
        assert r"^TP\d+" in code

    def test_all_match_criteria(self):
        spec = _make_spec(company_id=76, service_uuid="abcd", local_name_pattern=r"^Test")
        code = generate_parser(spec)
        assert "company_id=76" in code
        assert "service_uuid=" in code
        assert "local_name_pattern=" in code


# ===================================================================
# Class name generation
# ===================================================================

class TestClassName:
    def test_snake_case_to_pascal_case(self):
        spec = _make_spec(name="my_custom_protocol", company_id=76)
        code = generate_parser(spec)
        assert "MyCustomProtocol" in code

    def test_single_word(self):
        spec = _make_spec(name="simple", company_id=76)
        code = generate_parser(spec)
        assert "Simple" in code

    def test_already_pascal(self):
        spec = _make_spec(name="MyProto", company_id=76)
        code = generate_parser(spec)
        assert "MyProto" in code or "Myproto" in code


# ===================================================================
# Field extraction
# ===================================================================

class TestFieldExtraction:
    def test_uint8_field(self):
        spec = _make_spec(company_id=76, fields=[
            {"name": "flags", "offset": 0, "length": 1, "field_type": "uint8", "endian": "LE", "description": None, "sort_order": 0},
        ])
        code = generate_parser(spec)
        ast.parse(code)
        assert "flags" in code

    def test_uint16_le_field(self):
        spec = _make_spec(company_id=76, fields=[
            {"name": "temperature", "offset": 0, "length": 2, "field_type": "uint16", "endian": "LE", "description": None, "sort_order": 0},
        ])
        code = generate_parser(spec)
        ast.parse(code)
        assert "temperature" in code

    def test_uint16_be_field(self):
        spec = _make_spec(company_id=76, fields=[
            {"name": "value", "offset": 0, "length": 2, "field_type": "uint16", "endian": "BE", "description": None, "sort_order": 0},
        ])
        code = generate_parser(spec)
        ast.parse(code)
        # BE should use > format
        assert ">" in code or "big" in code

    def test_int16_field(self):
        spec = _make_spec(company_id=76, fields=[
            {"name": "signed_val", "offset": 0, "length": 2, "field_type": "int16", "endian": "LE", "description": None, "sort_order": 0},
        ])
        code = generate_parser(spec)
        ast.parse(code)
        assert "signed_val" in code

    def test_float32_field(self):
        spec = _make_spec(company_id=76, fields=[
            {"name": "pressure", "offset": 0, "length": 4, "field_type": "float32", "endian": "LE", "description": None, "sort_order": 0},
        ])
        code = generate_parser(spec)
        ast.parse(code)
        assert "pressure" in code

    def test_utf8_field(self):
        spec = _make_spec(company_id=76, fields=[
            {"name": "device_name", "offset": 0, "length": 10, "field_type": "utf8", "endian": "LE", "description": None, "sort_order": 0},
        ])
        code = generate_parser(spec)
        ast.parse(code)
        assert "device_name" in code

    def test_multiple_fields(self):
        spec = _make_spec(company_id=76, fields=[
            {"name": "flags", "offset": 0, "length": 1, "field_type": "uint8", "endian": "LE", "description": None, "sort_order": 0},
            {"name": "temperature", "offset": 1, "length": 2, "field_type": "uint16", "endian": "LE", "description": None, "sort_order": 1},
            {"name": "humidity", "offset": 3, "length": 1, "field_type": "uint8", "endian": "LE", "description": None, "sort_order": 2},
        ])
        code = generate_parser(spec)
        ast.parse(code)
        assert "flags" in code
        assert "temperature" in code
        assert "humidity" in code


# ===================================================================
# Endianness / struct format
# ===================================================================

class TestEndianness:
    def test_le_uses_little_endian_format(self):
        spec = _make_spec(company_id=76, fields=[
            {"name": "val", "offset": 0, "length": 2, "field_type": "uint16", "endian": "LE", "description": None, "sort_order": 0},
        ])
        code = generate_parser(spec)
        # LE should use < format
        assert "<" in code or "little" in code

    def test_be_uses_big_endian_format(self):
        spec = _make_spec(company_id=76, fields=[
            {"name": "val", "offset": 0, "length": 2, "field_type": "uint16", "endian": "BE", "description": None, "sort_order": 0},
        ])
        code = generate_parser(spec)
        assert ">" in code or "big" in code


# ===================================================================
# Minimum data length check
# ===================================================================

class TestMinLengthCheck:
    def test_contains_length_check(self):
        spec = _make_spec(company_id=76, fields=[
            {"name": "flags", "offset": 0, "length": 1, "field_type": "uint8", "endian": "LE", "description": None, "sort_order": 0},
            {"name": "value", "offset": 5, "length": 4, "field_type": "float32", "endian": "LE", "description": None, "sort_order": 1},
        ])
        code = generate_parser(spec)
        # max(offset+length) = 5+4 = 9
        assert "9" in code or "len(" in code

    def test_length_based_on_max_offset_plus_length(self):
        spec = _make_spec(company_id=76, fields=[
            {"name": "a", "offset": 0, "length": 2, "field_type": "uint16", "endian": "LE", "description": None, "sort_order": 0},
            {"name": "b", "offset": 10, "length": 4, "field_type": "float32", "endian": "LE", "description": None, "sort_order": 1},
        ])
        code = generate_parser(spec)
        # min length should be 14 (10+4)
        assert "14" in code


# ===================================================================
# Data source selection
# ===================================================================

class TestDataSource:
    def test_mfr_data_source(self):
        spec = _make_spec(company_id=76, data_source="mfr", fields=[
            {"name": "val", "offset": 0, "length": 1, "field_type": "uint8", "endian": "LE", "description": None, "sort_order": 0},
        ])
        code = generate_parser(spec)
        assert "manufacturer_data" in code

    def test_service_data_source(self):
        spec = _make_spec(service_uuid="abcd", data_source="service", fields=[
            {"name": "val", "offset": 0, "length": 1, "field_type": "uint8", "endian": "LE", "description": None, "sort_order": 0},
        ])
        code = generate_parser(spec)
        assert "service_data" in code


# ===================================================================
# Edge cases
# ===================================================================

class TestEdgeCases:
    def test_no_fields_still_valid_python(self):
        spec = _make_spec(company_id=76, fields=[])
        code = generate_parser(spec)
        ast.parse(code)

    def test_no_match_criteria_still_valid_python(self):
        spec = _make_spec(fields=[
            {"name": "val", "offset": 0, "length": 1, "field_type": "uint8", "endian": "LE", "description": None, "sort_order": 0},
        ])
        code = generate_parser(spec)
        ast.parse(code)

    def test_all_match_criteria_valid_python(self):
        spec = _make_spec(
            company_id=76,
            service_uuid="abcd",
            local_name_pattern=r"^Test\d+",
            fields=[
                {"name": "val", "offset": 0, "length": 1, "field_type": "uint8", "endian": "LE", "description": None, "sort_order": 0},
            ],
        )
        code = generate_parser(spec)
        ast.parse(code)

    def test_returns_parse_result(self):
        """Generated code should reference ParseResult."""
        spec = _make_spec(company_id=76, fields=[
            {"name": "val", "offset": 0, "length": 1, "field_type": "uint8", "endian": "LE", "description": None, "sort_order": 0},
        ])
        code = generate_parser(spec)
        assert "ParseResult" in code

    def test_empty_name_to_pascal(self):
        """_to_pascal('') should not crash."""
        from adwatch.codegen import _to_pascal
        result = _to_pascal("")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_description_with_quotes_valid_python(self):
        """Spec with quotes in description doesn't break generated code."""
        spec = _make_spec(
            name="tricky_proto",
            company_id=76,
            description='Has "double" and \'single\' quotes',
            fields=[
                {"name": "val", "offset": 0, "length": 1, "field_type": "uint8", "endian": "LE", "description": None, "sort_order": 0},
            ],
        )
        code = generate_parser(spec)
        ast.parse(code)

    def test_pattern_with_quotes_valid_python(self):
        """Spec with quotes in local_name_pattern doesn't break generated code."""
        spec = _make_spec(
            name="quote_proto",
            local_name_pattern=r'^Test"Device',
            fields=[
                {"name": "val", "offset": 0, "length": 1, "field_type": "uint8", "endian": "LE", "description": None, "sort_order": 0},
            ],
        )
        code = generate_parser(spec)
        ast.parse(code)
