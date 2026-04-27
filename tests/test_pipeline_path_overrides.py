import importlib
import sys
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def launch_pipeline_module():
    return importlib.reload(importlib.import_module("launch_pipeline"))


@pytest.fixture
def launch_analysis_module():
    return importlib.reload(importlib.import_module("launch_analysis_pipeline"))


@pytest.fixture
def pipeline_update_module():
    return importlib.reload(importlib.import_module("pipeline_update"))


@pytest.fixture
def pipeline_orchestrate_module():
    return importlib.reload(importlib.import_module("pipeline_orchestrate"))


@pytest.fixture
def template_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / "templates").mkdir(parents=True)
    (workspace / "templates" / "research-pipeline.md").write_text(
        "# Research Pipeline Template\n\n"
        "## Stage Transitions\n"
        "```yaml\n"
        "first_agent: architect\n"
        "type: research\n"
        "phases:\n"
        "  1:\n"
        "    stages:\n"
        "      - { role: architect, action: design, session: fresh }\n"
        "      - { role: critic, action: design_review, session: fresh }\n"
        "    gate: human\n"
        "```\n"
    )
    return workspace


def _load_frontmatter(path: Path) -> dict:
    text = path.read_text()
    _, fm_text, _ = text.split("---", 2)
    return yaml.safe_load(fm_text)


def test_launch_pipeline_accepts_custom_relative_artifact_paths(
    launch_pipeline_module, template_workspace
):
    workspace = template_workspace
    monkey_targets = {
        "WORKSPACE": workspace,
        "PIPELINES_DIR": workspace / "pipelines",
        "FINANCE_DIR": workspace / "machinelearning" / "snn_applied_finance",
        "BUILDS_DIR": workspace / "machinelearning" / "school" / "helicopter_nn" / "research" / "pipeline_builds",
        "SPECS_DIR": workspace / "machinelearning" / "school" / "helicopter_nn" / "specs",
        "NOTEBOOKS_DIR": workspace / "machinelearning" / "school" / "helicopter_nn" / "notebooks",
    }
    for name, value in monkey_targets.items():
        setattr(launch_pipeline_module, name, value)

    pipeline_file = launch_pipeline_module.create_pipeline(
        "heli-v1",
        "helicopter colab notebook",
        project="machinelearning-school",
        tags=["helicopter", "colab"],
        pipeline_type="research",
        project_root="machinelearning/school/helicopter_nn",
        builds_dir="machinelearning/school/helicopter_nn/research/pipeline_builds",
        spec_file="machinelearning/school/helicopter_nn/specs/heli-v1_spec.yaml",
        output_notebook="machinelearning/school/helicopter_nn/notebooks/heli-v1.ipynb",
    )

    frontmatter = _load_frontmatter(pipeline_file)
    assert frontmatter["project"] == "machinelearning-school"
    assert frontmatter["project_root"] == "machinelearning/school/helicopter_nn"
    assert frontmatter["pipeline_builds_dir"] == "machinelearning/school/helicopter_nn/research/pipeline_builds"
    assert frontmatter["spec_file"] == "machinelearning/school/helicopter_nn/specs/heli-v1_spec.yaml"
    assert frontmatter["output_notebook"] == "machinelearning/school/helicopter_nn/notebooks/heli-v1.ipynb"


def test_launch_pipeline_accepts_absolute_output_notebook_path(
    launch_pipeline_module, template_workspace, tmp_path
):
    workspace = template_workspace
    absolute_notebook = tmp_path / "external" / "heli.ipynb"

    monkey_targets = {
        "WORKSPACE": workspace,
        "PIPELINES_DIR": workspace / "pipelines",
        "FINANCE_DIR": workspace / "machinelearning" / "snn_applied_finance",
        "BUILDS_DIR": workspace / "machinelearning" / "school" / "helicopter_nn" / "research" / "pipeline_builds",
        "SPECS_DIR": workspace / "machinelearning" / "school" / "helicopter_nn" / "specs",
        "NOTEBOOKS_DIR": workspace / "machinelearning" / "school" / "helicopter_nn" / "notebooks",
    }
    for name, value in monkey_targets.items():
        setattr(launch_pipeline_module, name, value)

    pipeline_file = launch_pipeline_module.create_pipeline(
        "heli-v2",
        "absolute output path",
        project_root="machinelearning/school/helicopter_nn",
        builds_dir="machinelearning/school/helicopter_nn/research/pipeline_builds",
        spec_file="machinelearning/school/helicopter_nn/specs/heli-v2_spec.yaml",
        output_notebook=str(absolute_notebook),
    )

    frontmatter = _load_frontmatter(pipeline_file)
    assert frontmatter["output_notebook"] == str(absolute_notebook)


def test_launch_analysis_pipeline_accepts_custom_input_and_output_paths(
    launch_analysis_module, template_workspace, tmp_path
):
    workspace = template_workspace
    custom_pkl_dir = tmp_path / "inputs" / "helicopter-pkls"
    custom_output = "machinelearning/school/helicopter_nn/notebooks/heli-analysis.ipynb"

    monkey_targets = {
        "WORKSPACE": workspace,
        "PIPELINES_DIR": workspace / "pipelines",
        "FINANCE_DIR": workspace / "machinelearning" / "snn_applied_finance",
        "BUILDS_DIR": workspace / "machinelearning" / "school" / "helicopter_nn" / "research" / "pipeline_builds",
        "NOTEBOOKS_DIR": workspace / "machinelearning" / "school" / "helicopter_nn" / "notebooks",
    }
    for name, value in monkey_targets.items():
        setattr(launch_analysis_module, name, value)

    pipeline_file = launch_analysis_module.create_pipeline(
        "heli-analysis-v1",
        "analysis pipeline",
        source_version="heli-v1",
        source_pkl=str(custom_pkl_dir),
        project="machinelearning-school",
        tags=["helicopter", "analysis"],
        project_root="machinelearning/school/helicopter_nn",
        builds_dir="machinelearning/school/helicopter_nn/research/pipeline_builds",
        output_notebook=custom_output,
    )

    frontmatter = _load_frontmatter(pipeline_file)
    assert frontmatter["project_root"] == "machinelearning/school/helicopter_nn"
    assert frontmatter["pipeline_builds_dir"] == "machinelearning/school/helicopter_nn/research/pipeline_builds"
    assert frontmatter["source_pkl_dir"] == str(custom_pkl_dir)
    assert frontmatter["output_notebook"] == custom_output


def test_pipeline_update_saves_block_artifact_in_custom_builds_dir(
    pipeline_update_module, template_workspace
):
    workspace = template_workspace
    (workspace / "pipelines").mkdir(exist_ok=True)
    (workspace / "machinelearning" / "school" / "helicopter_nn" / "research" / "pipeline_builds").mkdir(parents=True)
    pipeline_file = workspace / "pipelines" / "heli-v3.md"
    pipeline_file.write_text(
        "---\n"
        "primitive: pipeline\n"
        "status: phase1_design\n"
        "type: research\n"
        "version: heli-v3\n"
        "pipeline_builds_dir: machinelearning/school/helicopter_nn/research/pipeline_builds\n"
        "started: 2026-04-27\n"
        "---\n"
        "\n# heli-v3\n"
    )

    monkey_targets = {
        "WORKSPACE": workspace,
        "PIPELINES_DIR": workspace / "pipelines",
        "BUILDS_DIR": workspace / "pipeline_builds",
        "RESEARCH_BUILDS_DIR": workspace / "machinelearning" / "snn_applied_finance" / "research" / "pipeline_builds",
    }
    for name, value in monkey_targets.items():
        setattr(pipeline_update_module, name, value)

    assert pipeline_update_module._builds_artifact_ref("heli-v3", "critic.md") == (
        "machinelearning/school/helicopter_nn/research/pipeline_builds/critic.md"
    )


def test_pipeline_orchestrate_resolve_build_path_honors_custom_builds_dir(
    pipeline_orchestrate_module, template_workspace
):
    workspace = template_workspace
    custom_builds = workspace / "machinelearning" / "school" / "helicopter_nn" / "research" / "pipeline_builds"
    custom_builds.mkdir(parents=True)
    (workspace / "pipelines").mkdir(exist_ok=True)
    pipeline_file = workspace / "pipelines" / "heli-v4.md"
    pipeline_file.write_text(
        "---\n"
        "primitive: pipeline\n"
        "status: phase1_design\n"
        "type: research\n"
        "version: heli-v4\n"
        "pipeline_builds_dir: machinelearning/school/helicopter_nn/research/pipeline_builds\n"
        "output_notebook: machinelearning/school/helicopter_nn/notebooks/heli-v4.ipynb\n"
        "started: 2026-04-27\n"
        "---\n"
        "\n# heli-v4\n"
    )
    expected = custom_builds / "heli-v4_architect_design.md"
    expected.write_text("design")

    monkey_targets = {
        "WORKSPACE": workspace,
        "PIPELINES_DIR": workspace / "pipelines",
        "BUILDS_DIR": workspace / "pipeline_builds",
        "RESEARCH_BUILDS_DIR": workspace / "machinelearning" / "snn_applied_finance" / "research" / "pipeline_builds",
    }
    for name, value in monkey_targets.items():
        setattr(pipeline_orchestrate_module, name, value)

    resolved = pipeline_orchestrate_module.resolve_build_path("heli-v4", "architect_design.md")
    assert resolved == expected
