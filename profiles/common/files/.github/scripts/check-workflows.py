#!/usr/bin/env python3
"""Run the pinned actionlint release against repository workflow sources."""

from __future__ import annotations

import hashlib
import io
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path


ACTIONLINT_VERSION = "1.7.12"
ASSETS = {
    ("Darwin", "arm64"): (
        "actionlint_1.7.12_darwin_arm64.tar.gz",
        "aba9ced2dee8d27fecca3dc7feb1a7f9a52caefa1eb46f3271ea66b6e0e6953f",
    ),
    ("Darwin", "x86_64"): (
        "actionlint_1.7.12_darwin_amd64.tar.gz",
        "5b44c3bc2255115c9b69e30efc0fecdf498fdb63c5d58e17084fd5f16324c644",
    ),
    ("Linux", "aarch64"): (
        "actionlint_1.7.12_linux_arm64.tar.gz",
        "325e971b6ba9bfa504672e29be93c24981eeb1c07576d730e9f7c8805afff0c6",
    ),
    ("Linux", "x86_64"): (
        "actionlint_1.7.12_linux_amd64.tar.gz",
        "8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8",
    ),
}


def _system_actionlint() -> Path | None:
    executable = shutil.which("actionlint")
    if not executable:
        return None
    result = subprocess.run(
        [executable, "-version"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip() == ACTIONLINT_VERSION:
        return Path(executable)
    return None


def _cache_root() -> Path:
    configured = os.environ.get("XDG_CACHE_HOME")
    if configured:
        return Path(configured)
    return Path.home() / ".cache"


def _install_actionlint() -> Path:
    key = (platform.system(), platform.machine())
    asset = ASSETS.get(key)
    if asset is None:
        supported = ", ".join(f"{system}/{machine}" for system, machine in ASSETS)
        raise RuntimeError(
            f"unsupported actionlint platform {key[0]}/{key[1]}; supported: {supported}"
        )
    archive_name, expected_digest = asset
    executable = (
        _cache_root()
        / "repository-standards"
        / "actionlint"
        / ACTIONLINT_VERSION
        / "actionlint"
    )
    if executable.is_file():
        return executable

    url = (
        "https://github.com/rhysd/actionlint/releases/download/"
        f"v{ACTIONLINT_VERSION}/{archive_name}"
    )
    with urllib.request.urlopen(url) as response:
        archive = response.read()
    actual_digest = hashlib.sha256(archive).hexdigest()
    if actual_digest != expected_digest:
        raise RuntimeError(
            f"actionlint archive checksum mismatch: expected {expected_digest}, "
            f"received {actual_digest}"
        )
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
        member = bundle.getmember("actionlint")
        source = bundle.extractfile(member)
        if source is None:
            raise RuntimeError("actionlint archive does not contain the executable")
        content = source.read()
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_bytes(content)
    executable.chmod(0o755)
    return executable


def _workflow_paths() -> list[str]:
    patterns = (
        ".github/workflows/*.yml",
        ".github/workflows/*.yaml",
        "profiles/*/examples/ci.yml",
        "profiles/*/examples/ci.yaml",
    )
    return sorted(
        path.as_posix()
        for pattern in patterns
        for path in Path.cwd().glob(pattern)
        if path.is_file()
    )


def main() -> int:
    paths = sys.argv[1:] or _workflow_paths()
    if not paths:
        print("No GitHub Actions workflows found.")
        return 0
    executable = _system_actionlint() or _install_actionlint()
    return subprocess.run(
        [str(executable), "-shellcheck=", *paths], check=False
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
