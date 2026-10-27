"""PyInstaller entry point, deliberately outside the gsrim package."""
from gsrim.portable import main

if __name__ == "__main__":
    raise SystemExit(main())
