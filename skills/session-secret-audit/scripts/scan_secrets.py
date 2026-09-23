#!/usr/bin/env python3
"""
Scan Claude Code session transcripts for leaked secrets and clean them up —
without ever putting the secret itself back through an LLM session.

  scan        report file / pattern / count / severity
  redact      replace matches of named pattern(s) in place, by shape only
  quarantine  move file(s) out of the scanned tree
  shred       multi-pass overwrite + delete file(s)

SAFETY: never pass a literal secret as an argument. Only prints paths,
pattern names, counts — no "show me the match" mode, by design.
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import shutil
import sys
from pathlib import Path

DEFAULT_ROOT = Path.home() / ".claude" / "projects"
SCAN_SUFFIXES = {".jsonl", ".txt", ".md"}
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# Known session/transcript homes for other agent CLIs and IDE tools.
# Only paths that exist on disk are scanned with --all; everything else is
# skipped silently, so it's safe to list tools that aren't installed here.
TOOL_ROOTS: dict[str, list[Path]] = {
    "claude-code": [Path.home() / ".claude" / "projects"],
    "codex": [Path.home() / ".codex"],
    "copilot-cli": [Path.home() / ".copilot"],
    "gemini-cli": [Path.home() / ".gemini"],
    "opencode": [
        Path.home() / ".config" / "opencode",
        Path.home() / ".local" / "share" / "opencode",
        Path.home() / ".local" / "state" / "opencode",
    ],
    "goose": [Path.home() / ".config" / "goose", Path.home() / ".local" / "share" / "goose"],
    "crush": [Path.home() / ".config" / "crush", Path.home() / ".local" / "share" / "crush"],
    "aider": [
        Path.home() / ".aider",
        Path.home() / ".aider-desk",
        Path.home() / ".aider.chat.history.md",
        Path.home() / ".aider.input.history",
    ],
    "continue": [Path.home() / ".continue"],
    "github-copilot": [Path.home() / ".config" / "github-copilot"],
    "cursor": [
        Path.home() / ".cursor",
        Path.home() / "Library" / "Application Support" / "Cursor",
    ],
    "windsurf": [
        Path.home() / ".windsurf",
        Path.home() / "Library" / "Application Support" / "Windsurf",
    ],
    "claude-desktop": [Path.home() / "Library" / "Application Support" / "Claude"],
    "zed": [Path.home() / ".zed", Path.home() / "Library" / "Application Support" / "Zed"],
    "amazon-q": [Path.home() / ".amazonq"],
    "sourcegraph-cody": [Path.home() / ".cody", Path.home() / ".sourcegraph"],
    "ollama": [Path.home() / ".ollama"],
}

# name -> (regex, severity). Shape-based only — never a literal value.
PATTERNS: dict[str, tuple[str, str]] = {
    "anthropic_api_key": (r"sk-ant-[A-Za-z0-9_-]{20,}", "critical"),
    "openrouter_api_key": (r"sk-or-v1-[A-Za-z0-9]{20,}", "critical"),
    # OpenAI project/service-account/admin keys contain '-'/'_'; the lookbehind keeps
    # identifiers like "task-management-..." from matching.
    "generic_sk_key": (
        r"(?<![A-Za-z0-9_-])sk-(?!ant-|or-v1-)"
        r"(?:(?:proj|svcacct|admin)-[A-Za-z0-9_-]{20,}|[A-Za-z0-9]{20,})",
        "critical",
    ),
    "aws_access_key_id": (r"AKIA[0-9A-Z]{16}", "critical"),
    # Whole block, not just the header — otherwise redact leaves the key body behind.
    # No END marker (truncated output): header + the base64 run that follows, literal "\n" included.
    "private_key_block": (
        r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"
        r"(?:[\s\S]{0,10000}?-----END (?:[A-Z]+ )?PRIVATE KEY-----|(?:\\[nr]|[\r\nA-Za-z0-9+/=])*)",
        "critical",
    ),
    "github_pat_classic": (r"ghp_[A-Za-z0-9]{30,}", "critical"),
    "github_pat_fine_grained": (r"github_pat_[A-Za-z0-9_]{20,}", "critical"),
    "slack_token": (r"xox[baprs]-[0-9A-Za-z-]{10,}", "critical"),
    "google_api_key": (r"AIza[0-9A-Za-z_-]{35}", "high"),
    "jwt": (r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "medium"),
    "db_connection_string": (
        r'(?:postgres(?:ql)?|mysql|mongodb|redis)://[^:\s"\\]+:[^@\s"\\]+@[^/\s"\\]+', "medium"
    ),
    "google_oauth_access_token": (r"ya29\.[0-9A-Za-z_-]{20,}", "low"),
    "bearer_token": (r"Bearer [A-Za-z0-9._-]{15,}", "low"),
}
COMPILED = {name: (re.compile(pat), sev) for name, (pat, sev) in PATTERNS.items()}


def iter_scan_files(root: Path):
    if root.is_file():
        if root.suffix in SCAN_SUFFIXES:
            yield root
        return
    for dirpath, _dirnames, filenames in os.walk(root):
        for fname in filenames:
            p = Path(dirpath) / fname
            if p.suffix in SCAN_SUFFIXES:
                yield p


def existing_files(paths: list[str]) -> list[Path]:
    out = []
    for f in paths:
        p = Path(f).expanduser()
        if p.is_file():
            out.append(p)
        else:
            print(f"skip (not a file): {p}", file=sys.stderr)
    return out


def scan_root(root: Path, tool: str = "") -> list[tuple[str, str, int, float, Path, str]]:
    # (severity, pattern, count, mtime, path, tool)
    rows = []
    for f in iter_scan_files(root):
        try:
            text = f.read_text(errors="ignore")
        except OSError:
            continue
        for name, (regex, sev) in COMPILED.items():
            n = len(regex.findall(text))
            if n:
                rows.append((sev, name, n, f.stat().st_mtime, f, tool))
    return rows


def print_rows(rows: list[tuple[str, str, int, float, Path, str]], base: Path, tool_col: bool) -> None:
    rows.sort(key=lambda r: (SEVERITY_ORDER.get(r[0], 9), -r[3]))
    if tool_col:
        header = f"{'SEVERITY':<9} {'TOOL':<15} {'PATTERN':<26} {'COUNT':<6} {'MTIME':<17} PATH"
    else:
        header = f"{'SEVERITY':<9} {'PATTERN':<26} {'COUNT':<6} {'MTIME':<17} PATH"
    print(header)
    print("-" * len(header))
    for sev, name, n, mtime, path, tool in rows:
        mtime_s = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        if tool_col:
            print(f"{sev:<9} {tool:<15} {name:<26} {n:<6} {mtime_s:<17} {path}")
        else:
            print(f"{sev:<9} {name:<26} {n:<6} {mtime_s:<17} {path.relative_to(base)}")

    print(f"\n{len(rows)} pattern/file hits across {len({r[4] for r in rows})} files. "
          f"No values printed — redact by pattern name or quarantine/shred the file.")


def cmd_scan(args: argparse.Namespace) -> None:
    if args.all or args.root is None:
        all_rows = []
        scanned_any_root = False
        for tool, roots in TOOL_ROOTS.items():
            for root in roots:
                if not root.exists():
                    continue
                scanned_any_root = True
                all_rows.extend(scan_root(root, tool=tool))
        if not scanned_any_root:
            sys.exit("no known agent-tool directories found on this machine")
        if not all_rows:
            print("No secret-shaped patterns found across any known agent-tool directory.")
            return
        print_rows(all_rows, base=Path.home(), tool_col=True)
        return

    root = Path(args.root).expanduser()
    if not root.exists():
        sys.exit(f"root not found: {root}")

    rows = scan_root(root)
    if not rows:
        print("No secret-shaped patterns found.")
        return
    print_rows(rows, base=root, tool_col=False)


def cmd_redact(args: argparse.Namespace) -> None:
    names = args.patterns or list(COMPILED.keys())
    for p in existing_files(args.files):
        # surrogateescape round-trips non-UTF-8 bytes instead of silently dropping them
        text = p.read_text(encoding="utf-8", errors="surrogateescape")
        total = 0
        for name in names:
            regex, _sev = COMPILED[name]
            text, n = regex.subn(f"**REDACTED_{name.upper()}**", text)
            total += n
        if total and not args.dry_run:
            tmp = p.with_suffix(p.suffix + ".redact.tmp")
            tmp.write_text(text, encoding="utf-8", errors="surrogateescape")
            shutil.copymode(p, tmp)  # transcripts are 0600; don't widen to umask default
            os.replace(tmp, p)
        action = "would redact" if args.dry_run else "redacted"
        print(f"{action} {total} match(es) in {p}")


def cmd_quarantine(args: argparse.Namespace) -> None:
    dest_dir = Path(args.dest).expanduser()
    dest_dir.mkdir(parents=True, exist_ok=True)
    for p in existing_files(args.files):
        target = dest_dir / p.name
        os.replace(p, target)
        print(f"quarantined {p} -> {target}")


def cmd_shred(args: argparse.Namespace) -> None:
    for p in existing_files(args.files):
        size = p.stat().st_size
        with open(p, "r+b", buffering=0) as fh:
            for _ in range(args.passes):
                fh.seek(0)
                fh.write(os.urandom(size))
                fh.flush()
                os.fsync(fh.fileno())
            fh.seek(0)
            fh.write(b"\x00" * size)
            fh.flush()
            os.fsync(fh.fileno())
        p.unlink()
        print(f"shredded {p}")
    print(
        "Note: on SSD/APFS (copy-on-write, wear-leveling) overwrite passes do not "
        "guarantee old blocks are physically unrecoverable. Rotate any leaked "
        "credential regardless of shredding."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="scan a directory tree and report matches (no values printed)")
    p_scan_root = p_scan.add_mutually_exclusive_group()
    p_scan_root.add_argument("--root", default=None,
                              help=f"directory to scan (default: scan every known agent-tool "
                                   f"directory found on this machine, i.e. --all)")
    p_scan_root.add_argument("--all", action="store_true",
                              help="scan every known agent-tool directory found on this machine "
                                   f"({', '.join(TOOL_ROOTS)}) — this is the default with no flags")
    p_scan.set_defaults(func=cmd_scan)

    p_redact = sub.add_parser("redact", help="redact matches of given pattern name(s) in place")
    p_redact.add_argument("files", nargs="+")
    p_redact.add_argument("--patterns", nargs="+", choices=list(COMPILED.keys()),
                           help="restrict to these pattern names (default: all)")
    p_redact.add_argument("--dry-run", action="store_true")
    p_redact.set_defaults(func=cmd_redact)

    p_quar = sub.add_parser("quarantine", help="move file(s) out of the scanned tree")
    p_quar.add_argument("files", nargs="+")
    p_quar.add_argument("--dest", default=str(Path.home() / ".claude" / "quarantine"))
    p_quar.set_defaults(func=cmd_quarantine)

    p_shred = sub.add_parser("shred", help="multi-pass overwrite + delete file(s)")
    p_shred.add_argument("files", nargs="+")
    p_shred.add_argument("--passes", type=int, default=3)
    p_shred.set_defaults(func=cmd_shred)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
