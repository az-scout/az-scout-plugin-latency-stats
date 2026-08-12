"""Tests for vendored third-party static assets.

az-scout recommends vendoring third-party frontend assets so the plugin works offline /
air-gapped. These tests guard that guarantee against regressions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from az_scout_latency_stats import LatencyStatsPlugin

# Hosts that would reintroduce a runtime network dependency for the UI.
CDN_PATTERN = re.compile(
    r"https?://(?:[\w.-]*\.)?(?:jsdelivr\.net|unpkg\.com|cdnjs\.cloudflare\.com|"
    r"ajax\.googleapis\.com|esm\.sh|skypack\.dev)",
    re.IGNORECASE,
)

VENDORED_FILES = (
    "vendor/topojson-client/topojson-client.min.js",
    "vendor/topojson-client/LICENSE",
    "vendor/world-atlas/countries-110m.json",
    "vendor/world-atlas/LICENSE",
)


def _static_dir() -> Path:
    static_dir = LatencyStatsPlugin().get_static_dir()
    assert static_dir is not None
    return static_dir


def _frontend_sources() -> list[Path]:
    static_dir = _static_dir()
    sources = [
        path
        for suffix in ("js", "css", "html")
        for path in static_dir.rglob(f"*.{suffix}")
        if "vendor" not in path.relative_to(static_dir).parts
    ]
    assert sources, "expected to find plugin frontend sources"
    return sources


class TestVendoredAssets:
    """The plugin must not depend on a CDN at runtime."""

    @pytest.mark.parametrize("relative_path", VENDORED_FILES)
    def test_vendored_file_is_shipped(self, relative_path: str) -> None:
        path = _static_dir() / relative_path

        assert path.is_file(), f"missing vendored asset: {relative_path}"
        assert path.stat().st_size > 0

    def test_no_cdn_references_in_frontend_sources(self) -> None:
        offenders = {
            path.name: CDN_PATTERN.findall(path.read_text(encoding="utf-8"))
            for path in _frontend_sources()
            if CDN_PATTERN.search(path.read_text(encoding="utf-8"))
        }

        assert not offenders, f"CDN references must be vendored instead: {offenders}"

    def test_frontend_references_vendored_paths(self) -> None:
        source = (_static_dir() / "js" / "latency-tab.js").read_text(encoding="utf-8")

        assert "static/vendor/topojson-client/topojson-client.min.js" in source
        assert "static/vendor/world-atlas/countries-110m.json" in source

    def test_vendored_topology_is_usable(self) -> None:
        topology = json.loads(
            (_static_dir() / "vendor" / "world-atlas" / "countries-110m.json").read_text(
                encoding="utf-8"
            )
        )

        assert topology["type"] == "Topology"
        assert "countries" in topology["objects"]
        assert topology["arcs"]

    def test_vendored_topojson_bundle_exposes_global(self) -> None:
        bundle = (
            _static_dir() / "vendor" / "topojson-client" / "topojson-client.min.js"
        ).read_text(encoding="utf-8")

        assert "topojson" in bundle
        assert "v3.1.0" in bundle
