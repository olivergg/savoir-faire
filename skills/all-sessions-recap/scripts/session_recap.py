#!/usr/bin/env python3
"""
Recap what's being worked on across every Claude Code project, grouped by
repo, ranked by an activity score (recency-weighted message volume).

Reads only ~/.claude/projects/*/*.jsonl (top-level session files — nested
subagent-transcript dirs are skipped). Local, read-only, no network.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import fnmatch
import json
import math
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_ROOT = Path.home() / ".claude" / "projects"
HALF_LIFE_DAYS = 3.0  # score contribution halves every N days of age
GIT_TIMEOUT = 2.0  # seconds, per git subprocess call

# Projects to always skip, as fnmatch glob patterns matched against both the
# full cwd and its "~"-shortened form (see short_name()). Set via
# SESSION_RECAP_IGNORE (colon-separated), extend per-run with --ignore,
# bypass with --no-ignore.
DEFAULT_IGNORE: list[str] = [
    p for p in os.environ.get("SESSION_RECAP_IGNORE", "").split(":") if p
]


def is_ignored(cwd: str, patterns: list[str]) -> bool:
    short = short_name(cwd)
    return any(fnmatch.fnmatch(cwd, p) or fnmatch.fnmatch(short, p) for p in patterns)

# ---------------------------------------------------------------------------
# Git ahead/behind vs. the repo's main branch — local refs only, no fetch.

_base_branch_cache: dict[str, str | None] = {}
_ahead_behind_cache: dict[tuple[str, str], tuple[int, int] | None] = {}


def _git(cwd: str, *args: str) -> str | None:
    try:
        r = subprocess.run(
            ["git", "-C", cwd, *args],
            capture_output=True, text=True, timeout=GIT_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def resolve_base_branch(cwd: str) -> str | None:
    if cwd in _base_branch_cache:
        return _base_branch_cache[cwd]
    base = None
    head = _git(cwd, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD")
    candidates = [head] if head else []
    candidates += ["origin/main", "origin/master", "main", "master"]
    for ref in candidates:
        if ref and _git(cwd, "rev-parse", "--verify", "-q", ref) is not None:
            base = ref
            break
    _base_branch_cache[cwd] = base
    return base


def git_ahead_behind(cwd: str, branch: str) -> tuple[int, int] | None:
    """(ahead, behind) of `branch` vs. the repo's default branch, using only
    local refs (no fetch — may be stale if origin hasn't been fetched
    recently, but that's fine for an at-a-glance indicator)."""
    key = (cwd, branch)
    if key in _ahead_behind_cache:
        return _ahead_behind_cache[key]
    result = None
    base = resolve_base_branch(cwd)
    if base and base.rsplit("/", 1)[-1] != branch:
        counts = _git(cwd, "rev-list", "--left-right", "--count", f"{branch}...{base}")
        if counts:
            parts = counts.split()
            if len(parts) == 2 and all(p.isdigit() for p in parts):
                result = (int(parts[0]), int(parts[1]))
    _ahead_behind_cache[key] = result
    return result

# ---------------------------------------------------------------------------
# Color

class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    ORANGE = "\033[38;5;208m"


def color_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def paint(text: str, *codes: str, enabled: bool) -> str:
    if not enabled or not codes:
        return text
    return "".join(codes) + text + C.RESET


# ---------------------------------------------------------------------------
# Emoji

EMOJI_RULES: list[tuple[str, str]] = [
    ("front", "🎨"), ("ui", "🎨"),
    ("postgres", "🗄️"), ("db", "🗄️"), ("sql", "🗄️"),
    ("kafka", "📨"),
    ("infra", "☸️"), ("kubernetes", "☸️"), ("k8s", "☸️"), ("provisioning", "☸️"),
    ("jenkins", "🚀"), ("cicd", "🚀"), ("pipeline", "🚀"),
    ("e2e", "🧪"), ("test", "🧪"),
    ("security", "🔐"), ("audit", "🔐"), ("secret", "🔐"),
    ("skill", "🧭"),
    ("doc", "📚"),
    ("jira", "🎫"),
    ("sso", "🔑"),
    ("sonar", "🔎"),
    ("map", "🗺️"), ("position", "🗺️"), ("gps", "🗺️"),
    ("changelog", "📰"),
]
DEFAULT_EMOJI = "📁"


def pick_emoji(name: str) -> str:
    low = name.lower()
    for needle, emoji in EMOJI_RULES:
        if needle in low:
            return emoji
    return DEFAULT_EMOJI


# ---------------------------------------------------------------------------
# Parsing

def parse_ts(ts: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))


class Session:
    def __init__(self, path: Path):
        self.path = path
        self.title: str | None = None
        self.cwd_counts: collections.Counter[str] = collections.Counter()
        self.git_branch: str | None = None
        self.first_ts: datetime.datetime | None = None
        self.last_ts: datetime.datetime | None = None
        self.user_count = 0
        self.assistant_count = 0

    @property
    def cwd(self) -> str | None:
        return self.cwd_counts.most_common(1)[0][0] if self.cwd_counts else None

    @property
    def message_count(self) -> int:
        return self.user_count + self.assistant_count

    @property
    def duration(self) -> datetime.timedelta:
        if self.first_ts is None or self.last_ts is None:
            return datetime.timedelta()
        return self.last_ts - self.first_ts


def load_session(path: Path) -> Session | None:
    s = Session(path)
    try:
        with path.open(errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = d.get("type")
                if t == "ai-title" and d.get("aiTitle"):
                    s.title = d["aiTitle"]
                if "cwd" in d:
                    s.cwd_counts[d["cwd"]] += 1
                if d.get("gitBranch"):
                    s.git_branch = d["gitBranch"]
                if not d.get("isSidechain", False):
                    if t == "user":
                        s.user_count += 1
                    elif t == "assistant":
                        s.assistant_count += 1
                ts = d.get("timestamp")
                if ts:
                    try:
                        dt = parse_ts(ts)
                    except ValueError:
                        continue
                    if s.first_ts is None or dt < s.first_ts:
                        s.first_ts = dt
                    if s.last_ts is None or dt > s.last_ts:
                        s.last_ts = dt
    except OSError:
        return None
    if s.last_ts is None:
        return None
    return s


def decode_dirname(name: str) -> str:
    # Best-effort: project dirs encode the path with '-' as separator; not
    # reversible when the real path contains '-', so only used as a fallback
    # when no session recorded a cwd.
    return "/" + name.lstrip("-").replace("-", "/")


def relative_age(dt: datetime.datetime, now: datetime.datetime) -> str:
    secs = (now - dt).total_seconds()
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    return f"{int(secs // 86400)}d ago"


def human_duration(td: datetime.timedelta) -> str:
    secs = int(td.total_seconds())
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m"
    if secs < 86400:
        return f"{secs // 3600}h{(secs % 3600) // 60:02d}"
    return f"{secs // 86400}d{(secs % 86400) // 3600}h"


def collect_projects(root: Path) -> dict[str, list[Session]]:
    projects: dict[str, list[Session]] = collections.defaultdict(list)
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        sessions = []
        for f in entry.glob("*.jsonl"):
            s = load_session(f)
            if s:
                sessions.append(s)
        if not sessions:
            continue
        cwd_votes: collections.Counter[str] = collections.Counter()
        for s in sessions:
            if s.cwd:
                cwd_votes[s.cwd] += 1
        name = cwd_votes.most_common(1)[0][0] if cwd_votes else decode_dirname(entry.name)
        projects[name].extend(sessions)
    return projects


def score_session(s: Session, now: datetime.datetime, half_life: float) -> float:
    age_days = (now - s.last_ts).total_seconds() / 86400.0
    decay = math.exp(-math.log(2) * age_days / half_life)
    return s.message_count * decay


def short_name(path: str) -> str:
    home = str(Path.home())
    if path.startswith(home):
        return "~" + path[len(home):]
    return path


# ---------------------------------------------------------------------------
# Rendering

def age_dot(dt: datetime.datetime, now: datetime.datetime, en: bool) -> str:
    secs = (now - dt).total_seconds()
    if secs < 3 * 3600:
        return paint("●", C.GREEN, enabled=en)
    if secs < 24 * 3600:
        return paint("●", C.YELLOW, enabled=en)
    return paint("●", C.DIM, enabled=en)


def format_ahead_behind(cwd: str | None, branch: str | None) -> str | None:
    """'12↑ 3↓', '12↑', '3↓', 'in sync', or None if not computable (repo
    gone, branch deleted, no resolvable main branch, git not on PATH...)."""
    if not cwd or not branch:
        return None
    ab = git_ahead_behind(cwd, branch)
    if ab is None:
        return None
    ahead, behind = ab
    if ahead == 0 and behind == 0:
        return "in sync"
    parts = []
    if ahead:
        parts.append(f"{ahead}↑")
    if behind:
        parts.append(f"{behind}↓")
    return " ".join(parts)


def render_list(rows, now, top_titles: int, en: bool, show_ids: bool, git_status: bool) -> None:
    for score, name, last_active, recent in rows:
        emoji = pick_emoji(name)
        header = f"{emoji} {paint(short_name(name), C.BOLD, enabled=en)}"
        count_note = paint(f"({len(recent)} session{'s' if len(recent) != 1 else ''})", C.DIM, enabled=en)
        print(f"\n{header}  {count_note}")
        for s in recent[:top_titles]:
            title = s.title or "(untitled)"
            when = f"{relative_age(s.last_ts, now):<8}"
            ab_note = ""
            if git_status and s.git_branch:
                ab = format_ahead_behind(s.cwd, s.git_branch)
                if ab:
                    ab_note = paint(f" ({ab})", C.MAGENTA, enabled=en)
            branch = paint(f" [{s.git_branch}]", C.DIM, enabled=en) if s.git_branch else ""
            id_note = paint(f"  · {s.path.stem}", C.DIM, enabled=en) if show_ids else ""
            print(f"  {age_dot(s.last_ts, now, en)} {when} {title}{branch}{ab_note}{id_note}")


def find_session_file(root: Path, session_id: str) -> Path:
    matches = []
    for entry in root.iterdir():
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        for f in entry.glob("*.jsonl"):
            if f.stem == session_id or f.stem.startswith(session_id):
                matches.append(f)
    if not matches:
        sys.exit(f"no session found matching id: {session_id}")
    if len(matches) > 1:
        sys.exit("ambiguous id, matches: " + ", ".join(m.stem for m in matches))
    return matches[0]


def sample_turns(turns: list[tuple[str, str]], max_turns: int | None) -> tuple[list[tuple[str, str]], int]:
    """Keep the shape of a session's arc without dumping hundreds of turns:
    first half + last half of the budget, noting how many were cut."""
    if not max_turns or len(turns) <= max_turns:
        return turns, 0
    head = (max_turns + 1) // 2
    tail = max_turns - head
    omitted = len(turns) - head - tail
    return turns[:head] + turns[-tail:], omitted


def extract_human_turns(path: Path, max_turns: int | None = None) -> dict:
    """Pull out only genuinely-typed human turns + the tail of assistant text,
    stripped of tool calls/attachments/sidechains — raw material for an LLM
    (not this script) to write an actual recap from."""
    title = None
    cwd = None
    branch = None
    first_ts = last_ts = None
    turns: list[tuple[str, str]] = []  # (timestamp, text)
    last_assistant_text = None

    with path.open(errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = d.get("type")
            if t == "ai-title" and d.get("aiTitle"):
                title = d["aiTitle"]
            if "cwd" in d:
                cwd = d["cwd"]
            if d.get("gitBranch"):
                branch = d["gitBranch"]
            ts = d.get("timestamp")
            if ts:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts

            if d.get("isSidechain"):
                continue
            msg = d.get("message") or {}
            content = msg.get("content")

            if t == "user" and (d.get("origin") or {}).get("kind") == "human":
                text = content if isinstance(content, str) else None
                if text is None and isinstance(content, list):
                    text = " ".join(
                        b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
                    ).strip()
                if text:
                    turns.append((ts or "", text[:500]))

            if t == "assistant" and isinstance(content, list):
                text = " ".join(
                    b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
                ).strip()
                if text:
                    last_assistant_text = text[:800]

    shown_turns, omitted = sample_turns(turns, max_turns)
    return {
        "id": path.stem,
        "path": str(path),
        "title": title,
        "cwd": cwd,
        "branch": branch,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "turns": shown_turns,
        "turns_total": len(turns),
        "turns_omitted": omitted,
        "last_assistant_text": last_assistant_text,
    }


def cmd_show(args: argparse.Namespace) -> None:
    root = Path(args.root).expanduser()
    if not root.exists():
        sys.exit(f"root not found: {root}")
    path = Path(args.session_id).expanduser() if Path(args.session_id).expanduser().is_file() \
        else find_session_file(root, args.session_id)
    data = extract_human_turns(path, max_turns=args.max_turns)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    print(f"session   {data['id']}")
    print(f"project   {data['cwd']}")
    if data["branch"]:
        print(f"branch    {data['branch']}")
    print(f"window    {data['first_ts']} -> {data['last_ts']}")
    print(f"title     {data['title'] or '(untitled)'}")
    print(f"\nhuman turns ({data['turns_total']}):")
    for i, (ts, text) in enumerate(data["turns"], 1):
        print(f"  {i:>2}. [{ts}] {text}")
        if data["turns_omitted"] and i == (len(data["turns"]) + 1) // 2:
            print(f"      ... {data['turns_omitted']} turn(s) omitted ...")
    if data["last_assistant_text"]:
        print("\nlast assistant note:")
        print(f"  {data['last_assistant_text']}")


def resolve_ignore(args: argparse.Namespace) -> list[str]:
    base = [] if args.no_ignore else list(DEFAULT_IGNORE)
    return base + (args.ignore or [])


def select_rows(root: Path, days: int, half_life: float, sort: str, limit: int | None,
                 ignore: list[str] | None = None):
    """Same project/session ranking used by every subcommand: recency-scored,
    grouped by project, most recent session first within each project."""
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(days=days)
    ignore = ignore or []

    projects = collect_projects(root)
    rows = []
    for name, sessions in projects.items():
        if ignore and is_ignored(name, ignore):
            continue
        recent = [s for s in sessions if s.last_ts >= cutoff]
        if not recent:
            continue
        score = sum(score_session(s, now, half_life) for s in recent)
        last_active = max(s.last_ts for s in recent)
        recent.sort(key=lambda s: s.last_ts, reverse=True)
        rows.append((score, name, last_active, recent))

    if sort == "recent":
        rows.sort(key=lambda r: r[2], reverse=True)
    else:
        rows.sort(key=lambda r: r[0], reverse=True)
    if limit:
        rows = rows[:limit]
    return rows, now


def cmd_recap(args: argparse.Namespace) -> None:
    if args.topics:
        args.sort = "recent"

    root = Path(args.root).expanduser()
    if not root.exists():
        sys.exit(f"root not found: {root}")

    en = color_enabled() and not args.plain
    rows, now = select_rows(root, args.days, args.half_life, args.sort, args.limit, resolve_ignore(args))
    if not rows:
        print(f"No sessions active in the last {args.days} day(s).")
        return

    if args.topics:
        for score, name, last_active, recent in rows:
            emoji = pick_emoji(name)
            print(f"\n{emoji}  {paint(short_name(name), C.BOLD, C.CYAN, enabled=en)}")
            for s in recent[: args.top_titles]:
                print(f"    - {s.title or '(untitled)'}")
        return

    render_list(rows, now, args.top_titles, en, show_ids=not args.no_ids, git_status=not args.no_git_status)


def cmd_digest(args: argparse.Namespace) -> None:
    """Bulk version of `show`: extracted human-turn material for every
    session that `recap` would list, in one pass — meant to be read by an
    LLM (the calling skill) to write real per-session recaps, not by a human."""
    root = Path(args.root).expanduser()
    if not root.exists():
        sys.exit(f"root not found: {root}")

    rows, now = select_rows(root, args.days, args.half_life, args.sort, args.limit, resolve_ignore(args))
    if not rows:
        print(f"No sessions active in the last {args.days} day(s).")
        return

    for score, name, last_active, recent in rows:
        print(f"\n=== {short_name(name)} ===")
        for s in recent[: args.top_titles]:
            data = extract_human_turns(s.path, max_turns=args.max_turns)
            branch_note = ""
            if data["branch"]:
                branch_note = f" [{data['branch']}"
                if not args.no_git_status:
                    ab = format_ahead_behind(data["cwd"], data["branch"])
                    if ab:
                        branch_note += f", {ab} vs main"
                branch_note += "]"
            print(f"\n-- session {data['id']}{branch_note}"
                  f"  ({relative_age(s.last_ts, now)}, {data['turns_total']} human turn(s)) --")
            print(f"auto-title: {data['title'] or '(untitled)'}")
            for i, (ts, text) in enumerate(data["turns"], 1):
                print(f"  {i:>2}. {text}")
                if data["turns_omitted"] and i == (len(data["turns"]) + 1) // 2:
                    print(f"      ... {data['turns_omitted']} turn(s) omitted ...")
            if data["last_assistant_text"]:
                print(f"  last note: {data['last_assistant_text'][:300]}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")

    p_recap = sub.add_parser("recap", help="repo-by-repo activity recap (default)")
    p_recap.add_argument("--root", default=str(DEFAULT_ROOT), help="projects dir (default: ~/.claude/projects)")
    p_recap.add_argument("--days", type=int, default=14, help="only list sessions active within N days (default: 14)")
    p_recap.add_argument("--half-life", type=float, default=HALF_LIFE_DAYS,
                          help=f"score half-life in days (default: {HALF_LIFE_DAYS})")
    p_recap.add_argument("--top-titles", type=int, default=5, help="sessions shown per project (default: 5)")
    p_recap.add_argument("--limit", type=int, default=None, help="max number of projects to show")
    p_recap.add_argument("--sort", choices=["score", "recent"], default="score",
                          help="rank projects by decayed score or by raw last-active time (default: score)")
    p_recap.add_argument("--topics", action="store_true",
                          help="just the subjects: sort by last activity, no score/date/branch/msg-count noise")
    p_recap.add_argument("--plain", action="store_true", help="disable colors/emoji, raw text output")
    p_recap.add_argument("--no-ids", action="store_true", help="hide session ids at end of each line")
    p_recap.add_argument("--no-git-status", action="store_true",
                          help="skip ahead/behind-vs-main git lookup (local refs only, but shells out per branch)")
    p_recap.add_argument("--ignore", action="append", metavar="GLOB",
                          help="extra glob pattern to exclude (matched against cwd and its ~-shortened form); "
                               f"repeatable, added on top of DEFAULT_IGNORE ({DEFAULT_IGNORE})")
    p_recap.add_argument("--no-ignore", action="store_true", help="disable DEFAULT_IGNORE (still applies --ignore)")
    p_recap.set_defaults(func=cmd_recap)

    p_show = sub.add_parser("show", help="extract one session's human turns (for an LLM to recap — not done here)")
    p_show.add_argument("session_id", help="session id (uuid, or a prefix of it), or a direct path to the .jsonl")
    p_show.add_argument("--root", default=str(DEFAULT_ROOT), help="projects dir (default: ~/.claude/projects)")
    p_show.add_argument("--max-turns", type=int, default=None, help="sample first/last N turns instead of all")
    p_show.add_argument("--json", action="store_true", help="machine-readable output")
    p_show.set_defaults(func=cmd_show)

    p_digest = sub.add_parser(
        "digest", help="bulk-extract human turns for every session `recap` would list — for an LLM to write real "
                        "per-session recaps from, not done here")
    p_digest.add_argument("--root", default=str(DEFAULT_ROOT), help="projects dir (default: ~/.claude/projects)")
    p_digest.add_argument("--days", type=int, default=7, help="only sessions active within N days (default: 7)")
    p_digest.add_argument("--half-life", type=float, default=HALF_LIFE_DAYS,
                           help=f"score half-life in days (default: {HALF_LIFE_DAYS})")
    p_digest.add_argument("--top-titles", type=int, default=5, help="sessions per project (default: 5)")
    p_digest.add_argument("--limit", type=int, default=15, help="max number of projects (default: 15)")
    p_digest.add_argument("--sort", choices=["score", "recent"], default="score")
    p_digest.add_argument("--max-turns", type=int, default=6, help="turns sampled per session (default: 6)")
    p_digest.add_argument("--no-git-status", action="store_true",
                           help="skip ahead/behind-vs-main git lookup (local refs only, but shells out per branch)")
    p_digest.add_argument("--ignore", action="append", metavar="GLOB",
                           help="extra glob pattern to exclude (matched against cwd and its ~-shortened form); "
                                f"repeatable, added on top of DEFAULT_IGNORE ({DEFAULT_IGNORE})")
    p_digest.add_argument("--no-ignore", action="store_true", help="disable DEFAULT_IGNORE (still applies --ignore)")
    p_digest.set_defaults(func=cmd_digest)

    # `recap` is the default subcommand when none / only flags are given.
    argv = sys.argv[1:]
    if not argv or argv[0].startswith("-"):
        argv = ["recap"] + argv
    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
