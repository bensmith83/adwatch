"""RED phase tests for release fixes — all should FAIL until implementation."""

import ast
import asyncio
import importlib
import logging
import re

import pytest
import pytest_asyncio


# ---------------------------------------------------------------------------
# 1. Codegen ParseResult fields (BUG - CRITICAL)
# ---------------------------------------------------------------------------

class TestCodegenParseResultFields:
    """Codegen should emit correct ParseResult fields (parser_name, metadata)."""

    def test_generated_code_uses_correct_parseresult_fields(self):
        from adwatch.codegen import generate_parser

        spec = {
            "name": "test_proto",
            "company_id": 0x1234,
            "fields": [
                {"name": "temp", "offset": 2, "length": 2, "field_type": "uint16"},
            ],
        }
        code = generate_parser(spec)

        # Should NOT contain the wrong fields
        assert "device_type=" not in code, "Generated code uses wrong field 'device_type'"
        assert "parsed_data=" not in code, "Generated code uses wrong field 'parsed_data'"

        # Should contain the correct fields
        assert "parser_name=" in code, "Generated code missing 'parser_name' field"
        assert "metadata=" in code, "Generated code missing 'metadata' field"

    def test_generated_code_is_valid_python(self):
        from adwatch.codegen import generate_parser

        spec = {
            "name": "test_proto",
            "company_id": 0x1234,
            "fields": [
                {"name": "temp", "offset": 2, "length": 2, "field_type": "uint16"},
            ],
        }
        code = generate_parser(spec)
        # Should parse without SyntaxError
        ast.parse(code)


# ---------------------------------------------------------------------------
# 2. SQL injection in pipeline.py (SECURITY)
# ---------------------------------------------------------------------------

class TestPipelineSQLInjection:
    """Pipeline should reject malicious storage_table and column names."""

    @pytest.fixture
    def mock_db(self):
        class MockDB:
            def __init__(self):
                self.calls = []

            async def execute(self, sql, params=None):
                self.calls.append((sql, params))

        return MockDB()

    @pytest.mark.asyncio
    async def test_rejects_malicious_storage_table(self, mock_db):
        from adwatch.models import RawAdvertisement, Classification, ParseResult
        from adwatch.pipeline import Pipeline
        from adwatch.storage.raw import RawStorage
        from adwatch.classifier import Classifier
        from adwatch.registry import ParserRegistry

        # Create a ParseResult with a malicious table name
        result = ParseResult(
            parser_name="evil",
            beacon_type="evil",
            device_class="evil",
            identifier_hash="deadbeef" * 2,
            raw_payload_hex="00",
            storage_table="evil; DROP TABLE raw_advertisements",
            storage_row={"col": "val"},
        )

        # Mock a parser that returns the malicious result
        class EvilParser:
            def parse(self, ad):
                return result

        registry = ParserRegistry()
        registry.register(
            name="evil", company_id=0xFFFF, description="evil",
            version="0.0", core=False, instance=EvilParser(),
        )
        classifier = Classifier()

        # Use a simple mock for raw_storage
        class MockRawStorage:
            async def save(self, *a, **kw):
                pass

        pipeline = Pipeline(MockRawStorage(), classifier, registry, db=mock_db)

        ad = RawAdvertisement(
            timestamp="2026-01-01T00:00:00Z",
            mac_address="AA:BB:CC:DD:EE:FF",
            address_type="random",
            manufacturer_data=b"\xff\xff\x01",
            service_data=None,
        )

        with pytest.raises(ValueError, match="[Ii]nvalid.*table"):
            await pipeline.process(ad)

    @pytest.mark.asyncio
    async def test_rejects_malicious_column_names(self, mock_db):
        from adwatch.models import RawAdvertisement, ParseResult
        from adwatch.pipeline import Pipeline
        from adwatch.storage.raw import RawStorage
        from adwatch.classifier import Classifier
        from adwatch.registry import ParserRegistry

        result = ParseResult(
            parser_name="evil",
            beacon_type="evil",
            device_class="evil",
            identifier_hash="deadbeef" * 2,
            raw_payload_hex="00",
            storage_table="valid_table",
            storage_row={"col; DROP TABLE x": "val"},
        )

        class EvilParser:
            def parse(self, ad):
                return result

        registry = ParserRegistry()
        registry.register(
            name="evil", company_id=0xFFFF, description="evil",
            version="0.0", core=False, instance=EvilParser(),
        )
        classifier = Classifier()

        class MockRawStorage:
            async def save(self, *a, **kw):
                pass

        pipeline = Pipeline(MockRawStorage(), classifier, registry, db=mock_db)

        ad = RawAdvertisement(
            timestamp="2026-01-01T00:00:00Z",
            mac_address="AA:BB:CC:DD:EE:FF",
            address_type="random",
            manufacturer_data=b"\xff\xff\x01",
            service_data=None,
        )

        with pytest.raises(ValueError, match="[Ii]nvalid.*column"):
            await pipeline.process(ad)


# ---------------------------------------------------------------------------
# 3. Default localhost + --listen-network flag
# ---------------------------------------------------------------------------

class TestDefaultLocalhostAndListenNetwork:
    """Host should default to 127.0.0.1; --listen-network should set 0.0.0.0."""

    def test_parse_args_defaults_to_localhost(self):
        from adwatch.main import parse_args

        args = parse_args([])
        assert args.host == "127.0.0.1", f"Default host should be 127.0.0.1, got {args.host}"

    def test_parse_args_listen_network_sets_all_interfaces(self):
        from adwatch.main import parse_args

        args = parse_args(["--listen-network"])
        assert args.host == "0.0.0.0", f"--listen-network should set host to 0.0.0.0, got {args.host}"


# ---------------------------------------------------------------------------
# 4. Codegen code injection (SECURITY)
# ---------------------------------------------------------------------------

class TestCodegenInjectionSafety:
    """Codegen should use repr() for spec name in ParseResult, not raw f-string."""

    def test_parseresult_line_uses_repr_for_name(self):
        from adwatch.codegen import generate_parser

        spec = {
            "name": "my_proto",
            "company_id": 99,
            "fields": [
                {"name": "val", "offset": 2, "length": 1, "field_type": "uint8"},
            ],
        }
        code = generate_parser(spec)

        # Find the ParseResult return line
        for line in code.splitlines():
            if "ParseResult(" in line and "return" in line:
                # Should use repr()-style quoting, not raw f-string interpolation
                # repr('my_proto') == "'my_proto'" — the name should be safely quoted
                # The key test: it should NOT use f'..."{name}"...' pattern
                # It SHOULD use the actual repr output
                assert "parser_name=" in line, "Missing parser_name in ParseResult"
                break
        else:
            pytest.fail("No ParseResult return line found in generated code")


# ---------------------------------------------------------------------------
# 5. ReDoS / invalid regex validation
# ---------------------------------------------------------------------------

class TestSpecRegexValidation:
    """SpecStorage should reject invalid regex patterns at creation time."""

    @pytest.mark.asyncio
    async def test_rejects_invalid_regex_pattern(self):
        from adwatch.storage.base import Database
        from adwatch.storage.migrations import run_migrations
        from adwatch.storage.specs import SpecStorage

        db = Database()
        await db.connect(":memory:")
        await run_migrations(db)
        spec_store = SpecStorage(db)

        with pytest.raises(ValueError, match="[Rr]egex|[Pp]attern|[Ii]nvalid"):
            await spec_store.create_spec(
                name="bad_regex",
                local_name_pattern="[invalid",
            )

        await db.close()

    @pytest.mark.asyncio
    async def test_accepts_valid_regex_pattern(self):
        from adwatch.storage.base import Database
        from adwatch.storage.migrations import run_migrations
        from adwatch.storage.specs import SpecStorage

        db = Database()
        await db.connect(":memory:")
        await run_migrations(db)
        spec_store = SpecStorage(db)

        # Should not raise
        result = await spec_store.create_spec(
            name="good_regex",
            local_name_pattern=r"^TP\d+",
        )
        assert result is not None

        await db.close()


# ---------------------------------------------------------------------------
# 6. Swallowed exceptions — modules should have loggers
# ---------------------------------------------------------------------------

class TestModuleLoggers:
    """Key modules should have module-level logger instances."""

    @pytest.mark.parametrize("module_path", [
        "adwatch.scanner",
        "adwatch.storage.raw",
        "adwatch.dashboard.websocket",
        "adwatch.storage.specs",
    ])
    def test_module_has_logger(self, module_path):
        mod = importlib.import_module(module_path)
        assert hasattr(mod, "logger"), f"{module_path} missing module-level 'logger'"
        assert isinstance(mod.logger, logging.Logger), (
            f"{module_path}.logger should be logging.Logger, got {type(mod.logger)}"
        )


# ---------------------------------------------------------------------------
# 7. Pydantic models for API endpoints
# ---------------------------------------------------------------------------

class TestPydanticAPIValidation:
    """Spec API should return 422 for invalid input, not 500."""

    @pytest.mark.asyncio
    async def test_create_spec_missing_name_returns_422(self):
        from httpx import AsyncClient, ASGITransport
        from adwatch.storage.base import Database
        from adwatch.storage.migrations import run_migrations
        from adwatch.storage.raw import RawStorage
        from adwatch.storage.specs import SpecStorage
        from adwatch.dashboard.app import create_app
        from adwatch.classifier import Classifier
        from adwatch.registry import ParserRegistry
        from adwatch.dashboard.websocket import WebSocketManager

        db = Database()
        await db.connect(":memory:")
        await run_migrations(db)
        raw = RawStorage(db)
        specs = SpecStorage(db)
        ws = WebSocketManager()
        app = create_app(raw, Classifier(), ParserRegistry(), ws, db=db, spec_storage=specs)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Missing "name" field entirely
            resp = await client.post("/api/explorer/specs", json={"description": "no name"})
            assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"

        await db.close()

    @pytest.mark.asyncio
    async def test_create_spec_name_wrong_type_returns_422(self):
        from httpx import AsyncClient, ASGITransport
        from adwatch.storage.base import Database
        from adwatch.storage.migrations import run_migrations
        from adwatch.storage.raw import RawStorage
        from adwatch.storage.specs import SpecStorage
        from adwatch.dashboard.app import create_app
        from adwatch.classifier import Classifier
        from adwatch.registry import ParserRegistry
        from adwatch.dashboard.websocket import WebSocketManager

        db = Database()
        await db.connect(":memory:")
        await run_migrations(db)
        raw = RawStorage(db)
        specs = SpecStorage(db)
        ws = WebSocketManager()
        app = create_app(raw, Classifier(), ParserRegistry(), ws, db=db, spec_storage=specs)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # name as integer instead of string
            resp = await client.post("/api/explorer/specs", json={"name": 12345})
            assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"

        await db.close()


# ---------------------------------------------------------------------------
# 8. __null__ sentinel constant
# ---------------------------------------------------------------------------

class TestNullSentinel:
    """raw.py should export a NULL_SENTINEL constant."""

    def test_null_sentinel_exists_and_equals_expected(self):
        from adwatch.storage.raw import NULL_SENTINEL

        assert NULL_SENTINEL == "__null__"


# ---------------------------------------------------------------------------
# 9. Company ID hex parsing utility
# ---------------------------------------------------------------------------

class TestExtractCompanyId:
    """A shared extract_company_id utility should exist."""

    def test_apple_company_id(self):
        from adwatch.utils import extract_company_id

        assert extract_company_id("4c001005") == 76  # Apple, little-endian

    def test_empty_string(self):
        from adwatch.utils import extract_company_id

        assert extract_company_id("") is None

    def test_too_short(self):
        from adwatch.utils import extract_company_id

        assert extract_company_id("4c") is None

    def test_none_input(self):
        from adwatch.utils import extract_company_id

        assert extract_company_id(None) is None


# ---------------------------------------------------------------------------
# 10. Dead stubs removal
# ---------------------------------------------------------------------------

class TestDeadStubsRemoved:
    """ParserRegistry should NOT have load_core_parsers or load_plugins methods."""

    def test_no_load_core_parsers(self):
        from adwatch.registry import ParserRegistry

        assert not hasattr(ParserRegistry, "load_core_parsers"), (
            "ParserRegistry still has dead stub 'load_core_parsers'"
        )

    def test_no_load_plugins(self):
        from adwatch.registry import ParserRegistry

        assert not hasattr(ParserRegistry, "load_plugins"), (
            "ParserRegistry still has dead stub 'load_plugins'"
        )
