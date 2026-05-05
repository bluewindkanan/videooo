from __future__ import annotations

from fastapi.testclient import TestClient

from app.src.server.main import create_app


def test_create_and_query_task_and_artifacts() -> None:
    app = create_app(db_path=":memory:")
    client = TestClient(app)

    resp = client.post(
        "/api/video-tasks",
        json={
            "input_kind": "topic",
            "input_text": "hello",
            "source_links": ["https://example.com/a.mp4"],
        },
    )
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]

    detail = client.get(f"/api/video-tasks/{task_id}")
    assert detail.status_code == 200
    data = detail.json()
    assert data["task"]["id"] == task_id
    assert len(data["steps"]) >= 1

    artifacts = client.get(f"/api/video-tasks/{task_id}/artifacts")
    assert artifacts.status_code == 200
    artifacts_json = artifacts.json()
    assert len(artifacts_json["artifacts"]) >= 1
    assert any(a["artifact_type"] in ("input", "parsed_json") for a in artifacts_json["artifacts"])
