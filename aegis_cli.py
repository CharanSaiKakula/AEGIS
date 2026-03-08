"""CLI: aegis run <script> [args...] | aegis fly [args...]"""

import os
import subprocess
import sys

if sys.version_info[:2] != (3, 12):
    print("aegis requires Python 3.12 (current: {}.{}).".format(*sys.version_info[:2]), file=sys.stderr)
    sys.exit(1)

# Project root (aegis_cli.py lives here)
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: aegis run <script> [args...]  |  aegis fly [args...]")
        print("  run   Run a script (e.g. aegis run flight_ops/utils/debug.py)")
        print("  fly   Run flight_ops main (same as aegis run flight_ops/main.py from project root)")
        sys.exit(1)

    if args[0] == "fly":
        # Run flight_ops.main; cwd=project root so flight_ops package is found
        fly_args = args[1:]
        sys.exit(
            subprocess.run(
                [sys.executable, "-m", "flight_ops.main"] + fly_args,
                cwd=_PROJECT_ROOT,
            ).returncode
        )

    if args[0] == "run" and len(args) > 1:
        script = args[1]
        script_args = args[2:]
        # Run from project root so flight_ops (and cv) resolve when script is flight_ops/main.py
        cwd = _PROJECT_ROOT if script.startswith("flight_ops/") or script.startswith("flight_ops\\") else None
        sys.exit(subprocess.run([sys.executable, script] + script_args, cwd=cwd).returncode)

    print("Usage: aegis run <script> [args...]  |  aegis fly [args...]")
    print("  Example: aegis run flight_ops/utils/debug.py")
    print("  Example: aegis fly   or   aegis fly --mock")
    sys.exit(1)
