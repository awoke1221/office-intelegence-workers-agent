#!/usr/bin/env python3
"""Launch the app in the repository project virtual environment.

This script creates and reuses a workspace-local `.venv` once.
If the virtual environment is missing, it will be created and the
project requirements will be installed only once.

Usage:
  python start.py
"""

from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
PYTHON_EXE = VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def in_project_venv() -> bool:
    try:
        return Path(sys.executable).resolve() == PYTHON_EXE.resolve()
    except Exception:
        return False


def create_venv() -> None:
    print("Creating project virtual environment in .venv...")
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])
    install_requirements()


def ensure_venv() -> None:
    if not VENV_DIR.exists() or not PYTHON_EXE.exists():
        create_venv()

    if not in_project_venv():
        print("Launching with the repository project virtual environment...")
        subprocess.call([str(PYTHON_EXE), str(__file__)] + sys.argv[1:])


def install_requirements() -> None:
    print("Installing requirements into .venv...")
    subprocess.check_call([str(PYTHON_EXE), "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([str(PYTHON_EXE), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])


def run_command(args: list[str]) -> int:
    command = [sys.executable] + args
    return subprocess.call(command, cwd=str(ROOT))


if __name__ == "__main__":
    ensure_venv()

    install_requirements()

    if len(sys.argv) > 1:
        raise SystemExit(run_command(sys.argv[1:]))

    print("Project environment is ready.")
    print("Use the Next.js frontend at C:\\Users\\hp\\Pictures\\Microfinince  frontend.")
    print("Start it with `npm install` and `npm run dev` from the frontend folder.")
