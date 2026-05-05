from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi"}
_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".bin"}


@dataclass(frozen=True)
class ArtifactRef:
    storage_ref: str
    artifact_type: str
    step_key: str


class ArtifactStore:
    """Filesystem artifact store.

    First slice keeps this intentionally simple:
    - Each task gets its own directory.
    - Each write produces a new file (retention by default).
    """

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def task_dir(self, task_id: str) -> Path:
        d = self.base_dir / task_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _unique_name(self, prefix: str, suffix: str) -> str:
        # Use time + uuid to avoid collisions within the same millisecond.
        return f"{prefix}-{int(time.time() * 1000)}-{uuid.uuid4().hex}{suffix}"

    def write_json(
        self,
        *,
        task_id: str,
        step_key: str,
        artifact_type: str,
        payload: Any,
    ) -> ArtifactRef:
        name = self._unique_name(f"{step_key}-{artifact_type}", ".json")
        path = self.task_dir(task_id) / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return ArtifactRef(
            storage_ref=str(path),
            artifact_type=artifact_type,
            step_key=step_key,
        )

    def write_file(
        self,
        *,
        task_id: str,
        step_key: str,
        artifact_type: str,
        filename: str,
        content: bytes,
    ) -> ArtifactRef:
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"disallowed file extension: {ext}")
        safe_name = f"{uuid.uuid4().hex}{ext}"
        path = self.task_dir(task_id) / safe_name
        path.write_bytes(content)
        return ArtifactRef(
            storage_ref=str(path),
            artifact_type=artifact_type,
            step_key=step_key,
        )

    def list_task_artifacts(self, task_id: str) -> list[ArtifactRef]:
        d = self.task_dir(task_id)
        refs: list[ArtifactRef] = []
        patterns = ["*.json"] + [f"*{ext}" for ext in _VIDEO_EXTENSIONS]
        seen: set[Path] = set()
        for pattern in patterns:
            for p in sorted(d.glob(pattern)):
                if p in seen:
                    continue
                seen.add(p)
                # best-effort parse step_key/artifact_type from filename
                stem = p.name.rsplit(".", 1)[0]
                parts = stem.split("-")
                step_key = parts[0] if parts else "unknown"
                artifact_type = parts[1] if len(parts) > 1 else "unknown"
                refs.append(ArtifactRef(storage_ref=str(p), artifact_type=artifact_type, step_key=step_key))
        return refs
