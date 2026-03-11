"""Integration tests: define 3 skills on disk, run searches, assert ranking."""

import pytest
from pathlib import Path
from skills_on_demand.server import load_index, _indexes

SKILLS = {
    "biopython": (
        "biopython",
        "Toolkit for biological sequence manipulation, FASTA/GenBank parsing, "
        "NCBI/PubMed access via Bio.Entrez, BLAST automation, and phylogenetics.",
        "Use for batch processing DNA, RNA, or protein sequences.",
    ),
    "scanpy": (
        "scanpy",
        "Single-cell RNA-seq analysis pipeline: QC, normalization, PCA, UMAP, "
        "clustering, and differential expression.",
        "Use for exploratory scRNA-seq analysis with established workflows.",
    ),
    "alphafold-database": (
        "alphafold-database",
        "Access AlphaFold 200M+ AI-predicted protein 3D structures by UniProt ID.",
        "Use when you need pre-computed protein structure predictions.",
    ),
}

SKILL_MD = """\
---
name: {name}
description: {description}
---

{body}
"""


@pytest.fixture()
def skills_dir(tmp_path: Path) -> Path:
    for folder, (name, description, body) in SKILLS.items():
        skill_path = tmp_path / folder
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text(
            SKILL_MD.format(name=name, description=description, body=body)
        )
    # Ensure this tmp_path is not already cached from a previous test run
    _indexes.pop(tmp_path.resolve(), None)
    return tmp_path


def test_protein_structure_query_ranks_alphafold_first(skills_dir: Path) -> None:
    idx = load_index(skills_dir)
    results = idx.search("protein structure prediction", top_k=3)
    assert results[0]["name"] == "alphafold-database"


def test_single_cell_rna_query_ranks_scanpy_first(skills_dir: Path) -> None:
    idx = load_index(skills_dir)
    results = idx.search("single cell RNA sequencing clustering", top_k=3)
    assert results[0]["name"] == "scanpy"


def test_sequence_parsing_query_ranks_biopython_first(skills_dir: Path) -> None:
    idx = load_index(skills_dir)
    results = idx.search("DNA sequence FASTA parsing NCBI", top_k=3)
    assert results[0]["name"] == "biopython"


def test_no_match_returns_empty(skills_dir: Path) -> None:
    idx = load_index(skills_dir)
    results = idx.search("quantum computing superconducting qubit")
    assert results == []


def test_load_index_raises_without_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SKILLS_DIR", raising=False)
    with pytest.raises(ValueError, match="SKILLS_DIR"):
        load_index(None)
