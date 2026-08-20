from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "adapter"))

from build import REQUIRED_METADATA_FIELDS, load_manifest  # noqa: E402
from corpus_coverage import coverage  # noqa: E402


MANIFEST = ROOT / "adapter" / "manifest.yaml"
SOURCE_TASK = "matplotlib__matplotlib-25775"
TARGETS = {
    "matplotlib-25775__control",
    "matplotlib-25775__upstream-fix",
}


def matplotlib_entries():
    return [
        entry
        for entry in load_manifest(MANIFEST)
        if entry.metadata.get("source_task") == SOURCE_TASK
    ]


def test_matplotlib_manifest_metadata_is_complete():
    entries = matplotlib_entries()
    assert {entry.target_name for entry in entries} == TARGETS
    for entry in entries:
        assert set(entry.metadata) >= REQUIRED_METADATA_FIELDS
        assert entry.metadata["cheat_mode"] == entry.mode
        assert entry.metadata["verifier_shape"] == "swebench"
        assert entry.metadata["control_pair"] in TARGETS - {entry.target_name}


def test_manifest_schema_rejects_missing_metadata_field(tmp_path):
    data = yaml.safe_load(MANIFEST.read_text())
    entry = next(
        item
        for item in data["entries"]
        if item["target_name"] == "matplotlib-25775__upstream-fix"
    )
    del entry["metadata"]["detector_expectation"]
    invalid_manifest = tmp_path / "manifest.yaml"
    invalid_manifest.write_text(yaml.safe_dump(data))

    with pytest.raises(ValueError, match="detector_expectation"):
        load_manifest(invalid_manifest)


def test_generated_matplotlib_fixtures_expose_corpus_metadata():
    for target in TARGETS:
        task_toml = ROOT / "datasets" / "reward-hack" / target / "task.toml"
        metadata = tomllib.loads(task_toml.read_text())["metadata"]
        assert set(metadata) >= REQUIRED_METADATA_FIELDS
        assert metadata["source_task"] == SOURCE_TASK


def test_corpus_coverage_reports_matplotlib_axes_and_modes():
    report = coverage(load_manifest(MANIFEST))
    assert json.loads((ROOT / "corpus" / "coverage.json").read_text()) == report
    family = next(
        item
        for item in report["families"]
        if item["source_task"] == SOURCE_TASK
    )
    assert family["hack_axes"] == ["solution-retrieval"]
    assert family["cheat_modes"] == ["control", "upstream-fix"]
    assert {fixture["target_name"] for fixture in family["fixtures"]} == TARGETS
