#!/usr/bin/env python3
"""Sync vendored third-party frontend assets into the plugin's static/vendor/ directory.

Stdlib-only: no npm, no bundler, no build step. The committed files under
``src/az_scout_latency_stats/static/vendor/`` are the source of truth — this script only
refreshes them from pinned upstream versions.

Usage::

    python tools/vendor_assets.py                     # download + verify pinned assets
    python tools/vendor_assets.py --check             # verify committed files, download nothing
    python tools/vendor_assets.py --update-checksums  # re-pin checksums after a version bump
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VENDOR_DIR = REPO_ROOT / "src" / "az_scout_latency_stats" / "static" / "vendor"

USER_AGENT = "az-scout-plugin-latency-stats vendor_assets.py"


@dataclass(frozen=True)
class Asset:
    """A single pinned third-party file to vendor."""

    name: str
    version: str
    url: str
    dest: str
    sha256: str

    @property
    def path(self) -> Path:
        return VENDOR_DIR / self.dest


# Pinned upstream assets. Bump ``version``/``url``, then run with --update-checksums.
ASSETS: tuple[Asset, ...] = (
    Asset(
        name="topojson-client",
        version="3.1.0",
        url="https://cdn.jsdelivr.net/npm/topojson-client@3.1.0/dist/topojson-client.min.js",
        dest="topojson-client/topojson-client.min.js",
        sha256="25cd02ae486cc5063e0215a4e4cfb15de83700c87ac48bac4d57dc6aaf3ebb89",
    ),
    Asset(
        name="topojson-client (license)",
        version="3.1.0",
        url="https://cdn.jsdelivr.net/npm/topojson-client@3.1.0/LICENSE",
        dest="topojson-client/LICENSE",
        sha256="4c4d15b635e04e691825a76db7d33f7f2033b55669a7430011694f31e6c65999",
    ),
    Asset(
        name="world-atlas countries-110m",
        version="2.0.2",
        url="https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json",
        dest="world-atlas/countries-110m.json",
        sha256="2516c915867c7baf18ddec727aec46c315541a07cfb3d79a6559b05d5e94eee8",
    ),
    Asset(
        name="world-atlas (license)",
        version="2.0.2",
        url="https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/LICENSE",
        dest="world-atlas/LICENSE",
        sha256="8048290dfdb6e83fbed17e8985c8cfc4ce9da9b842642f3d3e497280790cfa31",
    ),
)


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        data: bytes = response.read()
    return data


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def check_only() -> int:
    """Verify committed files match their pinned checksums."""
    failures = 0
    for asset in ASSETS:
        if not asset.path.exists():
            print(f"MISSING  {asset.dest}")
            failures += 1
            continue
        actual = digest(asset.path.read_bytes())
        if asset.sha256 == "PLACEHOLDER":
            print(f"UNPINNED {asset.dest} (sha256={actual})")
            failures += 1
        elif actual != asset.sha256:
            print(f"MISMATCH {asset.dest}\n  expected {asset.sha256}\n  actual   {actual}")
            failures += 1
        else:
            print(f"OK       {asset.dest}")
    return 1 if failures else 0


def sync(update_checksums: bool) -> int:
    """Download each pinned asset and write it into static/vendor/."""
    failures = 0
    resolved: list[tuple[Asset, str]] = []

    for asset in ASSETS:
        print(f"Fetching {asset.name} {asset.version} ...")
        try:
            payload = download(asset.url)
        except Exception as exc:  # noqa: BLE001 - report and continue with the other assets
            print(f"  FAILED: {exc}")
            failures += 1
            continue

        actual = digest(payload)
        resolved.append((asset, actual))

        if not update_checksums and asset.sha256 not in ("PLACEHOLDER", actual):
            print(f"  CHECKSUM MISMATCH\n    expected {asset.sha256}\n    actual   {actual}")
            print("  Refusing to write. Re-run with --update-checksums if the bump is intended.")
            failures += 1
            continue

        asset.path.parent.mkdir(parents=True, exist_ok=True)
        asset.path.write_bytes(payload)
        rel = asset.path.relative_to(REPO_ROOT)
        print(f"  wrote {rel} ({len(payload)} bytes, sha256={actual})")

    if update_checksums and resolved:
        print("\nUpdate the ASSETS manifest with these checksums:\n")
        for asset, actual in resolved:
            print(f'  {asset.dest}\n    sha256="{actual}",')

    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed files against pinned checksums without downloading",
    )
    parser.add_argument(
        "--update-checksums",
        action="store_true",
        help="download assets and print refreshed checksums (use after a version bump)",
    )
    args = parser.parse_args()

    if args.check:
        return check_only()
    return sync(update_checksums=args.update_checksums)


if __name__ == "__main__":
    sys.exit(main())
