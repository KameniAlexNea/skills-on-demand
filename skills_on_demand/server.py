"""Skills on Demand — MCP server for BM25 skill search.

Usage
-----
# Run as MCP server (stdio transport, default):
    skills-on-demand

# Point at a custom skills folder:
    SKILLS_DIR=/path/to/skills skills-on-demand

# Quick test from the REPL:
    python -c "
    from skills_on_demand.server import load_index
    idx = load_index()
    print(idx.search('single cell RNA sequencing'))
    "
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from rank_bm25 import BM25Okapi

# ---------------------------------------------------------------------------
# Skill scanner
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (frontmatter_dict, body) from a markdown string."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw = m.group(1)
    body = text[m.end():]
    meta: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip()
    return meta, body.strip()


def scan_skills(skills_dir: str | Path) -> list[dict[str, Any]]:
    """Walk *skills_dir* recursively and load every SKILL.md found."""
    root = Path(skills_dir)
    skills: list[dict[str, Any]] = []
    for skill_file in sorted(root.rglob("SKILL.md")):
        try:
            text = skill_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        meta, body = _parse_frontmatter(text)
        name = meta.get("name") or skill_file.parent.name
        description = meta.get("description", "")
        skills.append(
            {
                "name": name,
                "description": description,
                "body": body,
                "path": str(skill_file.relative_to(root)),
            }
        )
    return skills


# ---------------------------------------------------------------------------
# BM25 index
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[^a-z0-9\s]")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.sub(" ", text.lower()).split()


class SkillIndex:
    def __init__(self, skills: list[dict[str, Any]]) -> None:
        self.skills = skills
        corpus = [
            _tokenize(f"{s['name']} {s['description']} {s['body']}")
            for s in skills
        ]
        self.bm25 = BM25Okapi(corpus)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        tokens = _tokenize(query)
        scores = self.bm25.get_scores(tokens)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [
            {
                "name": self.skills[i]["name"],
                "description": self.skills[i]["description"],
                "path": self.skills[i]["path"],
                "score": round(float(scores[i]), 4),
            }
            for i in ranked[:top_k]
            if scores[i] > 0
        ]


# ---------------------------------------------------------------------------
# Index cache (keyed by resolved path)
# ---------------------------------------------------------------------------

_indexes: dict[Path, SkillIndex] = {}


def load_index(skills_dir: str | Path | None = None) -> SkillIndex:
    """Load (or return cached) the skill index for *skills_dir*.

    The directory is resolved from, in order:
    1. The *skills_dir* argument.
    2. The ``SKILLS_DIR`` environment variable.

    Raises ``ValueError`` if neither is provided.
    Each unique resolved path gets its own cached index.
    """
    raw = skills_dir or os.environ.get("SKILLS_DIR")
    if not raw:
        raise ValueError(
            "No skills directory specified. "
            "Pass skills_dir= or set the SKILLS_DIR environment variable."
        )
    resolved = Path(raw).resolve()
    if resolved not in _indexes:
        _indexes[resolved] = SkillIndex(scan_skills(resolved))
    return _indexes[resolved]


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP("skills-on-demand")


@mcp.tool()
def search_skills(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Search available skills using BM25 full-text ranking.

    Args:
        query:  What you are looking for, e.g. "protein structure prediction"
        top_k:  Maximum number of results to return (default 5).
    """
    return load_index().search(query, top_k)


@mcp.tool()
def list_skills() -> list[str]:
    """Return the names of all indexed skills."""
    return [s["name"] for s in load_index().skills]


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
