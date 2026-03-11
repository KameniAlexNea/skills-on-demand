# skills-on-demand

An MCP server that lets agents **discover and search skills on demand**.  
It scans a folder of `SKILL.md` files, builds a BM25 full-text index, and
exposes two MCP tools — `search_skills` and `list_skills` — that any
MCP-compatible agent (Claude Code, Claude Desktop, …) can call at runtime
to find the right skill for a task.

---

## Requirements

- Python ≥ 3.13
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

---

## Installation

### Into another project (recommended)

Add it as a dependency in the consuming project's `pyproject.toml`:

```toml
[project]
dependencies = [
    "skills-on-demand @ git+https://github.com/your-org/skills-on-demand.git",
]
```

Or install directly with uv/pip:

```bash
# with uv
uv pip install "git+https://github.com/your-org/skills-on-demand.git"

# with pip
pip install "git+https://github.com/your-org/skills-on-demand.git"
```

### From a local clone

```bash
git clone https://github.com/your-org/skills-on-demand.git
cd skills-on-demand
uv pip install -e "."
```

---

## Skills folder format

The server scans any folder recursively for files named **`SKILL.md`**.  
Each file must contain a YAML frontmatter block with at least a `description`
field. The `name` field is optional — the parent directory name is used as
fallback.

```
my-skills/
├── biopython/
│   └── SKILL.md
├── scanpy/
│   └── SKILL.md
└── alphafold-database/
    └── SKILL.md
```

Minimal `SKILL.md`:

```markdown
---
name: biopython
description: Toolkit for sequence manipulation, file parsing (FASTA/GenBank/PDB),
  phylogenetics, and NCBI/PubMed access.
---

# Biopython
...full skill instructions...
```

BM25 scoring indexes the `name`, `description`, **and the full body** of each
file, so detailed skill documents surface better results.

---

## Configuration

| Env variable  | Default | Description |
|---|---|---|
| `SKILLS_DIR`  | `<package-root>/claude-scientific-skills/scientific-skills` | Absolute path to the folder containing `SKILL.md` files |

---

## Usage

### As an MCP server in Claude Code

Add the server to your Claude Code MCP configuration (`~/.claude.json`):

```json
{
  "mcpServers": {
    "skills-on-demand": {
      "command": "/path/to/.venv/bin/skills-on-demand",
      "env": {
        "SKILLS_DIR": "/path/to/your/skills/folder"
      }
    }
  }
}
```

Or, using `uvx` so no separate install is needed:

```json
{
  "mcpServers": {
    "skills-on-demand": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/your-org/skills-on-demand.git",
        "skills-on-demand"
      ],
      "env": {
        "SKILLS_DIR": "/path/to/your/skills/folder"
      }
    }
  }
}
```

### As an MCP server in Claude Desktop

Add the same block inside the `mcpServers` key of
`~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or the equivalent path on your OS.

### From the Claude Code SDK (programmatic)

```python
import asyncio
from claude_code_sdk import ClaudeCodeOptions, query

async def main():
    options = ClaudeCodeOptions(
        mcp_servers={
            "skills-on-demand": {
                "command": "skills-on-demand",
                "env": {"SKILLS_DIR": "/path/to/skills"},
            }
        },
        allowed_tools=["mcp__skills-on-demand__search_skills",
                        "mcp__skills-on-demand__list_skills"],
    )

    # Ask the agent to find a relevant skill
    async for message in query(
        prompt="Find the best skill for analyzing single-cell RNA-seq data.",
        options=options,
    ):
        print(message)

asyncio.run(main())
```

### From the command line

```bash
# Start the MCP server on stdio (default transport):
skills-on-demand

# Point at a custom skills folder:
SKILLS_DIR=/path/to/skills skills-on-demand
```

### From Python

```python
from skills_on_demand.server import load_index

idx = load_index("/path/to/skills")          # or rely on SKILLS_DIR env var

# List all skills
print(idx.skills[0]["name"])

# BM25 search — returns ranked list of dicts
results = idx.search("protein structure prediction", top_k=5)
for r in results:
    print(f"[{r['score']}] {r['name']}: {r['description']}")
```

Example output:

```
[8.06] torchdrug: PyTorch-native graph neural networks for molecules and proteins.
[7.99] esm: Comprehensive toolkit for protein language models including ESM3.
[7.65] alphafold-database: Access AlphaFold 200M+ AI-predicted protein structures.
```

---

## MCP tools reference

### `search_skills`

Search indexed skills using BM25 full-text ranking.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | `str` | — | Natural-language description of what you need |
| `top_k` | `int` | `5` | Maximum number of results to return |

Returns a list of objects:

```json
[
  {
    "name": "alphafold-database",
    "description": "Access AlphaFold 200M+ AI-predicted protein structures.",
    "path": "alphafold-database/SKILL.md",
    "score": 7.6539
  }
]
```

Only skills with a score `> 0` are returned.

### `list_skills`

Return the names of all indexed skills. No parameters.

```json
["biopython", "scanpy", "alphafold-database", "...]
```

---

## License

See [LICENSE](LICENSE) (if present) or the consuming project's license.

