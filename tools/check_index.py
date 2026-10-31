#!/usr/bin/env python3
"""Keep the index honest.

    python3 tools/check_index.py          # check README matches skills.json, and every entry is live
    python3 tools/check_index.py --write  # rewrite the README table from skills.json, then check

An entry is live when its repository is public and its skill file (or folder) exists on the
default branch. Set GITHUB_TOKEN to avoid the API's anonymous rate limit. Standard library only.
"""
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BEGIN, END = "<!-- index:begin -->", "<!-- index:end -->"


def load():
    with open(os.path.join(ROOT, "skills.json"), encoding="utf-8") as f:
        return json.load(f)


def table(skills):
    out = []
    for category in dict.fromkeys(s["category"] for s in skills):
        out += [f"### {category}", "", "| Skill | Repository | What it does |", "|---|---|---|"]
        for s in (s for s in skills if s["category"] == category):
            url = f"https://github.com/{s['repo']}"
            link = f"{url}/tree/HEAD/{s['path']}" if s["path"].startswith(".") else f"{url}/blob/HEAD/{s['path']}"
            out.append(f"| [`/{s['name']}`]({link}) | [{s['repo']}]({url}) | {s['description']} |")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def readme_with(skills):
    path = os.path.join(ROOT, "README.md")
    text = open(path, encoding="utf-8").read()
    head, rest = text.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    return path, text, f"{head}{BEGIN}\n{table(skills)}{END}{tail}"


def api(path):
    req = urllib.request.Request(f"https://api.github.com/{path}", headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, None


def main():
    skills = load()
    problems = []
    names = [s["name"] for s in skills]
    if len(names) != len(set(names)):
        problems.append("skills.json has a duplicate name")

    path, current, wanted = readme_with(skills)
    if "--write" in sys.argv:
        open(path, "w", encoding="utf-8").write(wanted)
        current = wanted
    if current != wanted:
        problems.append("README table is out of date: run python3 tools/check_index.py --write")

    for s in skills:
        status, repo = api(f"repos/{s['repo']}")
        if status != 200 or repo is None:
            problems.append(f"{s['name']}: {s['repo']} not reachable (HTTP {status}); private, renamed or deleted?")
            continue
        if repo.get("private"):
            problems.append(f"{s['name']}: {s['repo']} is private; remove it from the index")
            continue
        status, _ = api(f"repos/{s['repo']}/contents/{s['path']}")
        if status != 200:
            problems.append(f"{s['name']}: {s['path']} not found in {s['repo']} (HTTP {status})")

    for p in problems:
        print("FAIL", p)
    print(f"{len(skills)} skills checked, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
