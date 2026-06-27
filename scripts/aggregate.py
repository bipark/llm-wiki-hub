#!/usr/bin/env python3
"""
LLM-Wiki-Hub 집계 스크립트 (확장판)
- projects.txt 에 등록된 각 프로젝트 git 을 '읽기 전용'으로 순회한다.
- git 메타데이터 + STATUS.md + 미완료 할일 + ADR 을 긁어와 wiki/ 아래 대시보드를 생성한다.
- 어느 프로젝트 git 도 수정하지 않는다. 통합은 단방향(읽기)·멱등(재실행 안전)이다.

생성물:
    wiki/index.md   - 프로젝트별 요약 + 상세 + 정체/블로커 경고
    wiki/todos.md   - 모든 프로젝트의 미완료 할일 통합 리스트
    wiki/adr.md     - 모든 프로젝트의 결정사항(ADR) 통합 목록

설정 (환경변수):
    LLMWIKIHUB_STALE_DAYS=7  -> 마지막 커밋이 7일 넘으면 정체로 표시

사용법:
    python scripts/aggregate.py
"""

import subprocess
import datetime
import re
import os
import fnmatch
from pathlib import Path

HUB = Path(__file__).resolve().parent.parent
PROJECTS_FILE = HUB / "projects.txt"
WIKI = HUB / "wiki"

STALE_DAYS = int(os.environ.get("LLMWIKIHUB_STALE_DAYS", "7"))
ADR_DIRS = ["docs/adr", "adr", "wiki/decisions", "decisions"]

# 할일을 절대 긁지 않을 파생물/벤더 디렉토리 (경로 어딘가에 이 이름이 있으면 제외).
# 주의: 'wiki' 는 제외하지 않는다 — 어떤 프로젝트는 wiki/ 에 진짜 계획 문서를 둔다.
# llm-wiki-hub 자신의 생성물 자기참조는 아래 DEFAULT_TODO_GLOBS(task-명 파일만)로 이미 막힌다.
TODO_EXCLUDE_DIRS = {
    ".venv", "venv", "node_modules", "vendor",
    "build", "dist", "__pycache__", ".git",
}
# STATUS.md 에 `todos:` 가 없을 때의 기본 스캔 대상 = '할일 목적' 파일만.
# 설계문서/README/setup 문서의 체크박스 노이즈를 기본적으로 배제한다.
# 프로젝트가 STATUS.md 에 `todos: <glob>[, <glob>]` 를 적으면 그 글롭이 우선한다.
DEFAULT_TODO_GLOBS = [
    "TODO.md", "TODOS.md", "TODO.txt",
    "tasks.md", "*-tasks.md", "*_tasks.md",
    "PLAN.md", "*-plan.md", "*_plan.md", "ROADMAP.md", "STATUS.md",
]


def git(repo: Path, args: list[str]) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo)] + args,
            capture_output=True, text=True, timeout=15,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def read_projects() -> list[Path]:
    if not PROJECTS_FILE.exists():
        return []
    paths = []
    for line in PROJECTS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        paths.append(Path(line).expanduser())
    return paths


def parse_status(repo: Path) -> dict:
    meta = {}
    f = repo / "STATUS.md"
    if not f.exists():
        return meta
    in_comment = False
    for line in f.read_text(encoding="utf-8").splitlines():
        # HTML 주석(<!-- ... -->) 안의 설명줄은 파싱하지 않는다.
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if "<!--" in line:
            in_comment = "-->" not in line
            continue
        m = re.match(r"^\s*([a-zA-Z_]+)\s*:\s*(.+?)\s*$", line)
        if m:
            meta[m.group(1).lower()] = m.group(2)
    return meta


def status_body(repo: Path) -> str:
    """STATUS.md 에서 프런트매터(key: value)와 HTML 주석을 걷어낸 자유 메모만 반환."""
    f = repo / "STATUS.md"
    if not f.exists():
        return ""
    text = re.sub(r"<!--.*?-->", "", f.read_text(encoding="utf-8"), flags=re.S)
    body, started = [], False
    for line in text.splitlines():
        if not started:
            # 맨 위 제목/프런트매터/빈 줄은 건너뛰고, 첫 본문 줄부터 메모로 본다.
            if line.strip().startswith("#"):
                continue
            if re.match(r"^\s*[a-zA-Z_]+\s*:\s*.+$", line):
                continue
            if not line.strip():
                continue
            started = True
        body.append(line)
    return "\n".join(body).strip()


def _todo_excluded(rel: str) -> bool:
    return any(part in TODO_EXCLUDE_DIRS for part in Path(rel).parts)


def _matches_globs(rel: str, globs: list) -> bool:
    name = Path(rel).name
    for g in globs:
        # 글롭에 '/' 가 있으면 전체 경로로, 없으면 파일명으로 매칭.
        target = rel if "/" in g else name
        if fnmatch.fnmatch(target, g):
            return True
    return False


def collect_todos(repo: Path, globs: list) -> list:
    files = git(repo, ["ls-files", "*.md", "*.txt"])
    if not files:
        return []
    todos = []
    for rel in files.splitlines():
        if _todo_excluded(rel) or not _matches_globs(rel, globs):
            continue
        p = repo / rel
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                m = re.match(r"^\s*-\s*\[ \]\s*(.+?)\s*$", line)
                if m:
                    todos.append((rel, m.group(1)))
        except Exception:
            pass
    return todos


def collect_adrs(repo: Path) -> list:
    adrs = []
    for d in ADR_DIRS:
        adr_dir = repo / d
        if not adr_dir.is_dir():
            continue
        for f in sorted(adr_dir.glob("*.md")):
            try:
                text = f.read_text(encoding="utf-8")
            except Exception:
                continue
            title_m = re.search(r"^#\s+(.+)$", text, re.M)
            title = title_m.group(1).strip() if title_m else f.stem
            st_m = re.search(r"^\s*status\s*:\s*(.+)$", text, re.M | re.I)
            status = st_m.group(1).strip() if st_m else "-"
            adrs.append({"file": f.name, "title": title, "status": status})
        break
    return adrs


def days_since(date_str: str):
    try:
        d = datetime.datetime.strptime(date_str.split()[0], "%Y-%m-%d").date()
        return (datetime.date.today() - d).days
    except Exception:
        return None


def ago_label(delta):
    if delta is None:
        return "?"
    if delta == 0:
        return "오늘"
    if delta == 1:
        return "어제"
    return f"{delta}일 전"


def collect(repo: Path) -> dict:
    name = repo.name
    if not (repo / ".git").exists():
        return {"name": name, "ok": False, "reason": "git 저장소 아님 또는 경로 없음",
                "path": str(repo)}

    last_date = git(repo, ["log", "-1", "--format=%cd", "--date=format:%Y-%m-%d %H:%M"])
    last_msg = git(repo, ["log", "-1", "--format=%s"])
    branch = git(repo, ["branch", "--show-current"]) or "(detached)"
    dirty = git(repo, ["status", "--porcelain"])
    dirty_files = dirty.splitlines() if dirty else []
    uncommitted = len(dirty_files)
    recent = git(repo, ["log", "-10", "--format=%cd  %s", "--date=format:%Y-%m-%d"])
    recent_commits = recent.splitlines() if recent else []
    meta = parse_status(repo)
    if meta.get("todos"):
        globs = [g.strip() for g in meta["todos"].split(",") if g.strip()]
    else:
        globs = DEFAULT_TODO_GLOBS
    todos = collect_todos(repo, globs)
    adrs = collect_adrs(repo)
    delta = days_since(last_date)
    stale = delta is not None and delta > STALE_DAYS

    return {
        "name": name, "ok": True, "branch": branch, "last_date": last_date,
        "delta": delta, "ago": ago_label(delta), "stale": stale, "path": str(repo),
        "last_msg": last_msg, "uncommitted": uncommitted, "todos": todos, "adrs": adrs,
        "dirty_files": dirty_files, "recent": recent_commits, "memo": status_body(repo),
        "status": meta.get("status", "-"), "milestone": meta.get("milestone", "-"),
        "blockers": meta.get("blockers", "-"), "updated": meta.get("updated", "-"),
    }


def slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-") or "project"


def build_sidebar(rows):
    """docsify 네비게이션용 _sidebar.md."""
    lines = [
        "- [📊 대시보드](index.md)",
        "- [✅ 통합 할일](todos.md)",
        "- [📐 결정사항(ADR)](adr.md)",
        "- 프로젝트",
    ]
    for r in rows:
        lines.append(f"  - [{r['name']}](projects/{slug(r['name'])}.md)")
    return "\n".join(lines) + "\n"


def header(now: str, regen_note: str) -> list:
    return [f"_자동 생성됨: {now} · `{regen_note}` · 직접 편집하지 말 것_", ""]


def build_index(rows, now):
    lines = ["# 프로젝트 대시보드", ""]
    lines += header(now, "scripts/aggregate.py")

    stale_rows = [r for r in rows if r.get("ok") and r.get("stale")]
    blocked_rows = [r for r in rows if r.get("ok") and r.get("status", "").lower() == "blocked"]
    if stale_rows or blocked_rows:
        lines += ["## ⚠️ 주의", ""]
        for r in blocked_rows:
            lines.append(f"- 🚫 **{r['name']}** — blocked: {r['blockers']}")
        for r in stale_rows:
            lines.append(f"- 💤 **{r['name']}** — {r['delta']}일째 커밋 없음 (정체)")
        lines.append("")

    lines += [
        "## 요약", "",
        "| 프로젝트 | 상태 | 브랜치 | 마지막 커밋 | 미커밋 | 할일 | ADR | 마일스톤 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        page = f"projects/{slug(r['name'])}.md"
        if not r["ok"]:
            lines.append(f"| **[{r['name']}]({page})** | ⚠️ {r['reason']} | - | - | - | - | - | - |")
            continue
        dirty_flag = f"⚠️{r['uncommitted']}" if r["uncommitted"] else "✓"
        ago = ("💤 " if r["stale"] else "") + r["ago"]
        lines.append(
            f"| **[{r['name']}]({page})** | {r['status']} | `{r['branch']}` | "
            f"{ago} | {dirty_flag} | {len(r['todos'])} | {len(r['adrs'])} | {r['milestone']} |"
        )

    lines += ["", "## 상세", ""]
    for r in rows:
        page = f"projects/{slug(r['name'])}.md"
        if not r["ok"]:
            lines += [f"### [{r['name']}]({page})", f"- ⚠️ {r['reason']}", ""]
            continue
        stale_tag = "  ·  💤 정체" if r["stale"] else ""
        lines += [
            f"### [{r['name']}]({page})",
            f"- 상태: {r['status']}  ·  마일스톤: {r['milestone']}{stale_tag}",
            f"- 마지막 커밋: {r['last_date']} ({r['ago']}) — {r['last_msg']}",
            f"- 브랜치: `{r['branch']}`  ·  미커밋 변경: {r['uncommitted']}개  ·  "
            f"미완료 할일: {len(r['todos'])}개  ·  ADR: {len(r['adrs'])}개",
            f"- 블로커: {r['blockers']}  ·  [자세히 →]({page})", "",
        ]
    lines += ["---", "", "관련: [통합 할일](todos.md) · [결정사항(ADR)](adr.md)", ""]
    return "\n".join(lines) + "\n"


def build_todos(rows, now):
    lines = ["# 통합 할일", ""]
    lines += header(now, "scripts/aggregate.py")
    total = sum(len(r["todos"]) for r in rows if r.get("ok"))
    lines += [f"전체 미완료: **{total}개**", ""]
    for r in rows:
        if not r.get("ok") or not r["todos"]:
            continue
        lines += [f"## {r['name']} ({len(r['todos'])})", ""]
        for path, text in r["todos"]:
            lines.append(f"- [ ] {text}  _<sub>{path}</sub>_")
        lines.append("")
    if total == 0:
        lines += ["_미완료 할일이 없습니다._", ""]
    return "\n".join(lines) + "\n"


def build_adr(rows, now):
    lines = ["# 결정사항 (ADR) 통합", ""]
    lines += header(now, "scripts/aggregate.py")
    total = sum(len(r["adrs"]) for r in rows if r.get("ok"))
    lines += [f"전체 ADR: **{total}개**", ""]
    for r in rows:
        if not r.get("ok") or not r["adrs"]:
            continue
        lines += [f"## {r['name']} ({len(r['adrs'])})", ""]
        lines += ["| 파일 | 제목 | 상태 |", "|---|---|---|"]
        for a in r["adrs"]:
            lines.append(f"| `{a['file']}` | {a['title']} | {a['status']} |")
        lines.append("")
    if total == 0:
        lines += [
            "_수집된 ADR 이 없습니다._", "",
            f"_ADR 은 각 프로젝트의 다음 디렉토리에서 찾습니다: {', '.join(ADR_DIRS)}_", "",
        ]
    return "\n".join(lines) + "\n"


def build_project_page(r, now):
    name = r["name"]
    lines = [f"# {name}", ""]
    lines += header(now, "scripts/aggregate.py")
    if not r.get("ok"):
        lines += [f"- ⚠️ {r['reason']}", f"- 경로: `{r.get('path', '-')}`", "",
                  "[← 대시보드](../index.md)", ""]
        return "\n".join(lines) + "\n"

    stale_tag = "  ·  💤 정체" if r["stale"] else ""
    lines += [
        f"- 상태: **{r['status']}**  ·  마일스톤: {r['milestone']}{stale_tag}",
        f"- 브랜치: `{r['branch']}`  ·  마지막 커밋: {r['last_date']} ({r['ago']})",
        f"- 미커밋: {r['uncommitted']}개  ·  미완료 할일: {len(r['todos'])}개  ·  ADR: {len(r['adrs'])}개",
        f"- 블로커: {r['blockers']}",
        f"- 경로: `{r['path']}`  ·  갱신: {r['updated']}",
        "",
        "## 최근 커밋 (최대 10)", "",
    ]
    lines += [f"- {c}" for c in r["recent"]] or ["_없음_"]
    lines.append("")

    if r["dirty_files"]:
        lines += [f"## 미커밋 변경 ({r['uncommitted']})", ""]
        lines += [f"- `{d}`" for d in r["dirty_files"]]
        lines.append("")

    if r["memo"]:
        lines += ["## 메모 (STATUS.md)", "", r["memo"], ""]

    lines += [f"## 할일 ({len(r['todos'])})", ""]
    if r["todos"]:
        for path, text in r["todos"]:
            lines.append(f"- [ ] {text}  _<sub>{path}</sub>_")
    else:
        lines.append("_없음_")
    lines.append("")

    lines += [f"## ADR ({len(r['adrs'])})", ""]
    if r["adrs"]:
        lines += ["| 파일 | 제목 | 상태 |", "|---|---|---|"]
        for a in r["adrs"]:
            lines.append(f"| `{a['file']}` | {a['title']} | {a['status']} |")
    else:
        lines.append("_없음_")
    lines += ["", "---", "", "[← 대시보드](../index.md)  ·  [통합 할일](../todos.md)  ·  [ADR](../adr.md)", ""]
    return "\n".join(lines) + "\n"


def write_project_pages(rows, now):
    pdir = WIKI / "projects"
    pdir.mkdir(parents=True, exist_ok=True)
    keep = set()
    for r in rows:
        fname = f"{slug(r['name'])}.md"
        keep.add(fname)
        (pdir / fname).write_text(build_project_page(r, now), encoding="utf-8")
    # projects.txt 에서 빠진 프로젝트의 옛 페이지는 제거 (멱등 유지).
    for f in pdir.glob("*.md"):
        if f.name not in keep:
            f.unlink()


def main():
    projects = read_projects()
    if not projects:
        print("projects.txt 가 비어 있습니다. 프로젝트 경로를 한 줄에 하나씩 추가하세요.")
        return
    rows = [collect(p) for p in projects]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    WIKI.mkdir(parents=True, exist_ok=True)
    (WIKI / "index.md").write_text(build_index(rows, now), encoding="utf-8")
    (WIKI / "todos.md").write_text(build_todos(rows, now), encoding="utf-8")
    (WIKI / "adr.md").write_text(build_adr(rows, now), encoding="utf-8")
    (WIKI / "_sidebar.md").write_text(build_sidebar(rows), encoding="utf-8")
    write_project_pages(rows, now)

    ok = sum(1 for r in rows if r["ok"])
    stale = sum(1 for r in rows if r.get("ok") and r.get("stale"))
    todos = sum(len(r["todos"]) for r in rows if r.get("ok"))
    adrs = sum(len(r["adrs"]) for r in rows if r.get("ok"))
    print("생성 완료: index.md / todos.md / adr.md / projects/*.md / _sidebar.md")
    print(f"  프로젝트 {ok}/{len(rows)} · 정체 {stale} · 통합 할일 {todos} · ADR {adrs}")


if __name__ == "__main__":
    main()
