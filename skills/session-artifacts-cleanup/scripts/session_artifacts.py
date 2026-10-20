#!/usr/bin/env python3
"""
Inventory the files a directory holds against what past Claude Code sessions
did to them, then archive (never delete) the ones the user picks.

  inventory <dir> [--recursive] [--stale-days N] [--json]
  archive   <dir> <path>...      move into <dir>/_archive/<date>/, log to MANIFEST.tsv
  restore   <dir> <archived>...  move back to the original path recorded in the manifest

Reads ~/.claude/projects/**/*.jsonl (subagent transcripts included). Local, no network.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal

Origin = Literal["written", "bash", "edited", "read", "none"]
Suggestion = Literal["superseded?", "stale", "unknown", "keep", "tracked"]

PROJECTS = Path.home() / ".claude" / "projects"
ARCHIVE = "_archive"
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", ARCHIVE}
WRITE_TOOLS: dict[str, Origin] = {"Write": "written", "NotebookEdit": "edited", "Edit": "edited", "MultiEdit": "edited"}
# strongest origin wins when an entry is touched several ways
RANK: dict[Origin, int] = {"written": 4, "bash": 3, "edited": 2, "read": 1, "none": 0}
# Bash output targets: `> f`, `>> f`, `-o f`, `--out[put] f`, `tee f`
BASH_OUT = re.compile(r"(?:>>?|\btee\s+(?:-a\s+)?|\s-o\s*|--out(?:put)?[= ])\s*(['\"]?)([^\s'\";|&)]+)\1")
DATE = re.compile(r"(?:19|20)\d{2}[-_.]?\d{2}[-_.]?\d{2}(?:t?\d{4,6})?")
SELF = Path(__file__).name
SWEEP = 3  # entries read by a single Bash command before it counts as a survey
NOISE = re.compile(r"v\d+|\d+|final|draft|old|new|copy|local|tmp|bak|backup|wip")


def family(name: str, is_dir: bool) -> str:
    stem = name.lower() if is_dir else re.sub(r"\.[a-z0-9]{1,5}$", "", name.lower())
    toks = [t for t in re.split(r"[^a-z0-9]+", DATE.sub(" ", stem)) if t and not NOISE.fullmatch(t)]
    return "-".join(toks) or stem


def title_of(p: Path) -> str:
    if p.is_dir():
        readme = next((r for r in p.glob("README*") if r.is_file()), None)
        return title_of(readme) if readme else ""
    try:
        head = p.open("rb").read(65536).decode("utf-8", "ignore")
    except OSError:
        return ""
    if p.suffix.lower() in {".html", ".htm", ".svg"}:
        m = re.search(r"<title[^>]*>(.*?)</title>|<h1[^>]*>(.*?)</h1>", head, re.S | re.I)
        txt = (m.group(1) or m.group(2)) if m else ""
        return re.sub(r"<[^>]+>|\s+", " ", txt).strip()[:70]
    if p.suffix.lower() in {".md", ".txt", ".tex", ".org"}:
        body = re.sub(r"\A---\n.*?\n---\n|<!--.*?-->", "", head, flags=re.S)
        lines = [ln for ln in body.splitlines() if ln.strip()]
        line = next((ln for ln in lines if ln.lstrip().startswith("#")), lines[0] if lines else "")
        return re.sub(r"^[#\s\\]*(?:section\*?\{|title\{)?", "", line).strip(" }")[:70]
    return ""


class Entry:
    def __init__(self, path: Path, root: Path) -> None:
        self.path, self.rel = path, path.relative_to(root).as_posix()
        self.is_dir = path.is_dir()
        files = [f for f in path.rglob("*") if f.is_file() and not SKIP_DIRS & set(f.parts)] if self.is_dir else [path]
        stats = [f.stat() for f in files]
        self.size = sum(s.st_size for s in stats)
        self.mtime = max((s.st_mtime for s in stats), default=path.stat().st_mtime)
        self.nfiles = len(files)
        self.origin: Origin = "none"
        self.sessions: set[str] = set()
        self.last: str | None = None
        self.created_by: tuple[str, str] | None = None  # (ts, first prompt of the writing session)
        self.family = family(path.name, self.is_dir)

    def touch(self, kind: Origin, ts: str, session: str, prompt: str) -> None:
        if RANK[kind] > RANK[self.origin]:
            self.origin = kind
        self.sessions.add(session)
        if ts:
            self.last = max(self.last or ts, ts)
        if kind in ("written", "bash") and (self.created_by is None or ts < self.created_by[0]):
            self.created_by = (ts, prompt)


def entries_of(root: Path, recursive: bool) -> list[Entry]:
    if recursive:
        paths = [f for f in root.rglob("*") if f.is_file() and not SKIP_DIRS & set(f.relative_to(root).parts)]
    else:
        paths = [p for p in root.iterdir() if p.name not in SKIP_DIRS and p.name != ".DS_Store"]
    entries = [Entry(p, root) for p in sorted(paths)]
    # a file named after a sibling dir (rapport-x/ -> rapport-x-v3.html) is usually its build output
    dirs = sorted((e.family for e in entries if e.is_dir), key=len, reverse=True)
    for e in entries:
        if not e.is_dir and (src := next((d for d in dirs if e.family.startswith(d + "-")), None)):
            e.family = src
    return entries


def resolve(token: str, cwd: str | None) -> Path | None:
    token = token.strip("'\"")
    if token.startswith("~"):
        return Path(token).expanduser()
    if token.startswith("/"):
        return Path(token)
    return Path(cwd, token) if cwd and token and not token.startswith("-") else None


def first_prompt(rec: dict) -> str | None:
    msg = rec.get("message") or {}
    c = msg.get("content")
    txt = c if isinstance(c, str) else next((b.get("text", "") for b in c or [] if b.get("type") == "text"), "")
    # skip harness-injected turns (<command-name>, <task-notification>, …)
    txt = re.sub(r"\s+", " ", txt or "").strip()
    return txt[:80] if txt and not txt.startswith("<") and not rec.get("isMeta") else None


def scan_sessions(root: Path, entries: list[Entry]) -> None:
    by_path = {e.path: e for e in entries}
    roots = (str(root), "~/" + str(root.relative_to(Path.home())) if root.is_relative_to(Path.home()) else str(root))

    def owner(p: Path | None) -> Entry | None:
        if p is None:
            return None
        p = Path(*[x for x in p.parts if x != "."])
        return next((by_path[c] for c in (p, *p.parents) if c in by_path), None)

    for jf in PROJECTS.rglob("*.jsonl"):
        prompt, session, cleanup = "", jf.stem, False
        touches: list[tuple[Origin, Entry, str, str]] = []
        try:
            fh = jf.open(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        with fh:
            for line in fh:
                cleanup = cleanup or SELF in line
                if not prompt and '"type":"user"' in line:
                    with contextlib.suppress(ValueError):
                        prompt = first_prompt(json.loads(line)) or ""
                if not any(r in line for r in roots):
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                ts, cwd = rec.get("timestamp", ""), rec.get("cwd")
                session = rec.get("sessionId", session)
                content = (rec.get("message") or {}).get("content")
                for b in content if isinstance(content, list) else []:
                    if b.get("type") != "tool_use":
                        continue
                    name, inp = b.get("name", ""), b.get("input") or {}
                    hits: list[tuple[Origin, Path | None]] = []
                    fp = inp.get("file_path") or inp.get("notebook_path") or inp.get("path")
                    if fp:
                        hits.append((WRITE_TOOLS.get(name, "read"), resolve(fp, cwd)))
                    if name == "Bash":
                        cmd = inp.get("command", "")
                        outs = {m.group(2) for m in BASH_OUT.finditer(cmd)}
                        hits += [("bash", resolve(o, cwd)) for o in outs]
                        try:
                            toks = shlex.split(cmd, comments=True)
                        except ValueError:
                            toks = cmd.split()
                        hits += [("read", resolve(t, cwd)) for t in toks if t not in outs and ("/" in t or "." in t)]
                    owned = [(kind, e) for kind, p in hits if (e := owner(p))]
                    # one command reading many entries (ls, head loop, grep -r) is a survey, not a use
                    sweep = len({e for kind, e in owned if kind == "read"}) >= SWEEP
                    touches += [(kind, e, ts, session) for kind, e in owned if kind != "read" or not sweep]
        # a cleanup session reads candidates to judge them: only its writes count
        for kind, e, ts, sid in touches:
            if kind != "read" or not cleanup:
                e.touch(kind, ts, sid, prompt)


def tracked(root: Path) -> set[Path]:
    r = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--full-name"], capture_output=True, text=True)
    if r.returncode:
        return set()
    top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    return {Path(top, f) for f in r.stdout.split("\0") if f}


def is_tracked(p: Path, git_files: set[Path]) -> bool:
    return p in git_files or any(p in f.parents for f in git_files)


def suggest(entries: list[Entry], stale_days: int, git_files: set[Path]) -> dict[Entry, Suggestion]:
    out: dict[Entry, Suggestion] = {}
    now = dt.datetime.now(dt.UTC)

    def version(e: Entry) -> tuple[str, float]:
        # a date in the name beats mtime: copies and re-saves reset mtime, the name keeps the version
        return max(DATE.findall(e.path.name.lower()), default=""), e.mtime

    newest: dict[tuple[str, bool], tuple[str, float]] = {}
    for e in entries:
        k = (e.family, e.is_dir)
        newest[k] = max(newest.get(k, version(e)), version(e))
    for e in entries:
        used = dt.datetime.fromisoformat(e.last.replace("Z", "+00:00")).timestamp() if e.last else 0
        idle = (now.timestamp() - max(e.mtime, used)) / 86400
        if is_tracked(e.path, git_files):
            out[e] = "tracked"
        elif version(e) < newest[(e.family, e.is_dir)]:
            out[e] = "superseded?"
        elif e.origin == "none":
            out[e] = "unknown"
        elif idle > stale_days:
            out[e] = "stale"
        else:
            out[e] = "keep"
    return out


def human(n: float) -> str:
    for unit in ("B", "K", "M", "G"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.0f}T"


def cmd_inventory(a: argparse.Namespace) -> None:
    root = Path(a.dir).expanduser().resolve()
    entries = entries_of(root, a.recursive)
    scan_sessions(root, entries)
    sug = suggest(entries, a.stale_days, tracked(root))
    order = {"superseded?": 0, "stale": 1, "unknown": 2, "keep": 3, "tracked": 4}
    entries.sort(key=lambda e: (order[sug[e]], e.family, -e.mtime))
    rows = [{
        "entry": e.rel + ("/" if e.is_dir else ""), "suggest": sug[e], "origin": e.origin,
        "family": e.family, "mtime": dt.date.fromtimestamp(e.mtime).isoformat(), "size": human(e.size),
        "files": e.nfiles, "sessions": len(e.sessions), "last_touch": (e.last or "")[:10],
        "created_by": e.created_by[1] if e.created_by else "", "title": title_of(e.path),
    } for e in entries]
    if a.json:
        json.dump(rows, sys.stdout, ensure_ascii=False, indent=1)
        return
    cols = ["entry", "suggest", "origin", "family", "mtime", "size", "sessions", "last_touch", "title", "created_by"]
    print("| " + " | ".join(cols) + " |\n|" + "---|" * len(cols))
    for r in rows:
        print("| " + " | ".join(str(r[c]).replace("|", "/") for c in cols) + " |")


def manifest(root: Path) -> Path:
    return root / ARCHIVE / "MANIFEST.tsv"


def cmd_archive(a: argparse.Namespace) -> None:
    root = Path(a.dir).expanduser().resolve()
    git_files, dest_root = tracked(root), root / ARCHIVE / dt.date.today().isoformat()
    for raw in a.paths:
        src = (root / Path(raw).expanduser()).resolve()  # an absolute raw replaces root
        if root not in src.parents or ARCHIVE in src.relative_to(root).parts:
            sys.exit(f"refused: {raw} is outside {root} or already archived")
        if not src.exists():
            sys.exit(f"refused: {raw} does not exist")
        if is_tracked(src, git_files):
            sys.exit(f"refused: {raw} is git-tracked — use git rm, history already keeps it")
        dst = dest_root / src.relative_to(root)
        if dst.exists():
            sys.exit(f"refused: {dst} already exists")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        with manifest(root).open("a") as m:
            m.write(f"{dt.datetime.now().isoformat(timespec='seconds')}\t{src}\t{dst}\n")
        print(f"archived {src.relative_to(root)} -> {dst.relative_to(root)}")


def cmd_restore(a: argparse.Namespace) -> None:
    root = Path(a.dir).expanduser().resolve()
    log = {Path(dst): Path(src) for _, src, dst in (ln.split("\t") for ln in manifest(root).read_text().splitlines() if ln)}
    for raw in a.paths:
        arch = (root / Path(raw).expanduser()).resolve()
        orig = log.get(arch)
        if orig is None or not arch.exists():
            sys.exit(f"refused: {raw} not found in {manifest(root)}")
        if orig.exists():
            sys.exit(f"refused: {orig} exists again")
        orig.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(arch), str(orig))
        print(f"restored {orig.relative_to(root)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    inv = sub.add_parser("inventory")
    inv.add_argument("dir")
    inv.add_argument("--recursive", action="store_true", help="one row per file instead of per top-level entry")
    inv.add_argument("--stale-days", type=int, default=30)
    inv.add_argument("--json", action="store_true")
    inv.set_defaults(fn=cmd_inventory)
    for name, fn in (("archive", cmd_archive), ("restore", cmd_restore)):
        p = sub.add_parser(name)
        p.add_argument("dir")
        p.add_argument("paths", nargs="+")
        p.set_defaults(fn=fn)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
