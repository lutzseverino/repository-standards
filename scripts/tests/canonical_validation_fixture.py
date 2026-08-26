from __future__ import annotations

import textwrap
from pathlib import Path


def write_fake_canonical_validation(library: Path) -> None:
    """Install the selected-release validation boundary used by lifecycle tests."""

    (library / "canonical_validation.py").write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import argparse
            import json
            from pathlib import Path
            import subprocess
            import sys

            parser = argparse.ArgumentParser()
            parser.add_argument("repository")
            parser.add_argument("--standards-root")
            args = parser.parse_args()
            repository = Path(args.repository)
            manifest = json.loads(
                (repository / ".repository-standards.json").read_text(encoding="utf-8")
            )
            validation = manifest["canonical-validation"]
            try:
                result = subprocess.run(
                    [validation["executable"], *validation["arguments"]],
                    cwd=repository / validation.get("working-directory", "."),
                    check=False,
                )
            except FileNotFoundError:
                print(
                    "error: canonical validation executable is unavailable: "
                    + repr(validation["executable"]),
                    file=sys.stderr,
                )
                raise SystemExit(127)
            if result.returncode:
                print(
                    "error: canonical validation exited with status "
                    + str(result.returncode),
                    file=sys.stderr,
                )
            raise SystemExit(result.returncode)
            """
        ),
        encoding="utf-8",
    )
