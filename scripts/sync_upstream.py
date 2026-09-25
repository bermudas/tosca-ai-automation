#!/usr/bin/env python3
"""Sync vendored skills/tools from upstream repos with a 3-way merge.

    python3 scripts/sync_upstream.py check  [--source NAME] [--ref REF]
    python3 scripts/sync_upstream.py apply  [--source NAME] [--ref REF]
    python3 scripts/sync_upstream.py validate

check    - fetch upstream, list new commits and which mapped / watched files changed. No writes.
apply    - merge upstream changes into the repo: base = locked commit, ours = repo file,
           theirs = new commit. Rewrite rules from upstream.json are applied to base and theirs
           so local path adaptations carry over. Conflicts are left as <<<<<<< markers.
           Updates upstream.lock.json.
validate - repo consistency checks (skill names, agent skill refs, relative links, JSON configs).

Config: upstream.json, lock: upstream.lock.json, cache: .cache/upstream/ (gitignored).
Requires git on PATH.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "upstream.json"
LOCK = ROOT / "upstream.lock.json"
CACHE = ROOT / ".cache" / "upstream"


def git(repo: Path, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def git_bytes(repo: Path, *args: str) -> bytes | None:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def ensure_clone(name: str, url: str, ref: str) -> Path:
    path = CACHE / name
    if not (path / ".git").exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        # full (not blob-less) clone: the merge reads hundreds of blobs, lazy fetching is far too slow
        subprocess.run(["git", "clone", "--quiet", "--no-checkout", url, str(path)], check=True)
    git(path, "fetch", "--quiet", "origin", ref)
    return path


def resolve(repo: Path, ref: str) -> str:
    for cand in (f"origin/{ref}", ref, "FETCH_HEAD"):
        out = git(repo, "rev-parse", "--verify", "--quiet", f"{cand}^{{commit}}", check=False).strip()
        if out:
            return out
    raise RuntimeError(f"cannot resolve ref {ref}")


def has_commit(repo: Path, sha: str) -> bool:
    def present() -> bool:
        return subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{sha}^{{commit}}"],
                              capture_output=True).returncode == 0
    if present():
        return True
    subprocess.run(["git", "-C", str(repo), "fetch", "--quiet", "origin", sha], capture_output=True)
    return present()


def ls_tree(repo: Path, sha: str, path: str) -> list[str]:
    out = git(repo, "ls-tree", "-r", "--name-only", sha, "--", path, check=False)
    return [l for l in out.splitlines() if l]


def expand_map(repo: Path, sha: str | None, mapping: list[dict]) -> dict[str, str]:
    """Return {dest_path: src_path} for every file under the mappings at commit sha."""
    files: dict[str, str] = {}
    if sha is None:
        return files
    for m in mapping:
        if "src_children" in m:
            base = m["src_children"].rstrip("/")
            for f in ls_tree(repo, sha, base):
                rel = f[len(base) + 1:]
                files[f"{m['dest_parent'].rstrip('/')}/{rel}"] = f
        else:
            src = m["src"].rstrip("/")
            for f in ls_tree(repo, sha, src):
                rel = f[len(src):].lstrip("/")
                files[m["dest"] if not rel else f"{m['dest'].rstrip('/')}/{rel}"] = f
    return files


def rewrite(dest: str, data: bytes, rules: list[dict]) -> bytes:
    applicable = [r for r in rules if fnmatch.fnmatch(dest, r["dest_glob"])]
    if not applicable:
        return data
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    for r in applicable:
        text = re.sub(r["find"], r["replace"], text)
    return text.encode("utf-8")


def merge3(ours: bytes, base: bytes, theirs: bytes, label: str) -> tuple[bytes, bool]:
    with tempfile.TemporaryDirectory() as td:
        o, b, t = Path(td, "ours"), Path(td, "base"), Path(td, "theirs")
        o.write_bytes(ours); b.write_bytes(base); t.write_bytes(theirs)
        r = subprocess.run(["git", "merge-file", "-L", f"{label} (repo)", "-L", "base", "-L", f"{label} (upstream)",
                            str(o), str(b), str(t)], capture_output=True)
        return o.read_bytes(), r.returncode != 0


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def sources(cfg: dict, only: str | None):
    for name, src in cfg["sources"].items():
        if only and name != only:
            continue
        yield name, src


def cmd_check(args) -> int:
    cfg, lock = load_json(CONFIG), load_json(LOCK)
    for name, src in sources(cfg, args.source):
        repo = ensure_clone(name, src["repo"], args.ref or src["ref"])
        new = resolve(repo, args.ref or src["ref"])
        old = lock.get(name, {}).get("commit")
        print(f"\n## {name}  ({src['repo']})")
        print(f"locked: {old or '-'}\nlatest: {new}")
        if old == new:
            print("up to date")
            continue
        if old and has_commit(repo, old):
            log = git(repo, "log", "--format=  %h %ad %s", "--date=short", f"{old}..{new}", check=False)
            print("commits:\n" + (log.rstrip() or "  (none on this ref)"))
        base_files = expand_map(repo, old if old and has_commit(repo, old) else None, src["map"])
        new_files = expand_map(repo, new, src["map"])
        changed, added, removed = [], [], []
        for dest, sp in new_files.items():
            if dest not in base_files:
                added.append(dest)
            elif git_bytes(repo, "show", f"{old}:{base_files[dest]}") != git_bytes(repo, "show", f"{new}:{sp}"):
                changed.append(dest)
        removed = [d for d in base_files if d not in new_files]
        for label, items in (("changed", changed), ("added", added), ("removed upstream", removed)):
            if items:
                print(f"{label} ({len(items)}):")
                for i in sorted(items):
                    print(f"  {i}")
        watch_changed = [w for w in src.get("watch", [])
                         if old and git_bytes(repo, "show", f"{old}:{w}") != git_bytes(repo, "show", f"{new}:{w}")]
        if watch_changed:
            print("watched files changed (merge by hand):")
            for w in watch_changed:
                print(f"  {w}   -> git -C {repo.relative_to(ROOT)} diff {old[:10]} {new[:10]} -- {w}")
        if old:
            for d in src.get("watch_new_dirs", []):
                diff = git(repo, "diff", "--name-status", old, new, "--", d, check=False)
                mapped = {v for v in new_files.values()} | set(src.get("watch", []))
                extra = [l for l in diff.splitlines() if l.split("\t")[-1] not in mapped
                         and not any(l.split("\t")[-1].startswith(p) for p in ("Tosca/Commander/MCP/cursor", "Tosca/Commander/MCP/windsurf",
                                     "Tosca/Commander/CLI/cursor", "Tosca/Commander/CLI/windsurf", "Tosca/Cloud/CLI/cursor", "Tosca/Cloud/CLI/windsurf"))]
                if extra:
                    print(f"other upstream changes under {d}/ (not vendored; review if relevant):")
                    for l in extra[:40]:
                        print(f"  {l}")
                    if len(extra) > 40:
                        print(f"  ... {len(extra) - 40} more")
    return 0


def cmd_apply(args) -> int:
    cfg, lock = load_json(CONFIG), load_json(LOCK)
    conflicts_total = 0
    for name, src in sources(cfg, args.source):
        repo = ensure_clone(name, src["repo"], args.ref or src["ref"])
        new = resolve(repo, args.ref or src["ref"])
        old = lock.get(name, {}).get("commit")
        if old and not has_commit(repo, old):
            print(f"!! {name}: locked commit {old} not found upstream; treating as first sync (no base)")
            old = None
        rules = src.get("rewrite", [])
        base_files = expand_map(repo, old, src["map"])
        new_files = expand_map(repo, new, src["map"])
        report = {k: [] for k in ("updated", "added", "conflict", "deleted", "kept-local-delete", "kept-local-change", "unchanged")}
        for dest, sp in sorted(new_files.items()):
            theirs = rewrite(dest, git_bytes(repo, "show", f"{new}:{sp}") or b"", rules)
            target = ROOT / dest
            base_raw = git_bytes(repo, "show", f"{old}:{base_files[dest]}") if old and dest in base_files else None
            base = rewrite(dest, base_raw, rules) if base_raw is not None else None
            if not target.exists():
                if base is not None:
                    report["kept-local-delete"].append(dest)  # we deleted it locally on purpose
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(theirs)
                report["added"].append(dest)
                continue
            ours = target.read_bytes()
            if ours == theirs or base == theirs:
                report["unchanged"].append(dest)
                continue
            if base is None:
                merged, conflict = merge3(ours, b"", theirs, dest)
            elif ours == base:
                merged, conflict = theirs, False
            else:
                merged, conflict = merge3(ours, base, theirs, dest)
            if merged == ours:
                report["unchanged"].append(dest)
                continue
            target.write_bytes(merged)
            report["conflict" if conflict else "updated"].append(dest)
        for dest in sorted(set(base_files) - set(new_files)):
            target = ROOT / dest
            if not target.exists():
                continue
            base = rewrite(dest, git_bytes(repo, "show", f"{old}:{base_files[dest]}") or b"", rules)
            if target.read_bytes() == base:
                target.unlink()
                report["deleted"].append(dest)
            else:
                report["kept-local-change"].append(dest + "  (removed upstream, but edited locally: decide)")
        print(f"\n## {name}: {old[:10] if old else '-'} -> {new[:10]}")
        for k, items in report.items():
            if k == "unchanged":
                print(f"unchanged: {len(items)}")
                continue
            if items:
                print(f"{k} ({len(items)}):")
                for i in items:
                    print(f"  {i}")
        conflicts_total += len(report["conflict"])
        date = git(repo, "log", "-1", "--format=%cI", new).strip()
        lock[name] = {"commit": new, "date": date, "synced": dt.date.today().isoformat()}
    LOCK.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    if conflicts_total:
        print(f"\n{conflicts_total} file(s) with conflict markers. Resolve them (grep -rn '^<<<<<<< ' .claude tools .github) and run validate.")
    return 1 if conflicts_total else 0


def cmd_validate(_args) -> int:
    problems: list[str] = []
    skills = ROOT / ".claude" / "skills"
    names = set()
    for d in sorted(p for p in skills.iterdir() if p.is_dir()):
        md = d / "SKILL.md"
        if not md.exists():
            problems.append(f"skill without SKILL.md: {d.name}")
            continue
        m = re.search(r"^name:\s*(\S+)", md.read_text(encoding="utf-8"), re.M)
        if not m or m.group(1).strip() != d.name:
            problems.append(f"skill name mismatch: dir {d.name} vs name {m.group(1) if m else None}")
        names.add(d.name)
    for agent in (ROOT / ".claude" / "agents").glob("*.md"):
        fm = agent.read_text(encoding="utf-8").split("---")[1]
        block = re.search(r"^skills:\s*\n((?:\s+-\s*\S+\s*\n)+)", fm, re.M)
        for s in re.findall(r"-\s*(\S+)", block.group(1)) if block else []:
            if s not in names:
                problems.append(f"{agent.name}: unknown skill {s}")
    agents_md = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for s in sorted(names):
        if f"`{s}`" not in agents_md:
            problems.append(f"skill not listed in AGENTS.md: {s}")
    link = re.compile(r"\]\(([^)#:\s]+\.(?:md|json|ps1|py|csx|mjs|sh))(?:#[^)]*)?\)")
    for f in list(ROOT.glob(".claude/**/*.md")) + list(ROOT.glob(".github/**/*.md")) + list(ROOT.glob("tools/**/*.md")) + [ROOT / "AGENTS.md"]:
        text = f.read_text(encoding="utf-8", errors="replace")
        if re.search(r"^<<<<<<< ", text, re.M):
            problems.append(f"conflict markers: {f.relative_to(ROOT)}")
        for l in link.findall(text):
            if not (f.parent / l).exists():
                problems.append(f"broken link: {f.relative_to(ROOT)} -> {l}")
    optional = {".mcp.json", ".vscode/mcp.json"}  # personal, gitignored; checked only if present
    for j in (".mcp.json.example", ".vscode/mcp.json.example", ".mcp.json", ".vscode/mcp.json",
              ".claude/settings.json", ".vscode/settings.json", "upstream.json", "upstream.lock.json"):
        if j in optional and not (ROOT / j).exists():
            continue
        try:
            json.loads((ROOT / j).read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            problems.append(f"invalid JSON {j}: {e}")
    for p in problems:
        print("✗", p)
    print("validate: OK" if not problems else f"validate: {len(problems)} problem(s)")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("check", "apply"):
        p = sub.add_parser(c)
        p.add_argument("--source", help="only this source (key in upstream.json)")
        p.add_argument("--ref", help="branch/tag/commit instead of the configured ref")
    sub.add_parser("validate")
    args = ap.parse_args()
    if args.cmd != "validate" and not shutil.which("git"):
        print("git is required", file=sys.stderr)
        return 2
    return {"check": cmd_check, "apply": cmd_apply, "validate": cmd_validate}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
