"""Measured pre-submission checks for a PromptWars repo, grouped by the seven scored dimensions.

Run from the repo root:  .venv/bin/python .agents/skills/pw-score/score.py [LIVE_URL]
Read-only: it never edits files. Optional tools (ruff, bandit, pip-audit, pytest-cov) are used if installed.
It never calls the AI route, so it costs no Gemini quota.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path.cwd()
VENV_BIN = ROOT / ".venv" / "bin"
SKIP_DIRS = {".venv", ".git", "__pycache__", ".pytest_cache", "node_modules", ".agents", ".claude", "htmlcov"}
results: list[tuple[str, str, str]] = []


def add(status: str, dim: str, msg: str) -> None:
    results.append((status, dim, msg))


def tool(name: str) -> str | None:
    p = VENV_BIN / name
    return str(p) if p.exists() else shutil.which(name)


def run(cmd: list[str], timeout: int = 300) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "timed out"


def files(*globs: str) -> list[Path]:
    out = []
    for g in globs:
        for p in ROOT.rglob(g):
            if p.is_file() and not (set(p.relative_to(ROOT).parts) & SKIP_DIRS):
                out.append(p)
    return sorted(set(out))


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def tracked_files() -> list[Path]:
    if (ROOT / ".git").exists():
        code, out = run(["git", "ls-files"])
        if code == 0:
            return [ROOT / line for line in out.splitlines() if (ROOT / line).is_file()]
    return files("*")


# ---------- Security ----------
def security() -> None:
    d = "Security"
    hits = []
    for p in tracked_files() + files("*.py", "*.js", "*.html", "*.md", "*.json", "*.yaml", "*.toml", "*.txt", "*.env"):
        for i, line in enumerate(read(p).splitlines(), 1):
            if re.search(r"AIza[0-9A-Za-z_\-]{20,}", line):
                hits.append(f"{rel(p)}:{i}")
    hits = sorted(set(hits))
    add("FAIL" if hits else "PASS", d, "API key found: " + ", ".join(hits) if hits else "No Google API keys in files")

    if (ROOT / ".git").exists():
        _, out = run(["git", "ls-files"])
        env = [f for f in out.splitlines() if re.search(r"(^|/)\.env($|\.)", f) and not f.endswith(".example")]
        add("FAIL" if env else "PASS", d, f".env committed: {env}" if env else "No .env file committed")

    dbg = [f"{rel(p)}:{i}" for p in files("*.py") for i, l in enumerate(read(p).splitlines(), 1)
           if re.search(r"debug\s*=\s*True", l)]
    add("FAIL" if dbg else "PASS", d, f"debug=True at {', '.join(dbg)}" if dbg else "Debug mode off")

    inner = [f"{rel(p)}:{i}" for p in files("*.js") for i, l in enumerate(read(p).splitlines(), 1)
             if "innerHTML" in l or "outerHTML" in l or "insertAdjacentHTML" in l]
    add("WARN" if inner else "PASS", d, f"HTML injection risk (use textContent): {', '.join(inner)}" if inner else "No innerHTML in JS")

    unsafe = [f"{rel(p)}:{i}" for p in files("*.html") for i, l in enumerate(read(p).splitlines(), 1) if "|safe" in l.replace(" ", "")]
    add("WARN" if unsafe else "PASS", d, f"Jinja |safe used: {', '.join(unsafe)}" if unsafe else "No |safe filters in templates")

    main = read(ROOT / "main.py")
    for label, pat in [("MAX_CONTENT_LENGTH", "MAX_CONTENT_LENGTH"), ("rate limiting", r"rate|limit|429")]:
        add("PASS" if re.search(pat, main, re.I) else "WARN", d, f"{label} {'found' if re.search(pat, main, re.I) else 'not found'} in main.py")

    bandit = tool("bandit")
    if bandit:
        code, out = run([bandit, "-q", "-r", ".", "-x", "./.venv,./tests,./.agents", "-ll", "-f", "txt"])
        issues = re.findall(r">> Issue: \[(\w+):(\w+)\] (.+)", out)
        add("WARN" if issues else "PASS", d, "bandit (medium+): " + ("; ".join(f"{a}: {c}" for a, _, c in issues[:5]) if issues else "no issues"))
    else:
        add("SKIP", d, "bandit not installed")

    audit = tool("pip-audit")
    if audit and (ROOT / "requirements.txt").exists():
        code, out = run([audit, "-r", "requirements.txt", "--no-deps", "--disable-pip", "--progress-spinner", "off"], timeout=180)
        if "No known vulnerabilities" in out:
            add("PASS", d, "pip-audit: no known vulnerabilities in requirements.txt")
        elif code == 124 or "error" in out.lower() and "vulnerab" not in out.lower():
            add("SKIP", d, "pip-audit could not run (network?)")
        else:
            add("WARN", d, "pip-audit: " + " | ".join(out.splitlines()[:4]))
    else:
        add("SKIP", d, "pip-audit not installed")


# ---------- Code quality ----------
def code_quality() -> None:
    d = "Code quality"
    ruff = tool("ruff")
    if ruff:
        code, out = run([ruff, "check", ".", "--exclude", ".venv,.agents,.claude", "--output-format", "concise"])
        n = len([l for l in out.splitlines() if re.match(r".+:\d+:\d+: ", l)])
        add("PASS" if code == 0 else "WARN", d, "ruff: clean" if code == 0 else f"ruff: {n} issues, e.g. " + " | ".join(out.splitlines()[:3]))
    else:
        add("SKIP", d, "ruff not installed")

    req = ROOT / "requirements.txt"
    if req.exists():
        loose = [l for l in read(req).splitlines() if l.strip() and not l.startswith("#") and "==" not in l]
        add("WARN" if loose else "PASS", d, f"Unpinned requirements: {loose}" if loose else "requirements.txt fully pinned")
    else:
        add("FAIL", d, "requirements.txt missing")

    py = [p for p in files("*.py") if "tests" not in p.parts]
    if py:
        funcs = sum(len(re.findall(r"^\s*def \w+\(", read(p), re.M)) for p in py)
        hinted = sum(len(re.findall(r"^\s*def \w+\(.*\)\s*->", read(p), re.M)) for p in py)
        pct = round(100 * hinted / funcs) if funcs else 100
        add("PASS" if pct >= 80 else "WARN", d, f"Return type hints on {hinted}/{funcs} functions ({pct}%)")
        big = [f"{rel(p)} ({len(read(p).splitlines())} lines)" for p in py if len(read(p).splitlines()) > 300]
        add("WARN" if big else "PASS", d, f"Large modules: {', '.join(big)}" if big else "All modules under 300 lines")
        todo = [f"{rel(p)}:{i}" for p in py for i, l in enumerate(read(p).splitlines(), 1) if re.search(r"\b(TODO|FIXME|print\()", l)]
        add("WARN" if todo else "PASS", d, f"TODO/print left in: {', '.join(todo[:6])}" if todo else "No TODOs or stray prints")


# ---------- Testing ----------
def testing() -> None:
    d = "Testing"
    tests = files("test_*.py", "*_test.py")
    if not tests:
        add("FAIL", d, "No tests found")
        return
    pytest = tool("pytest")
    if not pytest:
        add("FAIL", d, "pytest not installed")
        return
    cov = (VENV_BIN / "python").exists() and run([str(VENV_BIN / "python"), "-c", "import pytest_cov"])[0] == 0
    cmd = [pytest, "-q", "-p", "no:cacheprovider"]
    if cov:
        mods = sorted({p.stem for p in files("*.py") if p.parent == ROOT})
        cmd += [f"--cov={m}" for m in mods] + ["--cov-report=term"]
    code, out = run(cmd)
    summary = next((l for l in reversed(out.splitlines()) if re.search(r"passed|failed|error", l)), out[-200:])
    add("PASS" if code == 0 else "FAIL", d, f"pytest: {summary.strip('= ')}")
    add("PASS" if len(tests) else "WARN", d, f"{sum(len(re.findall(r'^def test_', read(p), re.M)) for p in tests)} tests in {len(tests)} files")
    if cov:
        m = re.search(r"^TOTAL\s+\d+\s+\d+\s+(\d+)%", out, re.M)
        if m:
            pct = int(m.group(1))
            add("PASS" if pct >= 70 else "WARN", d, f"Coverage {pct}% (aim for 70%+)")
    else:
        add("SKIP", d, "pytest-cov not installed, so no coverage figure")
    for name in ["logic.py", "validation.py", "ai.py"]:
        if (ROOT / name).exists():
            stem = name[:-3]
            covered = any(re.search(rf"\b{stem}\b", read(t)) for t in tests)
            add("PASS" if covered else "WARN", d, f"{name} {'is' if covered else 'is NOT'} covered by a test file")


# ---------- Efficiency ----------
def efficiency() -> None:
    d = "Efficiency"
    tracked = tracked_files()
    size = sum(p.stat().st_size for p in tracked)
    mb = size / 1_048_576
    add("FAIL" if mb >= 10 else ("WARN" if mb >= 5 else "PASS"), d, f"Repo size {mb:.2f} MB (limit is under 10 MB)")
    big = [f"{rel(p)} ({p.stat().st_size // 1024} KB)" for p in tracked if p.stat().st_size > 200_000]
    add("WARN" if big else "PASS", d, f"Files over 200 KB: {', '.join(big)}" if big else "No files over 200 KB")
    ai = read(ROOT / "ai.py")
    if ai:
        for label, pat in [("Cache for AI calls", r"lru_cache|cache"), ("Timeout on AI calls", r"timeout"), ("Fallback model", r"fallback")]:
            ok = re.search(pat, ai, re.I)
            add("PASS" if ok else "WARN", d, f"{label} {'found' if ok else 'not found'} in ai.py")
        canned = re.search(r"demo[_ ]?mode|\?demo|showing an example|STUB|hard.?coded", ai, re.I)
        add("FAIL" if canned else "PASS", "Problem alignment", "Canned or demo AI output left in ai.py (reads as fake data; disqualifies)" if canned else "No canned or demo AI output in ai.py")
    else:
        add("WARN", d, "ai.py not found, so cache, timeout and fallback were not checked")


# ---------- Accessibility (static; the browser scan is separate) ----------
def accessibility() -> None:
    d = "Accessibility"
    html = files("*.html")
    if not html:
        add("FAIL", d, "No templates found")
        return
    allh = "\n".join(read(p) for p in html)
    checks = [
        ("lang attribute on <html>", r"<html[^>]*\blang="),
        ("<main> landmark", r"<main\b"),
        ("<header> landmark", r"<header\b"),
        ("<footer> landmark", r"<footer\b"),
        ("Skip link", r'href="#(main|content)'),
        ("aria-live region", r"aria-live="),
        ("aria-describedby on inputs", r"aria-describedby="),
        ("viewport meta", r'name="viewport"'),
    ]
    for label, pat in checks:
        ok = re.search(pat, allh, re.I)
        add("PASS" if ok else "WARN", d, f"{label}: {'yes' if ok else 'missing'}")
    for p in html:
        t = read(p)
        h1 = len(re.findall(r"<h1\b", t, re.I))
        if h1 > 1:
            add("WARN", d, f"{rel(p)} has {h1} h1 headings (use one)")
        fields = re.findall(r'<(input|textarea|select)\b([^>]*)>', t, re.I)
        fields = [a for tag, a in fields if not re.search(r'type="(hidden|submit|button)"', a)]
        ids = [re.search(r'id="([^"]+)"', a).group(1) for a in fields if re.search(r'id="([^"]+)"', a)]
        unlabelled = [i for i in ids if not re.search(rf'for="{re.escape(i)}"', t)]
        no_id = [a for a in fields if 'id="' not in a and "aria-label" not in a]
        if unlabelled or no_id:
            add("WARN", d, f"{rel(p)}: fields without a visible label: {unlabelled + ['(no id)'] * len(no_id)}")
        imgs = [m for m in re.findall(r"<img\b[^>]*>", t, re.I) if "alt=" not in m]
        if imgs:
            add("WARN", d, f"{rel(p)}: {len(imgs)} images without alt")
        if re.search(r"<div[^>]*onclick", t, re.I):
            add("WARN", d, f"{rel(p)}: clickable div (use a button)")
    css = "\n".join(read(p) for p in files("*.css"))
    add("PASS" if "prefers-reduced-motion" in css else "WARN", d, f"prefers-reduced-motion {'handled' if 'prefers-reduced-motion' in css else 'missing'} in CSS")
    kill = re.search(r"outline\s*:\s*(none|0)", css) and not re.search(r":focus-visible|:focus\b", css)
    add("WARN" if kill else "PASS", d, "Focus outline removed with no :focus style" if kill else "Focus styles present")


# ---------- Google services + problem alignment (README) ----------
def readme_checks() -> None:
    rd = read(ROOT / "README.md")
    d = "Google services"
    if not rd:
        add("FAIL", d, "README.md missing")
        add("FAIL", "Problem alignment", "README.md missing")
        return
    for svc, pat in [("Gemini", r"gemini"), ("Cloud Run", r"cloud run"), ("Secret Manager", r"secret manager"), ("Cloud Logging", r"cloud logging|logging")]:
        ok = re.search(pat, rd, re.I)
        add("PASS" if ok else "WARN", d, f"{svc} {'named' if ok else 'not named'} in README")
    used_sdk = any("google-genai" in read(p) or "from google import genai" in read(p) for p in files("*.py", "requirements.txt"))
    add("PASS" if used_sdk else "FAIL", d, "google-genai SDK used in code" if used_sdk else "google-genai SDK not found in code")

    d = "Problem alignment"
    brief = read(ROOT / "BRIEF.md")
    m = re.search(r"## Challenge[^\n]*\n(.*?)\n## ", brief, re.S)
    challenge = re.sub(r"[>*_`]", "", m.group(1)).strip() if m else ""
    challenge = "\n".join(l for l in challenge.splitlines() if l.strip() and not l.lower().startswith("practice brief"))
    if challenge:
        words = re.findall(r"[a-z]{5,}", challenge.lower())
        key = sorted(set(words), key=words.index)
        missing = [w for w in key if w not in rd.lower()]
        pct = round(100 * (len(key) - len(missing)) / len(key)) if key else 0
        add("PASS" if pct >= 70 else "WARN", d, f"README uses {pct}% of the brief's key words" + (f"; missing: {', '.join(missing[:12])}" if missing else ""))
        snippet = " ".join(challenge.split()[:8]).lower()
        add("PASS" if snippet in " ".join(rd.lower().split()) else "WARN", d, "README quotes the challenge word for word" if snippet in " ".join(rd.lower().split()) else "README does not quote the challenge word for word")
    else:
        add("SKIP", d, "BRIEF.md has no challenge text to compare")
    add("PASS" if "run.app" in rd else "WARN", d, "Live Cloud Run link in README" if "run.app" in rd else "No run.app link in README")
    add("PASS" if (ROOT / "docs" / "prompts.md").exists() else "WARN", d, "docs/prompts.md present" if (ROOT / "docs" / "prompts.md").exists() else "docs/prompts.md missing")


# ---------- Live URL ----------
def live(url: str) -> None:
    d = "Live"
    url = url.rstrip("/")

    def get(path: str) -> tuple[int, dict, float]:
        req = urllib.request.Request(url + path, headers={"User-Agent": "pw-score"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                r.read()
                return r.status, {k.lower(): v for k, v in r.headers.items()}, time.time() - t0
        except urllib.error.HTTPError as e:
            return e.code, {k.lower(): v for k, v in e.headers.items()}, time.time() - t0
        except Exception as e:  # noqa: BLE001
            return 0, {"error": str(e)}, time.time() - t0

    s, _, _ = get("/health")
    add("PASS" if s == 200 else "FAIL", d, f"/health returned {s}")
    get("/")  # warm the instance so the timing below is not a cold start
    s, h, t = get("/")
    add("PASS" if s == 200 else "FAIL", d, f"Home page returned {s}")
    add("PASS" if t < 2 else "WARN", "Efficiency", f"Home page served in {t:.2f}s (warm)")
    for hdr in ["content-security-policy", "x-content-type-options", "referrer-policy", "x-frame-options"]:
        add("PASS" if hdr in h else "FAIL", "Security", f"Live header {hdr}: {'present' if hdr in h else 'MISSING'}")
    s, _, _ = get("/this-page-does-not-exist")
    add("PASS" if s == 404 else "WARN", d, f"Unknown page returned {s} (want a clean 404)")


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else ""
    for fn in (security, code_quality, testing, efficiency, accessibility, readme_checks):
        fn()
    if url:
        live(url)
    else:
        add("SKIP", "Live", "No live URL given")

    order = ["Problem alignment", "Code quality", "Security", "Efficiency", "Testing", "Accessibility", "Google services", "Live"]
    icon = {"PASS": "ok  ", "WARN": "WARN", "FAIL": "FAIL", "SKIP": "skip"}
    for dim in order:
        rows = [r for r in results if r[1] == dim]
        if not rows:
            continue
        print(f"\n## {dim}")
        for status, _, msg in sorted(rows, key=lambda r: ["FAIL", "WARN", "PASS", "SKIP"].index(r[0])):
            print(f"  {icon[status]}  {msg}")
    counts = {k: sum(1 for r in results if r[0] == k) for k in ["FAIL", "WARN", "PASS", "SKIP"]}
    print(f"\nTotal: {counts['FAIL']} fail, {counts['WARN']} warn, {counts['PASS']} pass, {counts['SKIP']} skipped")


if __name__ == "__main__":
    main()
