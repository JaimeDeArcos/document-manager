"""Generate a tiny, public-domain-style example PDF for the walkthrough."""

import pymupdf

from .config import Settings


def main() -> None:
    target = Settings.from_env().data_dir / "demo-handbook.pdf"
    target.parent.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open()
    for title, body in [
        ("Retention", "Project notes are kept for 90 days after a project closes."),
        ("Deletion", "After the retention period, the owner deletes the notes from local storage."),
    ]:
        page = document.new_page()
        page.insert_text((72, 80), title, fontsize=20)
        page.insert_text((72, 125), body, fontsize=12)
    document.set_toc([[1, "Retention", 1], [1, "Deletion", 2]])
    document.save(target)
    document.close()
    print(f"Created {target}. Upload it in the app and ask: How long are project notes kept?")


if __name__ == "__main__":
    main()
