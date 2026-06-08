"""Entry point for `python -m inclave_bridge` and the PyInstaller bundle."""

from inclave_bridge.server import main

if __name__ == "__main__":
    raise SystemExit(main())
