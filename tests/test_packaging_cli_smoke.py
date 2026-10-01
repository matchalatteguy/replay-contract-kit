"""Exercise a wheel without relying on the checkout's import path."""

import subprocess
import sys
from pathlib import Path


def run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True
    )


def test_wheel_installs_and_runs_outside_checkout(tmp_path):
    root = Path(__file__).parents[1]
    dist = tmp_path / "dist"
    run(["uv", "build", "--wheel", "--out-dir", str(dist)], cwd=root)
    wheel = next(dist.glob("replay_contract_kit-*.whl"))
    environment = tmp_path / "venv"
    run(["uv", "venv", "--python", sys.executable, str(environment)], cwd=tmp_path)
    python = environment / "bin/python"
    cli = environment / "bin/replay-contract"
    run(["uv", "pip", "install", "--python", str(python), str(wheel)], cwd=tmp_path)
    assert "validate-dataset" in run([str(cli), "--help"], cwd=tmp_path).stdout
    run([str(python), "-c", "import replay_contract_kit"], cwd=tmp_path)
    for fixture in ("synthetic_event_dataset", "synthetic_csv_dataset"):
        manifest = root / "examples" / fixture / "manifest.json"
        result = run([str(cli), "validate-dataset", str(manifest)], cwd=tmp_path)
        assert '"passed": true' in result.stdout
