from __future__ import annotations

from pathlib import Path

from app.src.artifacts.store import ArtifactStore


def test_artifact_store_retains_history(tmp_path: Path) -> None:
    store = ArtifactStore(str(tmp_path / "artifacts"))
    task_id = "t1"

    a1 = store.write_json(
        task_id=task_id,
        step_key="script_generation",
        artifact_type="input",
        payload={"v": 1},
    )
    a2 = store.write_json(
        task_id=task_id,
        step_key="script_generation",
        artifact_type="input",
        payload={"v": 2},
    )

    assert a1.storage_ref != a2.storage_ref
    assert Path(a1.storage_ref).exists()
    assert Path(a2.storage_ref).exists()

    artifacts = store.list_task_artifacts(task_id)
    assert len(artifacts) == 2

