"""Two-pass index page numbers: render docx to PDF, find the page of each section heading."""
import json, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
docx = ROOT / "docs" / "report.docx"
subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", "/tmp/rep", str(docx)], check=True, capture_output=True)
txt = subprocess.run(["pdftotext", "-layout", "/tmp/rep/report.pdf", "-"], capture_output=True, text=True).stdout
pages = txt.split("\f")
heads = ["1  Introduction", "2  Comparative Study of Literature", "3  Objective", "4  Methodology", "5  Work Done", "6  Results", "7  References"]
out = {}
for h in heads:
    pat = re.compile(r"^\s*" + re.escape(h).replace(r"\ \ ", r"\s+") + r"\s*$", re.M)
    for i, p in enumerate(pages[2:], start=3):      # skip cover and index
        if pat.search(p):
            out[h] = i
            break
print(out, "pages:", len(pages) - 1)
(ROOT / "docs" / ".report_pages.json").write_text(json.dumps(out))
