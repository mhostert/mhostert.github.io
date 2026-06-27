#!/usr/bin/env python3
"""
update_pubs.py - Generate and enrich publication pages for the academic website.

Step 1 — Generate markdown files from INSPIRE-HEP (replaces pubs_generator.py):
  - Queries INSPIRE for the author's publications via inspyhep.
  - Applies max_nauthors=9 by default, then force-includes specific papers
    listed in FORCE_INCLUDE_KEYS regardless of author count.

Step 2 — Enrich each publication with abstract and figure:
  - Downloads arXiv TeX source, extracts abstract and first figure.
  - Falls back to arXiv Atom API for abstracts.
  - Saves figures to files/pub_figs/ and updates YAML frontmatter.

Usage:
    python update_pubs.py              # run both steps
    python update_pubs.py --generate   # step 1 only (generate markdown)
    python update_pubs.py --enrich     # step 2 only (abstracts & figures)

Requirements:
    pip install inspyhep requests PyMuPDF PyYAML
Optional (for EPS figures):
    brew install ghostscript   # or: sudo apt install ghostscript
"""

import argparse
import glob
import gzip
import io
import os
import re
import subprocess
import tarfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
import yaml

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

INSPIRE_AUTHOR = "Matheus.Hostert.1"
MAX_NAUTHORS = 9

# Papers to force-include that are not in the INSPIRE author profile
# (e.g. large-collaboration papers, or papers under a different author ID).
# Each entry is a dict with the same fields as the Jekyll frontmatter.
FORCE_INCLUDE = [
    {
        "title": "Probing Long-Lived Particle Production in Muon Decays at the SNS with a Highly Capable Hydrocarbon Detector",
        "authors": "PROSPECT Collaboration",
        "date": "2026-6-17",
        "venue": "preprint",
        "eprint": "2606.19299",
        "paperurl": "https://arxiv.org/abs/2606.19299",
        "citation": "Probing Long-Lived Particle Production in Muon Decays at the SNS with a Highly Capable Hydrocarbon Detector, PROSPECT Collaboration, arXiv:2606.19299",
        "citation_notitle": "PROSPECT Collaboration, ",
    },
    {
        "title": "First Search for Dark Sector $e^+e^-$ Explanations of the MiniBooNE Anomaly at MicroBooNE",
        "authors": "MicroBooNE Collaboration",
        "date": "2026-3-27",
        "venue": "Phys.Rev.Lett. 136 (2026) 12 121804",
        "eprint": "2502.10900",
        "paperurl": "https://arxiv.org/abs/2502.10900",
        "citation": "First Search for Dark Sector e+e- Explanations of the MiniBooNE Anomaly at MicroBooNE, MicroBooNE Collaboration, Phys.Rev.Lett. 136 (2026) 12 121804",
        "citation_notitle": "MicroBooNE Collaboration, Phys.Rev.Lett. 136 (2026) 12 121804",
    },
    {
        "title": "From oversimplified to overlooked: the case for exploring Rich Dark Sectors",
        "authors": "Asli Abdullahi, Francesco Costa, Andrea Giovanni De Marchi, Alessandro Granelli, Jaime Hoefken-Zink, Matheus Hostert, Michele Lucente, Elina Merkel, Jacopo Nava, Silvia Pascoli, Salvador Rosauro-Alcaraz, Filippo Sala",
        "date": "2025-5-8",
        "venue": "Nucl.Phys.B 1020 (2025) 117148",
        "eprint": "2505.05663",
        "paperurl": "https://arxiv.org/abs/2505.05663",
        "citation": "From oversimplified to overlooked: the case for exploring Rich Dark Sectors, Asli Abdullahi et al., Nucl.Phys.B 1020 (2025) 117148",
        "citation_notitle": "Asli Abdullahi et al., Nucl.Phys.B 1020 (2025) 117148",
    },
]

PUBS_DIR = "_publications"
FIGS_DIR = "files/pub_figs"
HEADERS = {"User-Agent": "Mozilla/5.0 (academic-website/update_pubs.py)"}
SLEEP_BETWEEN = 3  # seconds between papers — be polite to arXiv


# ---------------------------------------------------------------------------
# Step 1: Generate publication markdown from INSPIRE-HEP
# ---------------------------------------------------------------------------


def generate_publications() -> None:
    """Query INSPIRE-HEP and write markdown files into _publications/."""
    from inspyhep import Author

    # Save enrichment data (abstract, fig1) from existing files before
    # regenerating, so we can restore them afterwards.
    preserved: dict[str, dict] = {}
    for fp in glob.glob(f"{PUBS_DIR}/*.md"):
        fm = read_frontmatter(fp)
        eprint = str(fm.get("eprint", "")).strip("'\"")
        if eprint:
            data = {}
            if fm.get("abstract"):
                data["abstract"] = fm["abstract"]
            if fm.get("fig1"):
                data["fig1"] = fm["fig1"]
            if data:
                preserved[eprint] = data

    # Remove old publication files
    for f in glob.glob(f"{PUBS_DIR}/*.md"):
        os.remove(f)

    mh = Author(INSPIRE_AUTHOR)

    # Regular papers (≤ MAX_NAUTHORS authors)
    mh.get_markdown_descriptor(max_nauthors=MAX_NAUTHORS, path=PUBS_DIR)

    # Force-include papers not in the INSPIRE author profile
    for pub in FORCE_INCLUDE:
        slug = re.sub(r"\[.*\]|[^a-zA-Z0-9_-]", "", pub["title"]).replace("--", "-")
        md_filename = f"{pub['date']}-{slug}.md"
        filepath = os.path.join(PUBS_DIR, md_filename)
        if os.path.exists(filepath):
            continue
        lines = [
            "---",
            f"title: '{pub['title']}'",
            f"authors: {pub['authors']}",
            "collection: publication",
            f"permalink: /publication/{pub['date']}-{slug}",
            f"date: {pub['date']}",
            f"venue: {pub['venue']}",
            f"paperurl: '{pub['paperurl']}'",
            f"citation_notitle: '{pub['citation_notitle']}'",
            f"citation: '{pub['citation']}'",
            f"eprint: '{pub['eprint']}'",
            "---",
        ]
        Path(filepath).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"FORCE-INCLUDED {pub['title'][:65]}")

    # Restore preserved abstract/fig1 data
    if preserved:
        for fp in glob.glob(f"{PUBS_DIR}/*.md"):
            fm = read_frontmatter(fp)
            eprint = str(fm.get("eprint", "")).strip("'\"")
            if eprint in preserved:
                for key, val in preserved[eprint].items():
                    if not fm.get(key):
                        if key == "abstract":
                            write_frontmatter_quoted(fp, key, val)
                        else:
                            write_frontmatter_field(fp, key, val)
        print(f"Restored abstract/fig1 for {len(preserved)} publications.")

    # Renumber all publications by date (most recent = 1) so that
    # force-included entries get correct pub_number values.
    all_pubs = sorted(glob.glob(f"{PUBS_DIR}/*.md"), reverse=True)
    for i, fp in enumerate(all_pubs, start=1):
        fm = read_frontmatter(fp)
        if fm.get("pub_number") != i:
            write_frontmatter_field(fp, "pub_number", str(i))

    print(f"\nGenerated {len(all_pubs)} publication files.\n")


# ---------------------------------------------------------------------------
# Step 2: Enrich publications with abstracts & figures
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------


def read_frontmatter(filepath: str) -> dict:
    """Return the YAML frontmatter dict from a Jekyll markdown file."""
    text = Path(filepath).read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\s*\n?", text, re.DOTALL)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}


def write_frontmatter_field(filepath: str, key: str, value: str) -> None:
    """Add or overwrite a single field in the YAML frontmatter block."""
    text = Path(filepath).read_text(encoding="utf-8")
    m = re.match(r"^(---\n)(.*?)(\n---\s*\n?)(.*)", text, re.DOTALL)
    if not m:
        return
    open_delim, fm_block, close_delim, body = m.groups()
    fm_block = re.sub(
        rf"^{re.escape(key)}:.*\n?", "", fm_block, flags=re.MULTILINE
    ).rstrip("\n")
    Path(filepath).write_text(
        f"{open_delim}{fm_block}\n{key}: {value}{close_delim}{body}",
        encoding="utf-8",
    )


def write_frontmatter_quoted(filepath: str, key: str, value: str) -> None:
    """Write a string field that may contain special YAML characters."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    write_frontmatter_field(filepath, key, f'"{escaped}"')


# ---------------------------------------------------------------------------
# arXiv source download & extraction
# ---------------------------------------------------------------------------


def download_source(eprint: str) -> bytes | None:
    """Download arXiv TeX source. Returns raw bytes or None."""
    url = f"https://arxiv.org/e-print/{eprint}"
    print(f"    Downloading source: {url}")
    try:
        resp = requests.get(url, timeout=60, headers=HEADERS)
    except requests.RequestException as exc:
        print(f"    Request failed: {exc}")
        return None
    if resp.status_code != 200:
        print(f"    HTTP {resp.status_code}")
        return None
    return resp.content


def extract_source(raw: bytes) -> dict[str, bytes]:
    """
    Unpack arXiv source bytes into {filename: bytes}.
    Handles tar.gz (multi-file), plain .gz (single .tex), and bare .tex.
    """
    # Try tar (catches .tar, .tar.gz, .tar.bz2, etc.)
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as tar:
            files = {}
            for member in tar.getmembers():
                if member.isfile():
                    fobj = tar.extractfile(member)
                    if fobj:
                        files[member.name] = fobj.read()
            return files
    except tarfile.TarError:
        pass

    # Try plain gzip (single compressed file)
    try:
        data = gzip.decompress(raw)
        return {"main.tex": data}
    except Exception:
        pass

    # Bare TeX
    if raw.lstrip()[:16] in (b"\\documentclass", b"%"):
        return {"main.tex": raw}

    return {}


# ---------------------------------------------------------------------------
# TeX parsing helpers
# ---------------------------------------------------------------------------


def strip_tex_comments(tex: str) -> str:
    """Remove TeX line comments (% … EOL), respecting escaped \\%."""
    return re.sub(r"(?<!\\)%[^\n]*", "", tex)


def expand_inputs(
    tex: str,
    files: dict[str, bytes],
    visited: set[str],
    base_dir: str = "",
) -> str:
    """
    Recursively expand \\input{file} and \\include{file} in place.
    Prevents cycles via the `visited` set.
    """
    incl_re = re.compile(r"\\(?:input|include)\{([^}]+)\}")

    def _replace(m: re.Match) -> str:
        name = m.group(1).strip()
        candidates = [name, name + ".tex"]
        if base_dir:
            candidates += [f"{base_dir}/{name}", f"{base_dir}/{name}.tex"]

        for cand in candidates:
            cand_norm = cand.replace("\\", "/").lstrip("./")
            for key, content in files.items():
                key_norm = key.replace("\\", "/").lstrip("./")
                if key_norm == cand_norm or key_norm.endswith("/" + cand_norm):
                    if key in visited:
                        return ""
                    visited.add(key)
                    sub = content.decode("utf-8", errors="replace")
                    sub_dir = "/".join(key.split("/")[:-1])
                    return expand_inputs(sub, files, visited, sub_dir)
        return m.group(0)

    return incl_re.sub(_replace, tex)


def _is_appendix(key: str) -> bool:
    """Return True if the filename looks like an appendix or wrapper file."""
    name = key.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return "appendix" in name


def find_main_tex(files: dict[str, bytes]) -> tuple[str, str] | tuple[None, None]:
    """
    Find the main .tex file (has \\documentclass). Returns (key, text).

    Priority:
      1. A file literally named 'main.tex' (any directory depth).
      2. Any .tex with \\documentclass, excluding files with 'appendix' in name.
      3. Fallback: largest .tex file, again excluding appendix files.
    """
    # 1. Prefer main.tex
    for key, content in files.items():
        if key.replace("\\", "/").rsplit("/", 1)[-1].lower() == "main.tex":
            try:
                return key, content.decode("utf-8", errors="replace")
            except Exception:
                pass

    # 2. Any .tex with \documentclass, skipping appendix files
    for key, content in files.items():
        if not key.lower().endswith(".tex") or _is_appendix(key):
            continue
        try:
            text = content.decode("utf-8", errors="replace")
        except Exception:
            continue
        if r"\documentclass" in text:
            return key, text

    # 3. Fallback: largest non-appendix .tex file
    tex_files = [
        (k, v)
        for k, v in files.items()
        if k.lower().endswith(".tex") and not _is_appendix(k)
    ]
    if tex_files:
        key, content = max(tex_files, key=lambda x: len(x[1]))
        return key, content.decode("utf-8", errors="replace")

    return None, None


def get_graphic_paths(tex: str) -> list[str]:
    """
    Parse \\graphicspath{{dir1/}{dir2/}} and return the list of path prefixes
    to probe when searching for figure files. Always includes "" (root).
    """
    paths = [""]
    m = re.search(r"\\graphicspath\{((?:\{[^}]*\})+)\}", tex)
    if m:
        for p in re.findall(r"\{([^}]*)\}", m.group(1)):
            p = p.strip("/").replace("\\", "/")
            if p:
                paths.append(p + "/")
    return paths


def find_first_figure_file(tex: str) -> str | None:
    """
    Return the filename argument of the first \\includegraphics inside a
    figure / figure* environment. Falls back to the first \\includegraphics
    anywhere in the document if no figure environment is found.
    """
    tex = strip_tex_comments(tex)

    incl_re = re.compile(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}")
    fig_re = re.compile(
        r"\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}",
        re.DOTALL,
    )

    for fig_m in fig_re.finditer(tex):
        incl_m = incl_re.search(fig_m.group(1))
        if incl_m:
            return incl_m.group(1).strip()

    # Fallback: any \\includegraphics in the document
    incl_m = incl_re.search(tex)
    return incl_m.group(1).strip() if incl_m else None


def extract_abstract_from_tex(full_tex: str) -> str | None:
    """
    Extract \\begin{abstract}...\\end{abstract}, preserving math environments
    intact for MathJax while stripping non-math TeX markup.
    """
    tex = strip_tex_comments(full_tex)
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex, re.DOTALL)
    if not m:
        return None
    raw = m.group(1).strip()

    # --- Step 1: protect math environments with placeholders ---
    math_store: list[str] = []

    def _protect(m: re.Match) -> str:
        math_store.append(m.group(0))
        return f"\x00M{len(math_store) - 1}\x00"

    # Display math first (longer patterns take priority)
    raw = re.sub(r"\$\$.*?\$\$", _protect, raw, flags=re.DOTALL)
    raw = re.sub(r"\\\[.*?\\\]", _protect, raw, flags=re.DOTALL)
    raw = re.sub(r"\\\(.*?\\\)", _protect, raw, flags=re.DOTALL)
    # Inline $...$ (non-greedy, single line)
    raw = re.sub(r"\$(?!\$).+?\$", _protect, raw)

    # --- Step 2: strip non-math TeX from the remaining text ---

    # Text-formatting commands: strip command, keep argument
    for cmd in (
        "emph",
        "textbf",
        "textit",
        "text",
        "textrm",
        "textsf",
        "texttt",
        "underline",
        "mbox",
        "hbox",
    ):
        raw = re.sub(rf"\\{cmd}\{{([^{{}}]*)\}}", r"\1", raw)

    # Remove citations, references, labels, footnotes entirely
    raw = re.sub(r"\\cite(?:p|t|alt|alp|num)?\*?\{[^}]*\}", "", raw)
    raw = re.sub(r"\\ref\{[^}]*\}", "", raw)
    raw = re.sub(r"\\label\{[^}]*\}", "", raw)
    raw = re.sub(r"\\footnote\{[^}]*\}", "", raw)

    # Strip remaining single-argument commands, keeping the argument
    raw = re.sub(r"\\[a-zA-Z]+\{([^{}]*)\}", r"\1", raw)
    # Strip bare TeX commands
    raw = re.sub(r"\\[a-zA-Z]+\b\*?", " ", raw)
    # Strip leftover braces
    raw = raw.replace("{", "").replace("}", "")

    # --- Step 3: restore math placeholders ---
    for i, math in enumerate(math_store):
        raw = raw.replace(f"\x00M{i}\x00", math)

    # Normalize whitespace
    raw = " ".join(raw.split())
    return raw if raw else None


# ---------------------------------------------------------------------------
# File lookup in the tarball
# ---------------------------------------------------------------------------

# Extensions to probe when the \\includegraphics path has no extension.
FIGURE_EXTS = [
    "",
    ".pdf",
    ".PDF",
    ".eps",
    ".EPS",
    ".png",
    ".PNG",
    ".jpg",
    ".JPG",
    ".jpeg",
    ".JPEG",
]


def locate_file(
    name: str,
    files: dict[str, bytes],
    graphic_paths: list[str],
) -> tuple[str, bytes, str] | None:
    """
    Find `name` (from \\includegraphics{name}) in the tarball dict.
    Returns (tarball_key, file_bytes, extension) or None.
    """
    name = name.replace("\\", "/").strip()

    candidates: list[str] = []
    for gpath in graphic_paths:
        for ext in FIGURE_EXTS:
            candidates.append((gpath + name + ext).lstrip("./"))
    basename = name.rsplit("/", 1)[-1]
    for ext in FIGURE_EXTS:
        candidates.append(basename + ext)

    norm_to_orig: dict[str, str] = {k.replace("\\", "/").lstrip("./"): k for k in files}

    for cand in candidates:
        cand_norm = cand.replace("\\", "/").lstrip("./")
        if cand_norm in norm_to_orig:
            orig = norm_to_orig[cand_norm]
            ext = orig.rsplit(".", 1)[-1].lower() if "." in orig else "bin"
            return orig, files[orig], ext
        for norm_k, orig_k in norm_to_orig.items():
            if norm_k.endswith("/" + cand_norm):
                ext = orig_k.rsplit(".", 1)[-1].lower() if "." in orig_k else "bin"
                return orig_k, files[orig_k], ext

    return None


# ---------------------------------------------------------------------------
# Image conversion
# ---------------------------------------------------------------------------


def pdf_to_png(pdf_bytes: bytes) -> tuple[bytes, str]:
    """Render the first page of a PDF to PNG using PyMuPDF."""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))  # 2× resolution
    return pix.tobytes("png"), "png"


def eps_to_png(eps_bytes: bytes) -> tuple[bytes, str] | None:
    """Convert EPS to PNG via Ghostscript subprocess (if gs is installed)."""
    try:
        result = subprocess.run(
            [
                "gs",
                "-dNOPAUSE",
                "-dBATCH",
                "-dSAFER",
                "-sDEVICE=pngalpha",
                "-r150",
                "-sOutputFile=-",
                "-",
            ],
            input=eps_bytes,
            capture_output=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout, "png"
    except FileNotFoundError:
        print("      Ghostscript (gs) not found — skipping EPS conversion")
    except subprocess.TimeoutExpired:
        print("      Ghostscript timed out")
    return None


def convert_to_png(data: bytes, ext: str) -> tuple[bytes, str] | None:
    """
    Convert image data to a web-safe format.
    Returns (bytes, ext) or None on failure.
    """
    ext = ext.lower()
    if ext in ("png", "jpg", "jpeg", "gif", "webp"):
        return data, ext
    if ext == "pdf":
        try:
            return pdf_to_png(data)
        except Exception as exc:
            print(f"      PDF→PNG failed: {exc}")
            return None
    if ext == "eps":
        result = eps_to_png(data)
        if result:
            return result
        return None
    print(f"      Unknown format: .{ext} — skipping")
    return None


# ---------------------------------------------------------------------------
# Figure extraction from parsed TeX
# ---------------------------------------------------------------------------


def get_fig1_from_tex(
    full_tex: str, files: dict[str, bytes]
) -> tuple[bytes, str] | None:
    """Extract and convert the first figure from an already-expanded TeX."""
    graphic_paths = get_graphic_paths(full_tex)
    fig_name = find_first_figure_file(full_tex)

    if not fig_name:
        print("    No \\includegraphics found in source")
        return None

    print(f"    First figure: {fig_name!r}")

    found = locate_file(fig_name, files, graphic_paths)
    if not found:
        print(f"    Could not find {fig_name!r} in tarball")
        return None

    tar_key, data, ext = found
    print(f"    Located: {tar_key} (.{ext}, {len(data):,} bytes)")
    return convert_to_png(data, ext)


# ---------------------------------------------------------------------------
# arXiv Atom API fallback for abstract
# ---------------------------------------------------------------------------

ARXIV_API = "https://export.arxiv.org/api/query"
ATOM_NS = "http://www.w3.org/2005/Atom"


def fetch_abstract_api(eprint: str) -> str | None:
    """Return the abstract text from the arXiv Atom API, or None on failure."""
    try:
        resp = requests.get(
            ARXIV_API, params={"id_list": eprint}, timeout=20, headers=HEADERS
        )
        if resp.status_code != 200:
            return None
        root = ET.fromstring(resp.text)
        entry = root.find(f"{{{ATOM_NS}}}entry")
        if entry is None:
            return None
        summary = entry.find(f"{{{ATOM_NS}}}summary")
        if summary is None or not summary.text:
            return None
        return " ".join(summary.text.split())
    except Exception as exc:
        print(f"    Abstract API fetch failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def enrich_publications() -> None:
    """Download abstracts and figures for all publications in _publications/."""
    os.makedirs(FIGS_DIR, exist_ok=True)

    pub_files = sorted(glob.glob(f"{PUBS_DIR}/*.md"))
    print(f"Found {len(pub_files)} publications\n")

    fig_ok = fig_skip = fig_fail = 0
    abs_ok = abs_skip = abs_fail = 0

    for filepath in pub_files:
        fm = read_frontmatter(filepath)
        eprint = str(fm.get("eprint", "")).strip("'\"")
        title = str(fm.get("title", "Unknown"))[:65]

        if not eprint:
            print(f"SKIP (no eprint): {title}")
            fig_skip += 1
            abs_skip += 1
            continue

        print(f"\n[{eprint}] {title}")

        need_abstract = not fm.get("abstract")
        need_figure = not fm.get("fig1")

        # If fig1 is in frontmatter, verify the file actually exists on disk
        if not need_figure:
            fig1_path = fm.get("fig1", "").lstrip("/")
            if fig1_path and not Path(fig1_path).exists():
                print("  Figure:   frontmatter set but file missing — re-downloading")
                need_figure = True

        # Check if figure file already exists on disk (frontmatter not yet set)
        if need_figure and not fm.get("fig1"):
            existing = [
                p
                for p in glob.glob(f"{FIGS_DIR}/{eprint}.*")
                if p.rsplit(".", 1)[-1].lower() in ("png", "jpg", "jpeg", "gif", "webp")
            ]
            if existing:
                rel = "/" + existing[0].replace("\\", "/")
                print("  Figure:   file exists — updating frontmatter only")
                write_frontmatter_field(filepath, "fig1", rel)
                fig_skip += 1
                need_figure = False

        if not need_abstract and not need_figure:
            print("  Abstract: already in frontmatter — skipping")
            print("  Figure:   already in frontmatter — skipping")
            abs_skip += 1
            fig_skip += 1
            continue

        if need_abstract:
            print("  Abstract: not in frontmatter")
        if need_figure:
            print("  Figure:   not in frontmatter")

        # Download source once for both abstract and figure
        full_tex = None
        files = None

        print("  Downloading TeX source...")
        raw = download_source(eprint)
        if raw:
            files = extract_source(raw)
            if files:
                print(f"    {len(files)} file(s) in source archive")
                main_key, main_tex = find_main_tex(files)
                if main_tex:
                    print(f"    Main TeX: {main_key}")
                    base_dir = "/".join(main_key.split("/")[:-1])
                    full_tex = expand_inputs(
                        main_tex, files, visited={main_key}, base_dir=base_dir
                    )
                else:
                    print("    No .tex file found in source")
            else:
                print("    Could not unpack source archive")

        # ---- Abstract -------------------------------------------------------
        if need_abstract:
            abstract = None

            if full_tex:
                abstract = extract_abstract_from_tex(full_tex)
                if abstract:
                    print(f"  ✓ Abstract extracted from TeX ({len(abstract)} chars)")

            if not abstract:
                print("  Trying arXiv API for abstract...")
                abstract = fetch_abstract_api(eprint)
                time.sleep(1)
                if abstract:
                    print(f"  ✓ Abstract from API ({len(abstract)} chars)")

            if abstract:
                write_frontmatter_quoted(filepath, "abstract", abstract)
                abs_ok += 1
            else:
                print("  ✗ Abstract not found")
                abs_fail += 1

        else:
            print("  Abstract: already in frontmatter — skipping")
            abs_skip += 1

        # ---- Figure ---------------------------------------------------------
        if need_figure:
            if full_tex and files:
                result = get_fig1_from_tex(full_tex, files)
            else:
                result = None

            if result:
                data, ext = result
                if ext == "jpeg":
                    ext = "jpg"
                out_path = f"{FIGS_DIR}/{eprint}.{ext}"
                Path(out_path).write_bytes(data)
                rel = "/" + out_path.replace("\\", "/")
                write_frontmatter_field(filepath, "fig1", rel)
                print(f"  ✓ Figure saved → {out_path}")
                fig_ok += 1
            else:
                print("  ✗ Figure not found")
                fig_fail += 1
        else:
            fig_skip += 1

        time.sleep(SLEEP_BETWEEN)

    print(f"\nAbstracts: {abs_ok} fetched, {abs_skip} skipped, {abs_fail} failed")
    print(f"Figures:   {fig_ok} downloaded, {fig_skip} skipped, {fig_fail} failed")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate and enrich academic publication pages."
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Only regenerate markdown from INSPIRE-HEP (step 1).",
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="Only enrich existing markdown with abstracts & figures (step 2).",
    )
    args = parser.parse_args()

    run_all = not args.generate and not args.enrich

    if run_all or args.generate:
        generate_publications()

    if run_all or args.enrich:
        enrich_publications()


if __name__ == "__main__":
    main()
