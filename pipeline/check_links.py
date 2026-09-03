"""Fail the build if any generated page points at a path that will 404 in production.

    python3 pipeline/check_links.py

The site is served from a subpath (spercle.github.io/fort.mouse/). Hugo's relURL
handles anything written in a template, but SVG produced by the Python pipeline is
inlined verbatim — so an absolute "/loop-base/x.jpg" in there resolves off the site
root and silently 404s. That shipped once, on all 21 aerial maps.

This walks the built output and checks that every local reference either carries the
baseURL path or is genuinely relative, and that the file it points at exists.
"""

import os
import re
import sys
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(ROOT, "public")

REF = re.compile(r'(?:href|src)=["\']?(/[^"\'\s>]+)', re.I)


def base_path():
    for line in open(os.path.join(ROOT, "hugo.toml")):
        if line.strip().startswith("baseURL"):
            return urlparse(line.split("=", 1)[1].strip().strip('"')).path.rstrip("/")
    return ""


def check_content():
    """References resolving is not the same as content being there.

    A template bug once replaced an entire inlined SVG with a short string. Every
    reference on the page still resolved, because there were no longer any to
    break, and this checker reported success. So also assert the things that are
    supposed to be on a page actually are.
    """
    import glob
    problems = []
    for path in sorted(glob.glob(os.path.join(PUBLIC, "loop", "*", "index.html"))):
        loop = os.path.basename(os.path.dirname(path))
        html = open(path, encoding="utf-8", errors="ignore").read()
        has_aerial_pane = "data-view=aerial" in html or 'data-view="aerial"' in html
        if has_aerial_pane and html.count("<svg") < 3:
            problems.append(f"loop {loop}: aerial pane present but only "
                            f"{html.count('<svg')} svg element(s) — expected map, "
                            f"aerial and sign")
        if "loop-map" in html and "<svg" not in html:
            problems.append(f"loop {loop}: map container with no svg inside")
    return problems


def main():
    if not os.path.isdir(PUBLIC):
        sys.exit("no public/ — run ./build.sh first")
    base = base_path()
    bad, checked = {}, 0

    for dirpath, _, files in os.walk(PUBLIC):
        for fn in files:
            if not fn.endswith(".html"):
                continue
            path = os.path.join(dirpath, fn)
            page = "/" + os.path.relpath(path, PUBLIC)
            for m in REF.finditer(open(path, encoding="utf-8", errors="ignore").read()):
                url = m.group(1)
                checked += 1
                if base and not url.startswith(base + "/"):
                    bad.setdefault(url, set()).add(page)
                    continue
                rel = url[len(base):].lstrip("/").split("?")[0].split("#")[0]
                if rel and not os.path.exists(os.path.join(PUBLIC, rel)):
                    bad.setdefault(url, set()).add(page)

    content = check_content()
    print(f"  {checked} local reference(s) checked across the built site")
    if content:
        print(f"\n  {len(content)} content problem(s):")
        for c in content:
            print(f"    {c}")
    if not bad and not content:
        print("  all resolve, and every loop map has its content")
        return
    if content and not bad:
        sys.exit(1)
    print(f"\n  {len(bad)} broken reference(s):")
    for url, pages in sorted(bad.items())[:20]:
        where = sorted(pages)[0] + (f" (+{len(pages)-1} more)" if len(pages) > 1 else "")
        why = "missing baseURL path" if base and not url.startswith(base + "/") \
              else "file not in public/"
        print(f"    {url}   {why}   e.g. {where}")
    sys.exit(1)


if __name__ == "__main__":
    main()
