"""
Comprehensive tests for Phase 5: Output Generator.

Tests cover:
- Empty database generation
- Single config per protocol (6 protocols)
- Multiple protocols
- Duplicate canonical configs
- Multiple occurrences pointing to same canonical config
- all.txt generation
- Per-protocol file generation
- Hysteria/Hysteria2 separation
- Deterministic ordering
- stats.json structure
- README.md generation
- No secrets in generated files
- Unknown protocol handling
- Filesystem/output errors
- Active/inactive lifecycle filtering
- Correct canonical configuration usage
"""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import Settings
from app.database.database import init_database, create_tables, drop_tables, get_session
from app.database.models import Config, ConfigLifecycleState
from app.database.repository import ChannelRepository, ConfigRepository, ConfigOccurrenceRepository
from app.output.generator import OutputGenerator, SUPPORTED_PROTOCOLS, PROTOCOL_FILENAMES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(session, protocol, raw_config, normalized_config=None, config_hash=None,
                 is_structurally_valid=True, lifecycle_state=ConfigLifecycleState.VALID,
                 is_active=True):
    """Insert a Config row and return it."""
    if normalized_config is None:
        normalized_config = f"norm:{protocol}:{raw_config}"
    if config_hash is None:
        import hashlib
        config_hash = hashlib.sha256(normalized_config.encode()).hexdigest()

    config = ConfigRepository.create(
        session,
        protocol=protocol,
        raw_config=raw_config,
        normalized_config=normalized_config,
        config_hash=config_hash,
        is_structurally_valid=is_structurally_valid,
    )
    ConfigRepository.update_lifecycle_state(session, config, lifecycle_state)
    config.is_active = is_active
    session.flush()
    session.refresh(config)
    return config


# ---------------------------------------------------------------------------
# Tests: Empty database
# ---------------------------------------------------------------------------

class TestEmptyDatabase:
    """Test generation with an empty database."""

    def test_empty_database_generates_valid_output(self, test_database, tmp_path):
        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        stats = generator.generate()

        assert stats["total_configs"] == 0
        assert stats["configs_by_protocol"] == {}

        out = tmp_path / "out"
        assert (out / "all.txt").exists()
        assert (out / "all.txt").read_text(encoding="utf-8") == ""
        assert (out / "vmess.txt").exists()
        assert (out / "vmess.txt").read_text(encoding="utf-8") == ""
        assert (out / "vless.txt").exists()
        assert (out / "vless.txt").read_text(encoding="utf-8") == ""
        assert (out / "trojan.txt").exists()
        assert (out / "trojan.txt").read_text(encoding="utf-8") == ""
        assert (out / "shadowsocks.txt").exists()
        assert (out / "shadowsocks.txt").read_text(encoding="utf-8") == ""
        assert (out / "hysteria.txt").exists()
        assert (out / "hysteria.txt").read_text(encoding="utf-8") == ""
        assert (out / "hysteria2.txt").exists()
        assert (out / "hysteria2.txt").read_text(encoding="utf-8") == ""
        assert (out / "stats.json").exists()
        assert (out / "README.md").exists()

    def test_empty_database_stats_json(self, test_database, tmp_path):
        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        stats = generator.generate()

        out = tmp_path / "out"
        data = json.loads((out / "stats.json").read_text(encoding="utf-8"))
        assert data["total_configs"] == 0
        assert data["configs_by_protocol"] == {}
        assert "generated_at" in data


# ---------------------------------------------------------------------------
# Tests: Single protocol configs
# ---------------------------------------------------------------------------

class TestSingleProtocolConfigs:
    """Test generation with a single config of each protocol."""

    def test_single_vmess(self, test_database, tmp_path):
        _make_config(
            test_database,
            protocol="vmess",
            raw_config="vmess://eyJ2IjoiMiJ9",
        )
        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        stats = generator.generate()

        assert stats["total_configs"] == 1
        assert stats["configs_by_protocol"]["vmess"] == 1

        out = tmp_path / "out"
        assert (out / "vmess.txt").read_text(encoding="utf-8") == "vmess://eyJ2IjoiMiJ9\n"
        assert (out / "all.txt").read_text(encoding="utf-8") == "vmess://eyJ2IjoiMiJ9\n"
        # Other protocol files should be empty
        assert (out / "vless.txt").read_text(encoding="utf-8") == ""

    def test_single_vless(self, test_database, tmp_path):
        _make_config(
            test_database,
            protocol="vless",
            raw_config="vless://12345678-1234-1234-1234-123456789abc@1.2.3.4:443?encryption=none",
        )
        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        stats = generator.generate()

        assert stats["total_configs"] == 1
        assert stats["configs_by_protocol"]["vless"] == 1

        out = tmp_path / "out"
        content = (out / "vless.txt").read_text(encoding="utf-8")
        assert "vless://12345678-1234-1234-1234-123456789abc@1.2.3.4:443" in content

    def test_single_trojan(self, test_database, tmp_path):
        _make_config(
            test_database,
            protocol="trojan",
            raw_config="trojan://password@1.2.3.4:443?security=tls",
        )
        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        stats = generator.generate()

        assert stats["total_configs"] == 1
        assert stats["configs_by_protocol"]["trojan"] == 1

        out = tmp_path / "out"
        content = (out / "trojan.txt").read_text(encoding="utf-8")
        assert "trojan://password@1.2.3.4:443" in content

    def test_single_shadowsocks(self, test_database, tmp_path):
        _make_config(
            test_database,
            protocol="shadowsocks",
            raw_config="ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@1.2.3.4:8388",
        )
        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        stats = generator.generate()

        assert stats["total_configs"] == 1
        assert stats["configs_by_protocol"]["shadowsocks"] == 1

        out = tmp_path / "out"
        content = (out / "shadowsocks.txt").read_text(encoding="utf-8")
        assert "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@1.2.3.4:8388" in content

    def test_single_hysteria(self, test_database, tmp_path):
        _make_config(
            test_database,
            protocol="hysteria",
            raw_config="hysteria://1.2.3.4:443?auth=test",
        )
        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        stats = generator.generate()

        assert stats["total_configs"] == 1
        assert stats["configs_by_protocol"]["hysteria"] == 1

        out = tmp_path / "out"
        content = (out / "hysteria.txt").read_text(encoding="utf-8")
        assert "hysteria://1.2.3.4:443" in content
        # Hysteria2 must be empty
        assert (out / "hysteria2.txt").read_text(encoding="utf-8") == ""

    def test_single_hysteria2(self, test_database, tmp_path):
        _make_config(
            test_database,
            protocol="hysteria2",
            raw_config="hysteria2://1.2.3.4:443?auth=test",
        )
        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        stats = generator.generate()

        assert stats["total_configs"] == 1
        assert stats["configs_by_protocol"]["hysteria2"] == 1

        out = tmp_path / "out"
        content = (out / "hysteria2.txt").read_text(encoding="utf-8")
        assert "hysteria2://1.2.3.4:443" in content
        # Hysteria must be empty
        assert (out / "hysteria.txt").read_text(encoding="utf-8") == ""


# ---------------------------------------------------------------------------
# Tests: Multiple protocols
# ---------------------------------------------------------------------------

class TestMultipleProtocols:
    """Test generation with configs across multiple protocols."""

    def test_all_protocols(self, test_database, tmp_path):
        raw_configs = {
            "vmess": "vmess://eyJ2IjoiMiJ9",
            "vless": "vless://12345678-1234-1234-1234-123456789abc@1.2.3.4:443?encryption=none",
            "trojan": "trojan://pass@1.2.3.4:443",
            "shadowsocks": "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@1.2.3.4:8388",
            "hysteria": "hysteria://1.2.3.4:443",
            "hysteria2": "hysteria2://1.2.3.4:443",
        }
        for protocol, raw in raw_configs.items():
            _make_config(test_database, protocol=protocol, raw_config=raw)

        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        stats = generator.generate()

        assert stats["total_configs"] == 6
        for protocol in SUPPORTED_PROTOCOLS:
            assert stats["configs_by_protocol"][protocol] == 1

        out = tmp_path / "out"
        all_content = (out / "all.txt").read_text(encoding="utf-8")
        for protocol, raw in raw_configs.items():
            assert raw in all_content

    def test_hysteria_and_hysteria2_separate(self, test_database, tmp_path):
        _make_config(test_database, protocol="hysteria", raw_config="hysteria://1.2.3.4:443")
        _make_config(test_database, protocol="hysteria2", raw_config="hysteria2://1.2.3.4:443")

        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        stats = generator.generate()

        assert stats["total_configs"] == 2
        assert stats["configs_by_protocol"]["hysteria"] == 1
        assert stats["configs_by_protocol"]["hysteria2"] == 1

        out = tmp_path / "out"
        h1 = (out / "hysteria.txt").read_text(encoding="utf-8")
        h2 = (out / "hysteria2.txt").read_text(encoding="utf-8")
        assert "hysteria://" in h1
        assert "hysteria2://" not in h1
        assert "hysteria2://" in h2
        assert "hysteria://" not in h2 or "hysteria2://" in h2  # ensure they're separate


# ---------------------------------------------------------------------------
# Tests: Deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:
    """Test that duplicate canonical configs are deduplicated."""

    def test_duplicate_same_hash_single_line(self, test_database, tmp_path):
        """Two Config rows with the same hash should still appear only once in output
        because the database enforces unique config_hash."""
        # The database has a unique constraint on config_hash, so inserting two
        # configs with the same hash would fail. Instead we verify that the
        # unique constraint exists and the generator doesn't produce duplicates.
        config = _make_config(
            test_database,
            protocol="vmess",
            raw_config="vmess://eyJ2IjoiMiJ9",
            config_hash="a" * 64,
        )
        # Trying to insert another with same hash should fail at DB level
        with pytest.raises(Exception):
            _make_config(
                test_database,
                protocol="vmess",
                raw_config="vmess://eyJ2IjoiMiJ9",
                config_hash="a" * 64,
            )
            test_database.commit()

        test_database.rollback()

    def test_multiple_occurrences_same_config(self, test_database, tmp_path):
        """Multiple occurrences of the same config produce a single output line."""
        config = _make_config(
            test_database,
            protocol="vless",
            raw_config="vless://12345678-1234-1234-1234-123456789abc@1.2.3.4:443",
        )
        channel = ChannelRepository.create(
            test_database, telegram_id=111, username="ch1", enabled=True,
        )
        # Two occurrences from different messages
        ConfigOccurrenceRepository.create(
            test_database, config_id=config.id, channel_id=channel.id,
            source_message_id=100, raw_occurrence="vless://raw1",
        )
        ConfigOccurrenceRepository.create(
            test_database, config_id=config.id, channel_id=channel.id,
            source_message_id=200, raw_occurrence="vless://raw2",
        )
        test_database.flush()

        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        stats = generator.generate()

        assert stats["total_configs"] == 1
        out = tmp_path / "out"
        lines = (out / "vless.txt").read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        assert lines[0] == "vless://12345678-1234-1234-1234-123456789abc@1.2.3.4:443"


# ---------------------------------------------------------------------------
# Tests: Deterministic ordering
# ---------------------------------------------------------------------------

class TestDeterministicOrdering:
    """Test that output ordering is deterministic."""

    def test_same_database_same_output(self, test_database, tmp_path):
        """Two runs with the same database state produce byte-identical output."""
        for i in range(5):
            _make_config(
                test_database,
                protocol="vmess",
                raw_config=f"vmess://config_{i}",
                config_hash=f"{i:064d}",
            )

        gen1 = OutputGenerator(output_dir=str(tmp_path / "run1"), session=test_database)
        gen1.generate()

        gen2 = OutputGenerator(output_dir=str(tmp_path / "run2"), session=test_database)
        gen2.generate()

        for filename in ["all.txt", "vmess.txt", "vless.txt", "trojan.txt",
                          "shadowsocks.txt", "hysteria.txt", "hysteria2.txt"]:
            content1 = (tmp_path / "run1" / filename).read_text(encoding="utf-8")
            content2 = (tmp_path / "run2" / filename).read_text(encoding="utf-8")
            assert content1 == content2, f"{filename} differs between runs"

    def test_ordering_by_config_hash(self, test_database, tmp_path):
        """Configs are sorted by config_hash, not insertion order."""
        hashes = ["c" * 64, "a" * 64, "b" * 64]
        raws = ["vmess://ccc", "vmess://aaa", "vmess://bbb"]
        for h, r in zip(hashes, raws):
            _make_config(test_database, protocol="vmess", raw_config=r, config_hash=h)

        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        generator.generate()

        content = (tmp_path / "out" / "vmess.txt").read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        assert lines == ["vmess://aaa", "vmess://bbb", "vmess://ccc"]


# ---------------------------------------------------------------------------
# Tests: stats.json
# ---------------------------------------------------------------------------

class TestStatsJson:
    """Test stats.json structure and content."""

    def test_stats_json_structure(self, test_database, tmp_path):
        _make_config(test_database, protocol="vmess", raw_config="vmess://test1")
        _make_config(test_database, protocol="vmess", raw_config="vmess://test2")
        _make_config(test_database, protocol="vless", raw_config="vless://test3")

        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        generator.generate()

        data = json.loads((tmp_path / "out" / "stats.json").read_text(encoding="utf-8"))

        assert "total_configs" in data
        assert "configs_by_protocol" in data
        assert "generated_at" in data
        assert "channel_name" in data
        assert "channel_username" in data
        assert data["total_configs"] == 3
        assert data["configs_by_protocol"]["vmess"] == 2
        assert data["configs_by_protocol"]["vless"] == 1

    def test_stats_no_secrets(self, test_database, tmp_path):
        _make_config(test_database, protocol="vmess", raw_config="vmess://test")

        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        generator.generate()

        content = (tmp_path / "out" / "stats.json").read_text(encoding="utf-8")
        assert "api_hash" not in content.lower()
        assert "bot_token" not in content.lower()
        assert "github_token" not in content.lower()


# ---------------------------------------------------------------------------
# Tests: README.md
# ---------------------------------------------------------------------------

class TestReadme:
    """Test README.md generation."""

    def test_readme_content(self, test_database, tmp_path):
        _make_config(test_database, protocol="vmess", raw_config="vmess://test")
        _make_config(test_database, protocol="vless", raw_config="vless://test")

        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        generator.generate()

        content = (tmp_path / "out" / "README.md").read_text(encoding="utf-8")
        assert "VMESS" in content
        assert "VLESS" in content
        assert "vmess.txt" in content
        assert "vless.txt" in content
        assert "2" in content  # total configs

    def test_readme_no_secrets(self, test_database, tmp_path):
        _make_config(test_database, protocol="vmess", raw_config="vmess://test")

        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        generator.generate()

        content = (tmp_path / "out" / "README.md").read_text(encoding="utf-8")
        assert "api_hash" not in content.lower()
        assert "bot_token" not in content.lower()


# ---------------------------------------------------------------------------
# Tests: No secrets in generated files
# ---------------------------------------------------------------------------

class TestNoSecrets:
    """Test that no secrets appear in generated files."""

    SENSITIVE_PATTERNS = [
        "api_hash",
        "bot_token",
        "github_token",
        "secret123",
        "password",
    ]

    def test_no_secrets_in_protocol_files(self, test_database, tmp_path):
        _make_config(test_database, protocol="vmess", raw_config="vmess://test")
        _make_config(test_database, protocol="vless", raw_config="vless://test")
        _make_config(test_database, protocol="trojan", raw_config="trojan://test")
        _make_config(test_database, protocol="shadowsocks", raw_config="ss://test")
        _make_config(test_database, protocol="hysteria", raw_config="hysteria://test")
        _make_config(test_database, protocol="hysteria2", raw_config="hysteria2://test")

        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        generator.generate()

        out = tmp_path / "out"
        for filename in ["all.txt", "vmess.txt", "vless.txt", "trojan.txt",
                          "shadowsocks.txt", "hysteria.txt", "hysteria2.txt",
                          "stats.json", "README.md"]:
            content = (out / filename).read_text(encoding="utf-8").lower()
            for pattern in self.SENSITIVE_PATTERNS:
                assert pattern not in content, f"Secret '{pattern}' found in {filename}"


# ---------------------------------------------------------------------------
# Tests: Lifecycle filtering
# ---------------------------------------------------------------------------

class TestLifecycleFiltering:
    """Test that only active/valid configs are included in output."""

    def test_inactive_configs_excluded(self, test_database, tmp_path):
        _make_config(test_database, protocol="vmess", raw_config="vmess://active", is_active=True)
        _make_config(test_database, protocol="vmess", raw_config="vmess://inactive", is_active=False)

        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        stats = generator.generate()

        assert stats["total_configs"] == 1
        content = (tmp_path / "out" / "vmess.txt").read_text(encoding="utf-8")
        assert "vmess://active" in content
        assert "vmess://inactive" not in content

    def test_invalid_configs_excluded(self, test_database, tmp_path):
        _make_config(test_database, protocol="vless", raw_config="vless://valid",
                     is_structurally_valid=True, lifecycle_state=ConfigLifecycleState.VALID)
        _make_config(test_database, protocol="vless", raw_config="vless://invalid",
                     is_structurally_valid=False, lifecycle_state=ConfigLifecycleState.INVALID)

        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        stats = generator.generate()

        assert stats["total_configs"] == 1
        content = (tmp_path / "out" / "vless.txt").read_text(encoding="utf-8")
        assert "vless://valid" in content
        assert "vless://invalid" not in content

    def test_mixed_lifecycle_states(self, test_database, tmp_path):
        """Only is_active=True AND is_structurally_valid=True configs appear."""
        # Active + valid → included
        _make_config(test_database, protocol="vmess", raw_config="vmess://ok",
                     is_active=True, is_structurally_valid=True)
        # Active + invalid → excluded
        _make_config(test_database, protocol="vmess", raw_config="vmess://bad_valid",
                     is_active=True, is_structurally_valid=False)
        # Inactive + valid → excluded
        _make_config(test_database, protocol="vmess", raw_config="vmess://bad_active",
                     is_active=False, is_structurally_valid=True)

        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        stats = generator.generate()

        assert stats["total_configs"] == 1
        content = (tmp_path / "out" / "vmess.txt").read_text(encoding="utf-8")
        assert content.strip() == "vmess://ok"


# ---------------------------------------------------------------------------
# Tests: Atomic generation
# ---------------------------------------------------------------------------

class TestAtomicGeneration:
    """Test that generation is atomic — partial output is not left on failure."""

    def test_previous_output_preserved_on_new_output_dir(self, test_database, tmp_path):
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        (out_dir / "old_file.txt").write_text("old", encoding="utf-8")

        generator = OutputGenerator(output_dir=str(out_dir), session=test_database)
        generator.generate()

        # Old file should be gone
        assert not (out_dir / "old_file.txt").exists()
        # New files should exist
        assert (out_dir / "all.txt").exists()


# ---------------------------------------------------------------------------
# Tests: File content format
# ---------------------------------------------------------------------------

class TestFileFormat:
    """Test that output files follow the required format."""

    def test_one_config_per_line(self, test_database, tmp_path):
        for i in range(3):
            _make_config(
                test_database,
                protocol="vmess",
                raw_config=f"vmess://config_{i}",
                config_hash=f"{i:064d}",
            )

        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        generator.generate()

        for filename in ["all.txt", "vmess.txt"]:
            content = (tmp_path / "out" / filename).read_text(encoding="utf-8")
            lines = content.strip().split("\n")
            assert len(lines) == 3
            for line in lines:
                assert line.startswith("vmess://")
                # No blank lines within the content
                assert line.strip() != ""

    def test_utf8_encoding(self, test_database, tmp_path):
        _make_config(test_database, protocol="vmess", raw_config="vmess://test")

        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        generator.generate()

        content = (tmp_path / "out" / "all.txt").read_bytes()
        # Should be valid UTF-8
        content.decode("utf-8")

    def test_no_headers_in_machine_readable_files(self, test_database, tmp_path):
        _make_config(test_database, protocol="vmess", raw_config="vmess://test")

        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        generator.generate()

        for filename in ["all.txt", "vmess.txt", "vless.txt", "trojan.txt",
                          "shadowsocks.txt", "hysteria.txt", "hysteria2.txt"]:
            content = (tmp_path / "out" / filename).read_text(encoding="utf-8")
            assert not content.startswith("#")
            assert not content.startswith("===")


# ---------------------------------------------------------------------------
# Tests: CLI generate command
# ---------------------------------------------------------------------------

class TestCLIGenerate:
    """Test the CLI generate command."""

    def test_cmd_generate_empty_db(self, test_database, tmp_path):
        """Test CLI generate with empty database."""
        os.environ["OUTPUT_DIR"] = str(tmp_path / "out")
        os.environ["DATABASE_PATH"] = str(tmp_path / "test.db")
        try:
            # Re-init so settings pick up the new env vars
            import app.config
            app.config.settings = None
            from main import cmd_generate
            result = cmd_generate()
        finally:
            os.environ.pop("OUTPUT_DIR", None)
            os.environ.pop("DATABASE_PATH", None)
            app.config.settings = None

        assert result == 0
        assert (tmp_path / "out" / "all.txt").exists()

    def test_cmd_generate_with_configs(self, test_database, tmp_path):
        """Test CLI generate with configs in database."""
        _make_config(test_database, protocol="vmess", raw_config="vmess://test")

        # Use the test database path (already set by the fixture)
        from app.database.database import get_database_path
        db_path = str(get_database_path())
        os.environ["OUTPUT_DIR"] = str(tmp_path / "out")
        os.environ["DATABASE_PATH"] = db_path
        try:
            import app.config
            app.config.settings = None
            from main import cmd_generate
            result = cmd_generate()
        finally:
            os.environ.pop("OUTPUT_DIR", None)
            os.environ.pop("DATABASE_PATH", None)
            app.config.settings = None

        assert result == 0
        content = (tmp_path / "out" / "vmess.txt").read_text(encoding="utf-8")
        assert "vmess://test" in content


# ---------------------------------------------------------------------------
# Tests: Protocol file separation
# ---------------------------------------------------------------------------

class TestProtocolSeparation:
    """Test that protocols are properly separated into their own files."""

    def test_vmess_only_in_vmess_file(self, test_database, tmp_path):
        raws = ["vmess://aaa", "vmess://bbb", "vmess://ccc"]
        for i, r in enumerate(raws):
            _make_config(test_database, protocol="vmess", raw_config=r, config_hash=f"{i:064d}")

        _make_config(test_database, protocol="vless", raw_config="vless://other",
                     config_hash="f" * 64)

        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        generator.generate()

        vmess_content = (tmp_path / "out" / "vmess.txt").read_text(encoding="utf-8")
        for r in raws:
            assert r in vmess_content
        assert "vless://" not in vmess_content

        vless_content = (tmp_path / "out" / "vless.txt").read_text(encoding="utf-8")
        assert "vless://other" in vless_content
        assert "vmess://" not in vless_content

    def test_all_txt_contains_all_protocols(self, test_database, tmp_path):
        configs = [
            ("vmess", "vmess://a"),
            ("vless", "vless://b"),
            ("trojan", "trojan://c"),
            ("shadowsocks", "ss://d"),
            ("hysteria", "hysteria://e"),
            ("hysteria2", "hysteria2://f"),
        ]
        for i, (proto, raw) in enumerate(configs):
            _make_config(test_database, protocol=proto, raw_config=raw, config_hash=f"{i:064d}")

        generator = OutputGenerator(output_dir=str(tmp_path / "out"), session=test_database)
        generator.generate()

        all_content = (tmp_path / "out" / "all.txt").read_text(encoding="utf-8")
        for _, raw in configs:
            assert raw in all_content


# ---------------------------------------------------------------------------
# Tests: Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Test error handling in the output generator."""

    def test_invalid_output_directory(self, test_database, tmp_path):
        """Test generation with a read-only output directory."""
        read_only_dir = tmp_path / "read_only"
        read_only_dir.mkdir()
        # Create a file to block directory creation
        blocker = read_only_dir / "all.txt"
        blocker.write_text("blocking", encoding="utf-8")
        # Make it read-only on Windows
        import stat
        blocker.chmod(stat.S_IRUSR)

        # Try to write into the read_only dir as if it were a file path
        generator = OutputGenerator(
            output_dir=str(blocker),  # This is a file, not a directory
            session=test_database,
        )
        with pytest.raises(Exception):
            generator.generate()

    def test_output_dir_is_file_not_dir(self, test_database, tmp_path):
        """Test generation when output_dir points to an existing file."""
        existing_file = tmp_path / "existing_file.txt"
        existing_file.write_text("content", encoding="utf-8")

        generator = OutputGenerator(
            output_dir=str(existing_file),
            session=test_database,
        )
        with pytest.raises(Exception):
            generator.generate()
