#!/usr/bin/env python3
"""Extract every human prompt of a Claude Code session, in order, with what the agent did in between.

  how_i_prompt.py extract [--session ID|PATH] [--project DIR] [-o OUT.json]
  how_i_prompt.py render OUT.json [-o OUT.md]

`extract` is deterministic: verbatim prompts (typed prompts, slash commands, mid-turn
messages, multiple-choice answers, refusals with feedback), tools used, files written, and an
excerpt of the agent's last reply. Each turn has an empty `resume` for the caller to fill in
one line. `render` turns the JSON into Markdown. Secrets, emails and home paths are masked.
"""
import argparse, collections, json, os, re, sys
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
EXCERPT = 600

SECRETS = [
    (re.compile(r"\b(sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|xox[abpr]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|glpat-[A-Za-z0-9_-]{20})\b"), "«secret»"),
    (re.compile(r"(?i)\b(password|passwd|pwd|token|secret|api[_-]?key)(\s*[=:]\s*)(\S+)"), r"\1\2«secret»"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+"), "«jwt»"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "«email»"),
    (re.compile(r"/Users/[^/\s]+|/home/[^/\s]+"), "~"),
]


def mask(s: str) -> str:
    for rx, sub in SECRETS:
        s = rx.sub(sub, s)
    return s


def session_file(session: str | None, project: str | None) -> Path:
    if session and Path(session).is_file():
        return Path(session)
    folder = PROJECTS / re.sub(r"[^A-Za-z0-9]", "-", str(Path(project or os.getcwd()).resolve()))
    if session:
        # Skip ".orphaned-…" copies Claude Code leaves next to a session file.
        hits = sorted((p for p in PROJECTS.glob(f"*/{session}*.jsonl") if ".orphaned" not in p.name), key=lambda p: len(p.name))
        if not hits:
            sys.exit(f"no session matching {session!r} under {PROJECTS}")
        return hits[0]
    files = sorted(folder.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not files:
        sys.exit(f"no session under {folder}")
    return files[-1]


def text_of(content) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(x.get("text", "") for x in content if isinstance(x, dict) and x.get("type") == "text")


def as_prompt(raw: str) -> tuple[str, str] | None:
    """Return (kind, prompt) for a human-typed user message, None for harness noise."""
    s = raw.strip()
    if not s or s.startswith(("[Request interrupted", "Caveat:")):
        return None
    if "<command-name>" in s:
        name = re.search(r"<command-name>(.*?)</command-name>", s, re.S)
        args = re.search(r"<command-args>(.*?)</command-args>", s, re.S)
        return "commande", f"{name.group(1).strip()} {args.group(1).strip() if args else ''}".strip()
    if s.startswith("<"):
        return None
    return "prompt", s


def qa_lines(pairs) -> str:
    return "\n".join(f"{q} → {a}" for q, a in pairs)


def extract(path: Path) -> dict:
    turns, cur, project = [], None, ""
    names = {}  # tool_use_id -> tool name

    def open_turn(ts, kind, prompt):
        nonlocal cur
        cur = {"n": len(turns) + 1, "ts": ts, "kind": kind, "prompt": mask(prompt),
               "tools": collections.Counter(), "files": [], "reply_excerpt": "", "resume": ""}
        turns.append(cur)

    for line in path.open():
        r = json.loads(line)
        if r.get("isSidechain"):
            continue
        t, ts = r.get("type"), r.get("timestamp", "")
        project = project or r.get("cwd", "")
        if t == "attachment":
            a = r.get("attachment", {})
            if a.get("type") == "queued_command" and (a.get("origin") or {}).get("kind") == "human":
                open_turn(a.get("timestamp", ts), "en cours de tour", a.get("prompt", ""))
            continue
        msg = r.get("message") if isinstance(r.get("message"), dict) else {}
        content = msg.get("content")
        if t == "user" and not r.get("isMeta"):
            results = [x for x in content if x.get("type") == "tool_result"] if isinstance(content, list) else []
            if results:
                res = r.get("toolUseResult")
                for x in results:
                    if names.get(x.get("tool_use_id")) == "AskUserQuestion" and isinstance(res, dict) and isinstance(res.get("answers"), dict):
                        open_turn(ts, "réponse QCM", qa_lines(res["answers"].items()))
                    elif isinstance(res, str) and "the user said:" in res:
                        said = res.split("the user said:", 1)[1]
                        # A multiple-choice dialog closed to clarify keeps the answers given so far.
                        if partial := re.findall(r'- "(.+?)"\n\s+Answer: (.+)', said):
                            open_turn(ts, "réponse QCM partielle", qa_lines(partial))
                        else:
                            open_turn(ts, "refus avec consigne", said.strip())
                continue
            if (p := as_prompt(text_of(content or ""))):
                open_turn(ts, *p)
        elif t == "assistant" and isinstance(content, list) and cur:
            for x in content:
                if x.get("type") == "tool_use":
                    names[x["id"]] = x["name"]
                    cur["tools"][x["name"]] += 1
                    fp = (x.get("input") or {}).get("file_path")
                    if x["name"] in ("Edit", "Write", "NotebookEdit") and fp and mask(fp) not in cur["files"]:
                        cur["files"].append(mask(fp))
                elif x.get("type") == "text" and x.get("text", "").strip():
                    cur["reply_excerpt"] = mask(x["text"].strip())[:EXCERPT]
    for tr in turns:
        tr["tools"] = dict(tr["tools"].most_common())
    return {"session": path.stem, "project": mask(project), "turns": turns}


def render(data: dict) -> str:
    out = [f"# Comment j'ai prompté · session {data['session'][:8]}", "",
           f"Projet : `{data['project']}` · {len(data['turns'])} tours humains", ""]
    for tr in data["turns"]:
        tools = ", ".join(f"{k}×{v}" for k, v in tr["tools"].items())
        out += [f"## {tr['n']}. {tr['ts'][:10]} {tr['ts'][11:16]} · {tr['kind']}", "",
                "> " + tr["prompt"].replace("\n", "\n> "), ""]
        if tr.get("resume"):
            out.append(f"→ {tr['resume']}")
        if tools:
            out.append(f"<sub>outils : {tools}{' · fichiers : ' + ', '.join(tr['files']) if tr['files'] else ''}</sub>")
        out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("--session"), e.add_argument("--project"), e.add_argument("-o", "--out")
    rd = sub.add_parser("render")
    rd.add_argument("json"), rd.add_argument("-o", "--out")
    a = ap.parse_args()
    if a.cmd == "extract":
        text = json.dumps(extract(session_file(a.session, a.project)), ensure_ascii=False, indent=1)
    else:
        text = render(json.loads(Path(a.json).read_text()))
    if a.out:
        Path(a.out).write_text(text)
        print(a.out)
    else:
        print(text)


if __name__ == "__main__":
    main()
