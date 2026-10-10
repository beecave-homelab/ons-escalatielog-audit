"""Controleer de publicatiegrens en commitbinding van de Pages-workflow."""

import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
APP = "escalatielog-audit-webui.html"
WORKFLOW = yaml.load(
    (ROOT / ".github/workflows/deploy-pages.yml").read_text(), Loader=yaml.BaseLoader
)


def run_step(step, directory, **env):
    return subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", step["run"]],
        cwd=directory,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        check=False,
    )


def test_deployment_requires_ci_and_the_same_commit():
    assert set(WORKFLOW["on"]) == {"push", "workflow_dispatch"}
    assert WORKFLOW["on"]["push"]["branches"] == ["main"]
    assert WORKFLOW["permissions"] == {"contents": "read"}
    assert WORKFLOW["concurrency"] == {"group": "pages", "cancel-in-progress": "true"}
    jobs = WORKFLOW["jobs"]
    verify, deploy = jobs["verify"], jobs["deploy"]
    assert verify["needs"] == "pin"
    assert verify["uses"] == "./.github/workflows/ci.yml"
    revision = verify["with"]["revision"]
    assert revision == "${{ needs.pin.outputs.sha }}"
    assert set(deploy["needs"]) == {"pin", "verify"}
    assert "if" not in deploy  # Default success() blocks failed/skipped verification.
    assert deploy["permissions"] == {
        "contents": "read",
        "pages": "write",
        "id-token": "write",
    }
    assert deploy["environment"]["name"] == "github-pages"
    steps = deploy["steps"]
    assert steps[0]["uses"] == "actions/checkout@v4"
    assert steps[0]["with"]["ref"] == revision
    assert steps[0]["with"]["persist-credentials"] == "false"
    assert steps[1]["uses"] == "actions/configure-pages@v5"
    assert "enablement" not in steps[1].get("with", {})
    assert steps[-2]["uses"] == "actions/upload-pages-artifact@v4"
    assert steps[-2]["with"]["path"] == "${{ steps.stage.outputs.path }}"
    assert steps[-1]["uses"] == "actions/deploy-pages@v4"


@pytest.mark.parametrize(
    "ref,sha,accepted",
    [
        ("refs/heads/main", "a" * 40, True),
        ("refs/heads/dev", "a" * 40, False),
        ("refs/tags/0.14.0", "a" * 40, False),
        ("refs/pull/20/merge", "a" * 40, False),
        ("refs/heads/main", "main", False),
    ],
)
def test_pin_rejects_other_refs_and_invalid_commits(tmp_path, ref, sha, accepted):
    output = tmp_path / "output"
    step = WORKFLOW["jobs"]["pin"]["steps"][0]
    assert step["env"] == {"START_REF": "${{ github.ref }}", "START_SHA": "${{ github.sha }}"}
    assert WORKFLOW["jobs"]["pin"]["outputs"]["sha"] == "${{ steps.pin.outputs.sha }}"
    result = run_step(step, tmp_path, START_REF=ref, START_SHA=sha, GITHUB_OUTPUT=str(output))
    assert (result.returncode == 0) is accepted
    if accepted:
        assert output.read_text() == f"sha={sha}\n"
    else:
        assert not output.exists()


@pytest.mark.parametrize("source", ["regular", "missing", "symlink"])
def test_artifact_contains_only_unchanged_html(tmp_path, source):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    for name in ("escalatielogs/private.xlsx", "exports/private.html", "docs/note.md"):
        path = checkout / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Do not publish")
    app = checkout / APP
    if source == "regular":
        app.write_bytes((ROOT / APP).read_bytes())
    elif source == "symlink":
        app.symlink_to(checkout / "exports/private.html")
    runner = tmp_path / "runner"
    runner.mkdir()
    (runner / "old-private-file").write_text("Not part of the artifact")
    output = tmp_path / "output"
    step = next(s for s in WORKFLOW["jobs"]["deploy"]["steps"] if s.get("id") == "stage")
    result = run_step(step, checkout, RUNNER_TEMP=str(runner), GITHUB_OUTPUT=str(output))
    if source == "regular":
        assert result.returncode == 0, result.stderr
        artifact = Path(output.read_text().strip().removeprefix("path="))
        assert artifact.parent == runner
        assert [p.name for p in artifact.iterdir()] == [APP]
        assert (artifact / APP).read_bytes() == app.read_bytes()
    else:
        assert result.returncode != 0
        assert not output.exists()
