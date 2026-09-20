#!/usr/bin/env python3
"""Write the lab guide as a single self-contained HTML file.

Images are embedded as data URIs and the diagrams are already inline SVG, so the
result opens by double-clicking it. No server, no internet, nothing to install.

    python3 projects/lab-runner/export-guide.py [lab-id]
"""

import base64
import json
import mimetypes
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import report  # noqa: E402

PROJECTS = ROOT.parent
LAB_ID = sys.argv[1] if len(sys.argv) > 1 else "01-cost-visibility"


def lab_dir(lab_id: str) -> Path:
    matches = sorted(PROJECTS.glob(f"{lab_id}*"))
    if not matches:
        sys.exit(f"No project folder matching {lab_id!r}")
    return matches[0]


def main() -> None:
    lab_file = ROOT / "labs" / f"{LAB_ID}.json"
    if not lab_file.is_file():
        sys.exit(f"No lab content at {lab_file}")

    lab = json.loads(lab_file.read_text())
    root = lab_dir(LAB_ID)

    # Build with a placeholder prefix, then swap each reference for a data URI.
    html = report.build_guide(lab, root, "EMBED::")

    shots = root / "docs" / "evidence" / "screenshots"
    embedded = 0

    def embed(m: re.Match) -> str:
        nonlocal embedded
        name = m.group(1)
        f = shots / name
        if not f.is_file():
            return 'src=""'
        mime = mimetypes.guess_type(name)[0] or "image/png"
        b64 = base64.b64encode(f.read_bytes()).decode()
        embedded += 1
        return f'src="data:{mime};base64,{b64}"'

    html = re.sub(r'src="EMBED::([^"]+)"', embed, html)

    out = root / "docs" / "guide.html"
    out.write_text(html, encoding="utf-8")

    print(f"  {out}")
    print(f"  {round(out.stat().st_size / 1024)} KB, {embedded} image(s) embedded")
    print("\n  Double-click it, or:  open " + str(out))


if __name__ == "__main__":
    main()
