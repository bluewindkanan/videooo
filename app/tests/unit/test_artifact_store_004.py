"""Feature 004: test ArtifactStore extensions for audio/subtitle files."""
from __future__ import annotations

from pathlib import Path

from app.src.artifacts.store import ALLOWED_EXTENSIONS, ArtifactStore


class TestAllowedExtensionsExtended:
    def test_mp3_allowed(self) -> None:
        assert ".mp3" in ALLOWED_EXTENSIONS

    def test_wav_allowed(self) -> None:
        assert ".wav" in ALLOWED_EXTENSIONS

    def test_srt_allowed(self) -> None:
        assert ".srt" in ALLOWED_EXTENSIONS


class TestWriteFileMediaTypes:
    def test_write_mp3_file(self, tmp_path: Path) -> None:
        store = ArtifactStore(str(tmp_path / "artifacts"))
        content = b"\xff\xfb\x90\x00fake-mp3-data"
        ref = store.write_file(
            task_id="t1",
            step_key="voiceover",
            artifact_type="audio",
            filename="voiceover.mp3",
            content=content,
        )
        assert Path(ref.storage_ref).exists()
        assert Path(ref.storage_ref).read_bytes() == content
        assert ref.storage_ref.endswith(".mp3")

    def test_write_srt_file(self, tmp_path: Path) -> None:
        store = ArtifactStore(str(tmp_path / "artifacts"))
        content = b"1\n00:00:00,000 --> 00:00:05,000\nHello world\n"
        ref = store.write_file(
            task_id="t1",
            step_key="subtitle",
            artifact_type="subtitle",
            filename="output.srt",
            content=content,
        )
        assert Path(ref.storage_ref).exists()
        assert Path(ref.storage_ref).read_bytes() == content
        assert ref.storage_ref.endswith(".srt")

    def test_write_wav_file(self, tmp_path: Path) -> None:
        store = ArtifactStore(str(tmp_path / "artifacts"))
        content = b"RIFF\x00\x00\x00\x00WAVEfmt fake-wav"
        ref = store.write_file(
            task_id="t1",
            step_key="voiceover",
            artifact_type="audio",
            filename="segment.wav",
            content=content,
        )
        assert Path(ref.storage_ref).exists()
        assert ref.storage_ref.endswith(".wav")


class TestListTaskArtifactsMediaFiles:
    def test_lists_mp3_files(self, tmp_path: Path) -> None:
        store = ArtifactStore(str(tmp_path / "artifacts"))
        store.write_file(
            task_id="t1",
            step_key="voiceover",
            artifact_type="audio",
            filename="voice.mp3",
            content=b"\xff\xfbfake",
        )
        refs = store.list_task_artifacts("t1")
        assert len(refs) == 1
        assert refs[0].storage_ref.endswith(".mp3")

    def test_lists_srt_files(self, tmp_path: Path) -> None:
        store = ArtifactStore(str(tmp_path / "artifacts"))
        store.write_file(
            task_id="t1",
            step_key="subtitle",
            artifact_type="subtitle",
            filename="subs.srt",
            content=b"1\n00:00:00,000 --> 00:00:05,000\nTest\n",
        )
        refs = store.list_task_artifacts("t1")
        assert len(refs) == 1
        assert refs[0].storage_ref.endswith(".srt")

    def test_lists_mixed_media_types(self, tmp_path: Path) -> None:
        store = ArtifactStore(str(tmp_path / "artifacts"))
        store.write_json(task_id="t1", step_key="input", artifact_type="input", payload={"v": 1})
        store.write_file(
            task_id="t1",
            step_key="voiceover",
            artifact_type="audio",
            filename="voice.mp3",
            content=b"audio-data",
        )
        store.write_file(
            task_id="t1",
            step_key="material_fetch",
            artifact_type="source_video",
            filename="clip.mp4",
            content=b"video-data",
        )
        store.write_file(
            task_id="t1",
            step_key="subtitle",
            artifact_type="subtitle",
            filename="out.srt",
            content=b"subtitle-data",
        )
        refs = store.list_task_artifacts("t1")
        extensions = {Path(r.storage_ref).suffix for r in refs}
        assert ".json" in extensions
        assert ".mp3" in extensions
        assert ".mp4" in extensions
        assert ".srt" in extensions
        assert len(refs) == 4
