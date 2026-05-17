#!/usr/bin/env python3
# huntd/scripts/parse_resume.py
"""Parse a PDF or DOCX resume and write its text to resume.md.

Usage: python scripts/parse_resume.py [path/to/resume.pdf]
       If no path given, auto-detects PDF/DOCX files in the huntd root.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def find_resume_file() -> Path | None:
    """Find a PDF or DOCX file in the huntd root directory."""
    for ext in ("*.pdf", "*.PDF", "*.docx", "*.DOCX"):
        matches = list(ROOT.glob(ext))
        if matches:
            return matches[0]
    return None


def parse_pdf(path: Path) -> str:
    import pdfplumber
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
    return "\n\n".join(pages)


def parse_docx(path: Path) -> str:
    from docx import Document
    doc = Document(path)
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def parse_resume(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(path)
    elif suffix == ".docx":
        return parse_docx(path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Use PDF or DOCX.")


def main() -> None:
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    if len(sys.argv) > 1:
        resume_path = Path(sys.argv[1])
    else:
        resume_path = find_resume_file()

    if not resume_path or not resume_path.exists():
        console.print(
            Panel(
                "No resume found.\n\n"
                "Drag your [bold]PDF or DOCX[/] resume into this folder, then run:\n"
                "  [bold cyan]gemini \"run /huntd setup\"[/]\n\n"
                "Or specify the path directly:\n"
                "  [dim]python scripts/parse_resume.py path/to/resume.pdf[/]",
                title="[bold red]huntd setup[/]",
                border_style="red",
            )
        )
        sys.exit(1)

    console.print(f"Parsing [bold]{resume_path.name}[/]...")
    text = parse_resume(resume_path)

    if not text.strip():
        console.print(f"[bold red]ERROR:[/] Could not extract text from {resume_path.name}. Try a different format.")
        sys.exit(1)

    out = ROOT / "resume.md"
    out.write_text(f"# Resume\n\n{text}\n")
    console.print(
        Panel(
            f"[bold cyan]{resume_path.name}[/] parsed successfully.\n"
            f"Saved to [dim]resume.md[/] ({len(text)} characters extracted).\n\n"
            "The AI will now read this file during setup and scoring.",
            border_style="cyan",
        )
    )


if __name__ == "__main__":
    main()
