"""Feature 003: test ArtifactStore.write_file and extended list_task_artifacts."""
from __future__ import annotations

from pathlib import Path

from app.src.artifacts.store import ALLOWED_EXTENSIONS, ArtifactStore


class TestAllowedExtensions:
    def test_contains_common_video_formats(self) -> None:
        assert ".mp4" in ALLOWED_EXTENSIONS
        assert ".mov" in ALLOWED_EXTENSIONS
        assert ".avi" in ALLOWED_EXTENSIONS

    def test_is_a_set(self) -> None:
        assert isinstance(ALLOWED_EXTENSIONS, set)


class TestWriteFile:
    def test_writes_binary_file(self, tmp_path: Path) -> None:
        store = ArtifactStore(str(tmp_path / "artifacts"))
        content = b"\x00\x01\x02\x03fake-video-data"
        ref = store.write_file(
            task_id="t1",
            step_key="material_fetch",
            artifact_type="source_video",
            filename="original.mp4",
            content=content,
        )
        assert Path(ref.storage_ref).exists()
        assert Path(ref.storage_ref).read_bytes() == content

    def test_sanitizes_filename_to_uuid(self, tmp_path: Path) -> None:
        store = ArtifactStore(str(tmp_path / "artifacts"))
        ref = store.write_file(
            task_id="t1",
            step_key="material_fetch",
            artifact_type="uploaded_video",
            filename="my dangerous file name with spaces.mov",
            content=b"data",
        )
        # File should end with .mov extension
        assert ref.storage_ref.endswith(".mov")
        # File name should NOT contain spaces or the original name
        actual_name = Path(ref.storage_ref).name
        assert " " not in actual_name
        assert "dangerous" not in actual_name

    def test_preserves_extension_only(self, tmp_path: Path) -> None:
        store = ArtifactStore(str(tmp_path / "artifacts"))
        ref = store.write_file(
            task_id="t1",
            step_key="step1",
            artifact_type="source_video",
            filename="video.avi",
            content=b"x",
        )
        assert ref.storage_ref.endswith(".avi")

    def test_returns_artifact_ref_fields(self, tmp_path: Path) -> None:
        store = ArtifactStore(str(tmp_path / "artifacts"))
        ref = store.write_file(
            task_id="t1",
            step_key="material_fetch",
            artifact_type="source_video",
            filename="clip.mp4",
            content=b"content",
        )
        assert ref.artifact_type == "source_video"
        assert ref.step_key == "material_fetch"
        assert ref.storage_ref  # non-empty

    def test_rejects_disallowed_extension(self, tmp_path: Path) -> None:
        store = ArtifactStore(str(tmp_path / "artifacts"))
        import pytest

        with pytest.raises(ValueError):
            store.write_file(
                task_id="t1",
                step_key="step1",
                artifact_type="source_video",
                filename="malicious.exe",
                content=b"bad",
            )


class TestListTaskArtifactsExtended:
    def test_lists_json_and_video_files(self, tmp_path: Path) -> None:
        store = ArtifactStore(str(tmp_path / "artifacts"))
        # Write a JSON artifact
        store.write_json(
            task_id="t1",
            step_key="step1",
            artifact_type="input",
            payload={"key": "val"},
        )
        # Write a video file
        store.write_file(
            task_id="t1",
            step_key="material_fetch",
            artifact_type="source_video",
            filename="video.mp4",
            content=b"\x00\x01\x02",
        )

        refs = store.list_task_artifacts("t1")
        assert len(refs) == 2
        extensions = {Path(r.storage_ref).suffix for r in refs}
        assert ".json" in extensions
        assert ".mp4" in extensions

    def test_lists_bin_files(self, tmp_path: Path) -> None:
        store = ArtifactStore(str(tmp_path / "artifacts"))
        # .bin is not an uploadable extension but should still be discoverable
        # by list_task_artifacts (e.g. written by a fetch skill directly).
        task_dir = store.task_dir("t1")
        (task_dir / "somefile.bin").write_bytes(b"\x00")
        refs = store.list_task_artifacts("t1")
        assert len(refs) >= 1
        assert any(r.storage_ref.endswith(".bin") for r in refs)

    def test_empty_task_returns_empty(self, tmp_path: Path) -> None:
        store = ArtifactStore(str(tmp_path / "artifacts"))
        refs = store.list_task_artifacts("nonexistent")
        assert refs == []
