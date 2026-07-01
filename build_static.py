import shutil
from pathlib import Path

SOURCE_DIR = Path(__file__).parent / "app" / "static"
DEST_DIR = Path(__file__).parent / "public" / "static"


def main():
    for folder in ("css", "js"):
        shutil.copytree(
            SOURCE_DIR / folder,
            DEST_DIR / folder,
            dirs_exist_ok=True
        )

    print("Copied app/static/{css,js} into public/static/.")


if __name__ == "__main__":
    main()
