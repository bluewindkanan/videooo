"""Feature 004: test new ArtifactType enum members for media pipeline."""
from __future__ import annotations

from app.src.domain.models import ArtifactType


class TestArtifactTypeMediaMembers:
    def test_audio_member_exists(self) -> None:
        assert hasattr(ArtifactType, "audio")

    def test_clip_member_exists(self) -> None:
        assert hasattr(ArtifactType, "clip")

    def test_subtitle_member_exists(self) -> None:
        assert hasattr(ArtifactType, "subtitle")

    def test_final_video_member_exists(self) -> None:
        assert hasattr(ArtifactType, "final_video")

    def test_audio_value(self) -> None:
        assert ArtifactType.audio.value == "audio"

    def test_clip_value(self) -> None:
        assert ArtifactType.clip.value == "clip"

    def test_subtitle_value(self) -> None:
        assert ArtifactType.subtitle.value == "subtitle"

    def test_final_video_value(self) -> None:
        assert ArtifactType.final_video.value == "final_video"

    def test_existing_types_still_work(self) -> None:
        """Ensure we didn't break existing enum members."""
        assert ArtifactType.input.value == "input"
        assert ArtifactType.llm_raw.value == "llm_raw"
        assert ArtifactType.parsed_json.value == "parsed_json"
        assert ArtifactType.review.value == "review"
        assert ArtifactType.error.value == "error"
        assert ArtifactType.source_video.value == "source_video"
        assert ArtifactType.uploaded_video.value == "uploaded_video"
        assert ArtifactType.material_status.value == "material_status"
