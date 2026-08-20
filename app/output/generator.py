"""
Output Generator for V2Ray Aggregator.

Reads active/valid canonical configurations from the database and generates
public output files: per-protocol text files, all.txt, stats.json, and README.md.
"""
import json
import shutil
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.repository import ConfigRepository
from app.logging_config import get_logger

logger = get_logger(__name__)

# All supported protocols in deterministic order
SUPPORTED_PROTOCOLS = [
    "vmess",
    "vless",
    "trojan",
    "shadowsocks",
    "hysteria",
    "hysteria2",
]

# Mapping from protocol to output filename
PROTOCOL_FILENAMES = {
    "vmess": "vmess.txt",
    "vless": "vless.txt",
    "trojan": "trojan.txt",
    "shadowsocks": "shadowsocks.txt",
    "hysteria": "hysteria.txt",
    "hysteria2": "hysteria2.txt",
}


@dataclass(frozen=True)
class ConfigSnapshot:
    """Lightweight, session-independent snapshot of a config row."""
    protocol: str
    raw_config: str
    config_hash: str


class OutputGenerator:
    """
    Reusable output generator that reads active/valid configs from the database
    and produces the complete public output set.

    Strategy:
    - Source of truth: database (Config table, is_active=True, is_structurally_valid=True)
    - Deduplication: inherent via unique config_hash in the database
    - Sorting: by config_hash for deterministic, stable ordering
    - Safety: generates into a temporary staging directory, then atomically replaces
    """

    def __init__(self, output_dir: Optional[str] = None, session: Optional[Session] = None):
        """
        Initialize the output generator.

        Args:
            output_dir: Override output directory. If None, uses settings.output_dir.
            session: Database session. If None, creates one via get_session context manager.
        """
        settings = get_settings()
        self.output_dir = Path(output_dir or settings.output_dir)
        self.channel_name = settings.channel_name
        self.channel_username = settings.channel_username
        self._session = session

    def generate(self) -> Dict[str, Any]:
        """
        Generate the complete output set.

        Uses atomic generation: writes to a temp directory first, then replaces
        the output directory only after successful generation.

        Returns:
            Dictionary with generation statistics.
        """
        logger.info("Starting output generation")

        try:
            # Fetch active configs from database (extracts data within session scope)
            snapshots = self._fetch_active_configs()
            logger.info(f"Fetched {len(snapshots)} active configurations")

            # Group by protocol and sort deterministically
            protocol_groups = self._group_by_protocol(snapshots)

            # Create temp staging directory
            staging_dir = Path(tempfile.mkdtemp(prefix="v2ray_output_"))

            try:
                # Generate per-protocol files
                for protocol in SUPPORTED_PROTOCOLS:
                    lines = [
                        snap.raw_config
                        for snap in protocol_groups.get(protocol, [])
                    ]
                    self._write_text_file(
                        staging_dir / PROTOCOL_FILENAMES[protocol],
                        lines,
                    )

                # Generate all.txt (union of all protocols, sorted by hash)
                all_lines = []
                for protocol in SUPPORTED_PROTOCOLS:
                    all_lines.extend([
                        snap.raw_config
                        for snap in protocol_groups.get(protocol, [])
                    ])
                self._write_text_file(staging_dir / "all.txt", all_lines)

                # Generate stats.json
                stats = self._compute_stats(snapshots, protocol_groups)
                self._write_json_file(staging_dir / "stats.json", stats)

                # Generate README.md
                readme = self._generate_readme(stats)
                self._write_text_file(staging_dir / "README.md", [readme])

                # Atomic replacement of output directory
                self._atomic_replace(staging_dir)

                logger.info(
                    f"Output generation complete: {stats['total_configs']} configs "
                    f"across {len([p for p, c in protocol_groups.items() if c])} protocols"
                )
                return stats

            except Exception:
                # Clean up staging directory on failure
                shutil.rmtree(staging_dir, ignore_errors=True)
                raise

        except Exception as e:
            logger.error(f"Output generation failed: {e}")
            raise

    def _fetch_active_configs(self) -> List[ConfigSnapshot]:
        """
        Fetch active, structurally valid configurations from the database.

        Extracts lightweight snapshots within the session scope so that
        ORM objects are never used after the session closes.

        Returns:
            List of ConfigSnapshot objects sorted by config_hash.
        """
        if self._session is not None:
            configs = ConfigRepository.get_all_active(self._session)
            return self._extract_snapshots(configs)

        from app.database.database import get_session

        with get_session() as session:
            configs = ConfigRepository.get_all_active(session)
            return self._extract_snapshots(configs)

    @staticmethod
    def _extract_snapshots(configs: list) -> List[ConfigSnapshot]:
        """Extract lightweight snapshots from ORM Config objects."""
        snapshots = [
            ConfigSnapshot(
                protocol=c.protocol,
                raw_config=c.raw_config,
                config_hash=c.config_hash,
            )
            for c in configs
        ]
        snapshots.sort(key=lambda s: s.config_hash)
        return snapshots

    def _group_by_protocol(self, snapshots: List[ConfigSnapshot]) -> Dict[str, List[ConfigSnapshot]]:
        """
        Group config snapshots by protocol, sorted by config_hash within each group.

        Args:
            snapshots: List of ConfigSnapshot objects.

        Returns:
            Dictionary mapping protocol name to sorted list of ConfigSnapshot objects.
        """
        groups: Dict[str, List[ConfigSnapshot]] = defaultdict(list)
        for snap in snapshots:
            groups[snap.protocol].append(snap)

        # Sort each group by config_hash for deterministic ordering
        for protocol in groups:
            groups[protocol].sort(key=lambda s: s.config_hash)

        return dict(groups)

    def _compute_stats(
        self,
        snapshots: List[ConfigSnapshot],
        protocol_groups: Dict[str, List[ConfigSnapshot]],
    ) -> Dict[str, Any]:
        """
        Compute non-sensitive aggregate statistics.

        Args:
            snapshots: All active config snapshots.
            protocol_groups: Configs grouped by protocol.

        Returns:
            Dictionary with statistics.
        """
        configs_by_protocol: Dict[str, int] = {}
        for protocol in SUPPORTED_PROTOCOLS:
            count = len(protocol_groups.get(protocol, []))
            if count > 0:
                configs_by_protocol[protocol] = count

        return {
            "total_configs": len(snapshots),
            "configs_by_protocol": configs_by_protocol,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "channel_name": self.channel_name,
            "channel_username": self.channel_username,
        }

    def _generate_readme(self, stats: Dict[str, Any]) -> str:
        """
        Generate a public-facing README.md.

        Args:
            stats: Generation statistics.

        Returns:
            README content as a string.
        """
        lines = [
            f"# {self.channel_name}",
            "",
            f"> Auto-updated V2Ray configuration list from **{self.channel_username}**.",
            "",
            "## Supported Protocols",
            "",
            "| Protocol | File |",
            "| --- | --- |",
        ]

        for protocol in SUPPORTED_PROTOCOLS:
            filename = PROTOCOL_FILENAMES[protocol]
            lines.append(f"| {protocol.upper()} | [{filename}](configs/{filename}) |")

        lines.extend([
            "",
            "## All Configurations",
            "",
            f"- **File:** [all.txt](configs/all.txt)",
            f"- **Total unique configs:** {stats['total_configs']}",
            "",
            "## Statistics",
            "",
            f"- **Generated at:** {stats['generated_at']}",
        ])

        for protocol, count in stats.get("configs_by_protocol", {}).items():
            lines.append(f"- **{protocol.upper()}:** {count} configurations")

        lines.extend([
            "",
            "## Usage",
            "",
            "1. Subscribe to one of the per-protocol files above in your V2Ray client.",
            "2. The files are updated automatically.",
            "",
            "---",
            "",
            f"*Updated automatically by {self.channel_name}*",
        ])

        return "\n".join(lines) + "\n"

    def _write_text_file(self, path: Path, lines: List[str]) -> None:
        """
        Write a text file with one entry per line.

        Args:
            path: File path to write.
            lines: List of strings, one per line.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(lines)
        if lines:
            content += "\n"
        path.write_text(content, encoding="utf-8")

    def _write_json_file(self, path: Path, data: Dict[str, Any]) -> None:
        """
        Write a JSON file with readable formatting.

        Args:
            path: File path to write.
            data: Dictionary to serialize.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(data, indent=2, ensure_ascii=False)
        path.write_text(content, encoding="utf-8")

    def _atomic_replace(self, staging_dir: Path) -> None:
        """
        Atomically replace the output directory with the staging directory.

        Uses rename when possible (same filesystem), falls back to copy+delete.

        Args:
            staging_dir: Path to the staging directory with generated files.
        """
        output_dir = self.output_dir.resolve()
        staging_resolved = staging_dir.resolve()

        # If output dir exists, remove it first
        if output_dir.exists():
            # Remove old output
            shutil.rmtree(output_dir)

        # Move staging to output
        try:
            shutil.move(str(staging_resolved), str(output_dir))
        except Exception:
            # Fallback: copy then delete staging
            shutil.copytree(str(staging_resolved), str(output_dir))
            shutil.rmtree(staging_resolved, ignore_errors=True)
