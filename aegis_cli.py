"""CLI for running Python scripts: aegis run <script> [args...]"""

import subprocess
import sys


def main():
    args = sys.argv[1:]
    if args and args[0] == "run" and len(args) > 1:
        script = args[1]
        script_args = args[2:]
        sys.exit(subprocess.run([sys.executable, script] + script_args).returncode)
    else:
        print("Usage: aegis run <script> [args...]")
        print("  Example: aegis run flight_ops/main.py")
        sys.exit(1)
