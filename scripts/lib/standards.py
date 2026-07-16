"""Resolve, audit, and synchronize repository-standard managed files."""

from __future__ import annotations

import argparse
import difflib
import fnmatch
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SUPPORTED_STANDARDS_VERSION = 1
MANIFEST_NAMES = (
    ".repository-standards.json",
    ".repository-standards.yml",
    ".repository-standards.yaml",
)
VARIABLE_PATTERN = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


class StandardsError(Exception):
    """Raised for an invalid manifest, profile, or managed plan."""


@dataclass(frozen=True)
class Source:
    mode: str
    path: Path
    target: str
    order: int
    profile: str
    profile_index: int


@dataclass(frozen=True)
class PlannedFile:
    target: str
    content: bytes
    origins: tuple[str, ...]


@dataclass(frozen=True)
class Result:
    target: str
    status: str
    expected: bytes
    actual: bytes | None
    origins: tuple[str, ...]


def standards_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _relative_path(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise StandardsError(f"{field} must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise StandardsError(f"{field} must stay within the repository: {value!r}")
    return path.as_posix()


def _read_data(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise StandardsError(f"cannot read {path}: {exc}") from exc

    if path.suffix == ".json":
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise StandardsError(f"invalid JSON in {path}: {exc}") from exc
    else:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError as exc:
            raise StandardsError(
                f"{path.name} requires PyYAML; use .repository-standards.json "
                "for dependency-free operation"
            ) from exc
        try:
            value = yaml.safe_load(text)
        except yaml.YAMLError as exc:  # type: ignore[attr-defined]
            raise StandardsError(f"invalid YAML in {path}: {exc}") from exc

    if not isinstance(value, dict):
        raise StandardsError(f"{path} must contain an object")
    return value


def find_manifest(repository: Path, requested: str | None = None) -> Path:
    if requested:
        candidate = Path(requested)
        if not candidate.is_absolute():
            candidate = repository / candidate
        if not candidate.is_file():
            raise StandardsError(f"manifest not found: {candidate}")
        return candidate.resolve()

    found = [repository / name for name in MANIFEST_NAMES if (repository / name).is_file()]
    if not found:
        names = ", ".join(MANIFEST_NAMES)
        raise StandardsError(f"no repository standards manifest found ({names})")
    if len(found) > 1:
        raise StandardsError(f"multiple manifests found: {', '.join(str(path) for path in found)}")
    return found[0].resolve()


def load_manifest(repository: Path, requested: str | None = None) -> tuple[Path, dict[str, Any]]:
    path = find_manifest(repository, requested)
    manifest = _read_data(path)
    allowed = {
        "$schema",
        "standards-version",
        "standards-release",
        "profiles",
        "variables",
        "local-fragments",
        "repository-owned",
    }
    unknown = sorted(set(manifest) - allowed)
    if unknown:
        raise StandardsError(f"unknown manifest fields: {', '.join(unknown)}")

    if manifest.get("standards-version") != SUPPORTED_STANDARDS_VERSION:
        raise StandardsError(
            "standards-version must be " f"{SUPPORTED_STANDARDS_VERSION}"
        )

    standards_release = manifest.get("standards-release")
    if not isinstance(standards_release, str) or not SEMVER_PATTERN.fullmatch(
        standards_release
    ):
        raise StandardsError("standards-release must be a semantic version such as 1.0.0")

    profiles = manifest.get("profiles")
    if not isinstance(profiles, list) or not profiles or not all(
        isinstance(item, str) and item for item in profiles
    ):
        raise StandardsError("profiles must be a non-empty list of names")
    if len(profiles) != len(set(profiles)):
        raise StandardsError("profiles must not contain duplicates")

    variables = manifest.get("variables", {})
    if not isinstance(variables, dict) or not all(
        isinstance(key, str) and isinstance(value, (str, int, float, bool))
        for key, value in variables.items()
    ):
        raise StandardsError("variables must map names to scalar values")

    local_fragments = manifest.get("local-fragments", {})
    if not isinstance(local_fragments, dict):
        raise StandardsError("local-fragments must be an object")
    normalized_fragments: dict[str, list[str]] = {}
    for raw_target, raw_sources in local_fragments.items():
        target = _relative_path(raw_target, "local-fragments target")
        if not isinstance(raw_sources, list) or not all(
            isinstance(item, str) for item in raw_sources
        ):
            raise StandardsError(f"local-fragments[{target!r}] must be a list")
        normalized_fragments[target] = [
            _relative_path(item, f"local-fragments[{target!r}]") for item in raw_sources
        ]

    repository_owned = manifest.get("repository-owned")
    if not isinstance(repository_owned, list) or not all(
        isinstance(item, str) and item for item in repository_owned
    ):
        raise StandardsError("repository-owned must be a list of path patterns")
    for pattern in repository_owned:
        _relative_path(pattern, "repository-owned pattern")

    manifest["local-fragments"] = normalized_fragments
    manifest["variables"] = variables
    return path, manifest


def _load_profile(
    root: Path,
    name: str,
    ordered: list[tuple[str, dict[str, Any], Path]],
    loaded: set[str],
    visiting: set[str],
) -> None:
    if name in loaded:
        return
    if name in visiting:
        raise StandardsError(f"profile inheritance cycle at {name!r}")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise StandardsError(f"invalid profile name: {name!r}")

    profile_dir = root / "profiles" / name
    path = profile_dir / "profile.json"
    if not path.is_file():
        raise StandardsError(f"unknown profile: {name!r}")
    data = _read_data(path)
    if data.get("name") != name:
        raise StandardsError(f"{path}: name must be {name!r}")
    unknown = sorted(set(data) - {"name", "description", "extends", "files"})
    if unknown:
        raise StandardsError(f"{path}: unknown fields: {', '.join(unknown)}")
    parents = data.get("extends", [])
    if not isinstance(parents, list) or not all(isinstance(item, str) for item in parents):
        raise StandardsError(f"{path}: extends must be a list")

    visiting.add(name)
    for parent in parents:
        _load_profile(root, parent, ordered, loaded, visiting)
    visiting.remove(name)
    loaded.add(name)
    ordered.append((name, data, profile_dir))


def load_profiles(root: Path, selected: Iterable[str]) -> list[tuple[str, dict[str, Any], Path]]:
    ordered: list[tuple[str, dict[str, Any], Path]] = []
    loaded: set[str] = set()
    for name in selected:
        _load_profile(root, name, ordered, loaded, set())
    return ordered


def collect_sources(
    profiles: list[tuple[str, dict[str, Any], Path]]
) -> dict[str, list[Source]]:
    targets: dict[str, list[Source]] = {}
    for profile_index, (name, data, profile_dir) in enumerate(profiles):
        files = data.get("files", [])
        if not isinstance(files, list):
            raise StandardsError(f"profile {name!r}: files must be a list")
        for item in files:
            if not isinstance(item, dict):
                raise StandardsError(f"profile {name!r}: file declarations must be objects")
            unknown = sorted(set(item) - {"mode", "source", "target", "order"})
            if unknown:
                raise StandardsError(
                    f"profile {name!r}: unknown file fields: {', '.join(unknown)}"
                )
            mode = item.get("mode")
            if mode not in {"exact", "template", "compose"}:
                raise StandardsError(f"profile {name!r}: invalid file mode {mode!r}")
            source_value = _relative_path(item.get("source"), f"profile {name} source")
            target = _relative_path(item.get("target"), f"profile {name} target")
            order = item.get("order", 0)
            if not isinstance(order, int):
                raise StandardsError(f"profile {name!r}: order must be an integer")
            source = (profile_dir / source_value).resolve()
            try:
                source.relative_to(profile_dir.resolve())
            except ValueError as exc:
                raise StandardsError(f"profile {name!r}: source escapes profile") from exc
            if not source.is_file():
                raise StandardsError(f"profile {name!r}: source not found: {source_value}")
            targets.setdefault(target, []).append(
                Source(mode, source, target, order, name, profile_index)
            )

    for target, sources in targets.items():
        modes = {source.mode for source in sources}
        if modes == {"compose"}:
            continue
        if len(sources) > 1 or len(modes) > 1:
            origins = ", ".join(source.profile for source in sources)
            raise StandardsError(f"conflicting managed target {target!r}: {origins}")
    return targets


def _render_template(source: Source, variables: dict[str, Any]) -> bytes:
    try:
        template = source.path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise StandardsError(f"cannot read template {source.path}: {exc}") from exc
    missing = sorted(set(VARIABLE_PATTERN.findall(template)) - set(variables))
    if missing:
        raise StandardsError(
            f"template {source.path} is missing variables: {', '.join(missing)}"
        )
    rendered = VARIABLE_PATTERN.sub(lambda match: str(variables[match.group(1)]), template)
    remaining = VARIABLE_PATTERN.findall(rendered)
    if remaining:
        raise StandardsError(f"unresolved variables in {source.path}")
    return rendered.encode("utf-8")


def _join_fragments(parts: list[bytes], target: str) -> bytes:
    decoded: list[str] = []
    for part in parts:
        try:
            decoded.append(part.decode("utf-8").strip("\n"))
        except UnicodeDecodeError as exc:
            raise StandardsError(f"compose target {target!r} must use UTF-8 fragments") from exc
    return ("\n\n".join(value for value in decoded if value) + "\n").encode("utf-8")


def _matches_owned(target: str, patterns: Iterable[str]) -> str | None:
    for pattern in patterns:
        if fnmatch.fnmatchcase(target, pattern):
            return pattern
    return None


def build_plan(root: Path, repository: Path, manifest: dict[str, Any]) -> list[PlannedFile]:
    root = root.resolve()
    repository = repository.resolve()
    version_path = root / "VERSION"
    try:
        source_release = version_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise StandardsError(f"cannot read standards release from {version_path}: {exc}") from exc
    if manifest["standards-release"] != source_release:
        raise StandardsError(
            f"manifest requires standards release {manifest['standards-release']}, "
            f"but this checkout is {source_release}; check out tag "
            f"v{manifest['standards-release']} or update the manifest deliberately"
        )
    profiles = load_profiles(root, manifest["profiles"])
    sources_by_target = collect_sources(profiles)
    local_fragments: dict[str, list[str]] = manifest["local-fragments"]

    unknown_fragment_targets = sorted(set(local_fragments) - set(sources_by_target))
    if unknown_fragment_targets:
        raise StandardsError(
            "local fragments require a managed compose target: "
            + ", ".join(unknown_fragment_targets)
        )

    planned: list[PlannedFile] = []
    for target in sorted(sources_by_target):
        owned_pattern = _matches_owned(target, manifest["repository-owned"])
        if owned_pattern:
            raise StandardsError(
                f"managed target {target!r} conflicts with repository-owned pattern "
                f"{owned_pattern!r}"
            )
        sources = sources_by_target[target]
        origins = [f"{source.profile}:{source.path.name}" for source in sources]
        if sources[0].mode == "exact":
            content = sources[0].path.read_bytes()
        elif sources[0].mode == "template":
            content = _render_template(sources[0], manifest["variables"])
        else:
            sources = sorted(sources, key=lambda item: (item.order, item.profile_index))
            parts = [source.path.read_bytes() for source in sources]
            origins = [f"{source.profile}:{source.path.name}" for source in sources]
            for local_value in local_fragments.get(target, []):
                local_path = (repository / local_value).resolve()
                try:
                    local_path.relative_to(repository)
                except ValueError as exc:
                    raise StandardsError(f"local fragment escapes repository: {local_value}") from exc
                if not local_path.is_file():
                    raise StandardsError(f"local fragment not found: {local_value}")
                parts.append(local_path.read_bytes())
                origins.append(f"repository:{local_value}")
            content = _join_fragments(parts, target)
        planned.append(PlannedFile(target, content, tuple(origins)))
    return planned


def inspect(repository: Path, plan: Iterable[PlannedFile]) -> list[Result]:
    repository = repository.resolve()
    results: list[Result] = []
    for item in plan:
        target = repository / item.target
        resolved = target.resolve(strict=False)
        try:
            resolved.relative_to(repository)
        except ValueError as exc:
            raise StandardsError(f"managed target escapes through a symlink: {item.target}") from exc
        if target.is_symlink():
            raise StandardsError(f"managed target must not be a symlink: {item.target}")
        if not target.exists():
            results.append(Result(item.target, "missing", item.content, None, item.origins))
        elif not target.is_file():
            results.append(Result(item.target, "not-file", item.content, None, item.origins))
        else:
            try:
                actual = target.read_bytes()
            except OSError as exc:
                raise StandardsError(f"cannot read managed target {item.target}: {exc}") from exc
            status = "ok" if actual == item.content else "drift"
            results.append(Result(item.target, status, item.content, actual, item.origins))
    return results


def _text_diff(result: Result) -> str:
    if result.actual is None:
        actual_text = ""
    else:
        try:
            actual_text = result.actual.decode("utf-8")
        except UnicodeDecodeError:
            return f"Binary content differs for {result.target}\n"
    try:
        expected_text = result.expected.decode("utf-8")
    except UnicodeDecodeError:
        return f"Binary content differs for {result.target}\n"
    return "".join(
        difflib.unified_diff(
            actual_text.splitlines(keepends=True),
            expected_text.splitlines(keepends=True),
            fromfile=f"a/{result.target}",
            tofile=f"b/{result.target}",
        )
    )


def write(repository: Path, results: Iterable[Result]) -> int:
    repository = repository.resolve()
    changed = 0
    for result in results:
        if result.status == "ok":
            continue
        target = repository / result.target
        resolved = target.resolve(strict=False)
        try:
            resolved.relative_to(repository)
        except ValueError as exc:
            raise StandardsError(f"managed target escapes through a symlink: {result.target}") from exc
        if target.is_symlink():
            raise StandardsError(f"managed target must not be a symlink: {result.target}")
        if target.exists() and not target.is_file():
            raise StandardsError(f"managed target is not a file: {result.target}")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(result.expected)
        except OSError as exc:
            raise StandardsError(f"cannot write managed target {result.target}: {exc}") from exc
        changed += 1
    return changed


def _resolve(repository_value: str, manifest_value: str | None) -> tuple[Path, Path, dict[str, Any], list[Result]]:
    repository = Path(repository_value).expanduser().resolve()
    if not repository.is_dir():
        raise StandardsError(f"repository directory not found: {repository}")
    _, manifest = load_manifest(repository, manifest_value)
    plan = build_plan(standards_root(), repository, manifest)
    return repository, standards_root(), manifest, inspect(repository, plan)


def audit_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit managed repository standards")
    parser.add_argument("repository", help="repository to audit")
    parser.add_argument("--manifest", help="manifest path, relative to repository")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    try:
        repository, _, manifest, results = _resolve(args.repository, args.manifest)
    except StandardsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    drift = [result for result in results if result.status != "ok"]
    if args.json_output:
        print(
            json.dumps(
                {
                    "repository": str(repository),
                    "standards-version": manifest["standards-version"],
                    "standards-release": manifest["standards-release"],
                    "profiles": manifest["profiles"],
                    "clean": not drift,
                    "files": [
                        {
                            "path": result.target,
                            "status": result.status,
                            "origins": list(result.origins),
                        }
                        for result in results
                    ],
                },
                indent=2,
            )
        )
    else:
        for result in results:
            marker = "OK" if result.status == "ok" else result.status.upper()
            print(f"{marker:8} {result.target}")
        print(f"\n{len(results) - len(drift)} clean, {len(drift)} requiring synchronization")
    return 1 if drift else 0


def sync_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preview or write managed repository standards")
    parser.add_argument("repository", help="repository to synchronize")
    parser.add_argument("--manifest", help="manifest path, relative to repository")
    parser.add_argument("--write", action="store_true", help="write managed targets")
    args = parser.parse_args(argv)
    try:
        repository, _, _, results = _resolve(args.repository, args.manifest)
        drift = [result for result in results if result.status != "ok"]
        if args.write:
            changed = write(repository, drift)
            print(f"Synchronized {changed} managed file(s) in {repository}")
            return 0
        if not drift:
            print(f"All managed files are current in {repository}")
            return 0
        for result in drift:
            print(_text_diff(result), end="")
        print(f"\nPreview: {len(drift)} managed file(s) would change. Re-run with --write.")
        return 1
    except StandardsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
