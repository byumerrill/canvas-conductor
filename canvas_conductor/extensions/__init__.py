"""Extension auto-discovery.

Drop a `.py` file into this directory that defines a module-level
`app = typer.Typer(name=...)` and it will be registered as a subcommand
group on the main CLI. Files starting with `_` are ignored (use them for
shared helpers or examples like `_example.py`).

By convention, this directory is treated as *private by default* in git
(see the local `.gitignore`). The discovery loader still picks up every
`.py` file at runtime, so a private extension works exactly like a
tracked one; it just won't be committed. `playbook.py` and `_example.py`
are the only extensions tracked as worked examples.
"""
from __future__ import annotations

import importlib
import pkgutil
import sys
import traceback
from pathlib import Path

import typer


def discover_extensions(main_app: typer.Typer) -> list[str]:
    """Scan this package for modules that expose `app: typer.Typer`.

    Each found app is registered onto `main_app` via `add_typer`. Returns the
    list of registered extension names. Errors are printed to stderr but do
    not crash the CLI.
    """
    registered: list[str] = []
    pkg_path = Path(__file__).parent

    for info in pkgutil.iter_modules([str(pkg_path)]):
        if info.name.startswith("_"):
            continue
        full_name = f"{__name__}.{info.name}"
        try:
            mod = importlib.import_module(full_name)
        except Exception as exc:  # pragma: no cover - error path
            print(
                f"warning: failed to load extension '{info.name}': {exc}",
                file=sys.stderr,
            )
            if "--verbose" in sys.argv or "-v" in sys.argv:
                traceback.print_exc()
            continue

        ext_app = getattr(mod, "app", None)
        if not isinstance(ext_app, typer.Typer):
            continue

        name = ext_app.info.name or info.name
        main_app.add_typer(ext_app, name=name)
        registered.append(name)

    return registered
