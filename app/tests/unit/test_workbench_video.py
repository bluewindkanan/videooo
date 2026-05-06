"""
T008 smoke tests — verify workbench HTML/JS contain video preview artefacts.
These are static file checks (no server required).
"""
import pathlib


WORKBENCH_HTML = pathlib.Path(__file__).resolve().parents[2] / "src" / "web" / "workbench.html"
WORKBENCH_JS = pathlib.Path(__file__).resolve().parents[2] / "src" / "web" / "workbench.js"


def _read_html() -> str:
    return WORKBENCH_HTML.read_text(encoding="utf-8")


def _read_js() -> str:
    return WORKBENCH_JS.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# HTML CSS checks
# ---------------------------------------------------------------------------

def test_workbench_html_has_video_css():
    """workbench.html must define .video-player CSS class."""
    html = _read_html()
    assert ".video-player" in html, "Missing .video-player CSS in workbench.html"


def test_workbench_html_has_download_css():
    """workbench.html must define .video-actions CSS class."""
    html = _read_html()
    assert ".video-actions" in html, "Missing .video-actions CSS in workbench.html"


def test_workbench_html_has_audio_css():
    """workbench.html must define .audio-player CSS class."""
    html = _read_html()
    assert ".audio-player" in html, "Missing .audio-player CSS in workbench.html"


def test_workbench_html_has_media_info_css():
    """workbench.html must define .media-info CSS class."""
    html = _read_html()
    assert ".media-info" in html, "Missing .media-info CSS in workbench.html"


# ---------------------------------------------------------------------------
# JS content checks
# ---------------------------------------------------------------------------

def test_workbench_js_has_final_video():
    """workbench.js must detect final_video artifact type."""
    js = _read_js()
    assert "final_video" in js, "Missing final_video artifact detection in workbench.js"


def test_workbench_js_has_audio_section():
    """workbench.js must detect audio artifact with voiceover step_key."""
    js = _read_js()
    assert 'artifact_type === "audio"' in js, "Missing audio artifact detection in workbench.js"
    assert 'step_key === "voiceover"' in js, "Missing voiceover step_key filter in workbench.js"


def test_workbench_js_has_subtitle_section():
    """workbench.js must detect subtitle artifact type."""
    js = _read_js()
    assert 'artifact_type === "subtitle"' in js, "Missing subtitle artifact detection in workbench.js"


def test_workbench_js_has_video_download():
    """workbench.js must render a download link for the video."""
    js = _read_js()
    assert "download" in js and "下载视频" in js, "Missing download link in workbench.js"


def test_workbench_js_has_subtitle_render_case():
    """workbench.js renderArtifactContent must handle subtitle step."""
    js = _read_js()
    assert 'stepKey === "subtitle"' in js, "Missing subtitle case in renderArtifactContent"
