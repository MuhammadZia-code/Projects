#!/usr/bin/env python3
"""Parse the TPL directory: folder titles + per-case descriptions from .doc files."""
import os
import re
import sys
import glob

# Location of the extracted TPL directory. Override with the TPL_DIR env var;
# defaults to a "TPL" folder next to the repository root.
TPL = os.environ.get(
    "TPL_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "TPL"),
)

# An entry line in a .doc: starts (after optional ws) with a case code token
# like GMASP001 / gmgmc001 / GMGHG025, optional extension, then -- or : then text.
ENTRY_RE = re.compile(
    r'^\s*(?:\d+\.\s*)?'            # optional leading list marker e.g. "1."
    r'([A-Za-z]{2,}\d{3,}[A-Za-z0-9_]*)'  # case code token (underscores allowed)
    r'(\.[A-Za-z0-9]+)?'           # optional extension e.g. .DAT / .OBREC
    r'\s*[-–—:]+\s+'      # separator: - / en-dash / em-dash / colon run
    r'(.*)$')


def read_text(path):
    with open(path, 'rb') as f:
        raw = f.read()
    # .doc files here are plain text, cp1252-ish (en-dash bytes). Decode leniently.
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('cp1252', errors='replace')


def parse_doc(path):
    """Return (title, {basecode_lower: description})."""
    text = read_text(path)
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    # Title = first non-empty line that is not a rule of dashes.
    title = None
    idx = 0
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s:
            continue
        if set(s) <= {'-', '=', '*'}:
            continue
        title = s
        idx = i
        break
    descs = {}
    current_key = None
    for ln in lines[idx + 1:]:
        m = ENTRY_RE.match(ln)
        if m:
            token = m.group(1)
            desc = m.group(3).strip()
            key = token.lower()
            # Only keep first separator-split; collapse internal whitespace.
            descs[key] = desc
            current_key = key
        else:
            # continuation line? indented, non-empty, belongs to current entry
            s = ln.strip()
            if s and current_key and ln[:1] in (' ', '\t'):
                # avoid swallowing section headers made of dashes
                if set(s) <= {'-', '=', '*'}:
                    continue
                descs[current_key] = (descs[current_key] + ' ' + s).strip()
            else:
                current_key = None
    return title or os.path.basename(path), descs


def build_model():
    folders = []
    for d in sorted(os.listdir(TPL)):
        fpath = os.path.join(TPL, d)
        if not os.path.isdir(fpath):
            continue
        dats = sorted(glob.glob(os.path.join(fpath, '*.dat')) +
                      glob.glob(os.path.join(fpath, '*.DAT')),
                      key=lambda p: os.path.basename(p).lower())
        if not dats:
            continue
        docs = glob.glob(os.path.join(fpath, '*000.doc')) or \
            glob.glob(os.path.join(fpath, '*.doc'))
        if docs:
            title, descs = parse_doc(docs[0])
        else:
            title, descs = d.upper(), {}
        cases = []
        for dp in dats:
            base = os.path.basename(dp)
            key = os.path.splitext(base)[0].lower()
            cases.append({
                'path': dp,
                'name': base,
                'key': key,
                'desc': descs.get(key, ''),
            })
        folders.append({
            'code': d,
            'title': title,
            'has_doc': bool(docs),
            'cases': cases,
        })
    return folders


if __name__ == '__main__':
    folders = build_model()
    total_cases = 0
    missing = 0
    print(f"{'CODE':6} {'#DAT':>5}  DOC?  TITLE")
    print('-' * 70)
    for fo in folders:
        n = len(fo['cases'])
        total_cases += n
        miss = sum(1 for c in fo['cases'] if not c['desc'])
        missing += miss
        print(f"{fo['code']:6} {n:>5}  {'Y' if fo['has_doc'] else 'N':>3}   {fo['title']}  (no-desc: {miss})")
    print('-' * 70)
    print(f"folders={len(folders)}  total .dat cases={total_cases}  missing-desc={missing}")
    # show a few sample descriptions
    print("\nSample cases (first folder):")
    for c in folders[0]['cases'][:5]:
        print(f"  {c['name']:16} -> {c['desc'][:70]}")
    # Show any folders with many missing descriptions
    print("\nCases missing descriptions (sample up to 20):")
    shown = 0
    for fo in folders:
        for c in fo['cases']:
            if not c['desc'] and shown < 20:
                print(f"  {fo['code']}/{c['name']}")
                shown += 1
