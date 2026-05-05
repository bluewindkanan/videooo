"""Material fetch skill — download source links and categorize failures."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from app.src.artifacts.store import ArtifactStore

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi"}
ALLOWED_CONTENT_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo"}
MAX_FILE_SIZE = int(os.environ.get("VIDEOOO_MAX_MATERIAL_SIZE", str(500 * 1024 * 1024)))
DOWNLOAD_TIMEOUT = int(os.environ.get("VIDEOOO_DOWNLOAD_TIMEOUT", "60"))

# Threshold for detecting auth-wall / redirect pages
_PLATFORM_RESTRICTION_BODY_THRESHOLD = 1024  # bytes


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class MaterialFetchResult:
    url: str
    status: str  # "success" | "failed"
    failure_category: str | None = None  # unreachable, timeout, unsupported_format, size_exceeded, platform_restriction
    failure_message: str | None = None
    storage_ref: str | None = None
    file_size: int | None = None
    content_type: str | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extension_from_url(url: str) -> str:
    """Extract the file extension from the URL path component."""
    path = PurePosixPath(url.split("?", 1)[0].split("#", 1)[0])
    return path.suffix.lower()


def _categorize_error(exc: Exception) -> tuple[str, str]:
    """Map an httpx exception to a (failure_category, failure_message) tuple."""
    if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout)):
        return "unreachable", str(exc)
    if isinstance(exc, httpx.ReadTimeout):
        return "timeout", str(exc)
    # Fallback for unexpected errors
    return "unreachable", str(exc)


def _fetch_single(
    *,
    url: str,
    client: httpx.Client,
    artifact_store: "ArtifactStore",
    task_id: str,
) -> MaterialFetchResult:
    """Download a single URL and return a MaterialFetchResult."""
    try:
        response = client.get(url)
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        cat, msg = _categorize_error(exc)
        return MaterialFetchResult(url=url, status="failed", failure_category=cat, failure_message=msg)
    except httpx.ReadTimeout as exc:
        cat, msg = _categorize_error(exc)
        return MaterialFetchResult(url=url, status="failed", failure_category=cat, failure_message=msg)
    except httpx.HTTPError as exc:
        cat, msg = _categorize_error(exc)
        return MaterialFetchResult(url=url, status="failed", failure_category=cat, failure_message=msg)

    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    content_length_header = response.headers.get("content-length")

    # --- Validate extension from URL ---
    ext = _extension_from_url(url)
    if ext not in ALLOWED_EXTENSIONS:
        return MaterialFetchResult(
            url=url,
            status="failed",
            failure_category="unsupported_format",
            failure_message=f"URL extension '{ext}' is not in allowed set {ALLOWED_EXTENSIONS}",
        )

    # --- Validate Content-Type ---
    if content_type not in ALLOWED_CONTENT_TYPES:
        # Before rejecting, check if this looks like a platform restriction
        body = response.content
        if len(body) < _PLATFORM_RESTRICTION_BODY_THRESHOLD:
            return MaterialFetchResult(
                url=url,
                status="failed",
                failure_category="platform_restriction",
                failure_message=f"Response body is only {len(body)} bytes with Content-Type '{content_type}' — suspected auth wall or redirect",
            )
        return MaterialFetchResult(
            url=url,
            status="failed",
            failure_category="unsupported_format",
            failure_message=f"Content-Type '{content_type}' is not in allowed set {ALLOWED_CONTENT_TYPES}",
        )

    # --- Validate size (header) ---
    if content_length_header is not None:
        try:
            declared_size = int(content_length_header)
            if declared_size > MAX_FILE_SIZE:
                return MaterialFetchResult(
                    url=url,
                    status="failed",
                    failure_category="size_exceeded",
                    failure_message=f"Declared Content-Length {declared_size} exceeds max {MAX_FILE_SIZE}",
                )
        except ValueError:
            pass  # malformed header — will check actual body size instead

    # --- Read body and validate actual size ---
    body = response.content
    if len(body) > MAX_FILE_SIZE:
        return MaterialFetchResult(
            url=url,
            status="failed",
            failure_category="size_exceeded",
            failure_message=f"Actual body size {len(body)} exceeds max {MAX_FILE_SIZE}",
        )

    # --- Platform restriction: 200 but body suspiciously small and not truly video ---
    if len(body) < _PLATFORM_RESTRICTION_BODY_THRESHOLD and not content_type.startswith("video/"):
        return MaterialFetchResult(
            url=url,
            status="failed",
            failure_category="platform_restriction",
            failure_message=f"Response body is only {len(body)} bytes — suspected auth wall or redirect",
        )

    # --- Success: write to artifact store ---
    filename = PurePosixPath(url.split("?", 1)[0].split("#", 1)[0]).name or "video"
    ref = artifact_store.write_file(
        task_id=task_id,
        step_key="material_fetch",
        artifact_type="source_video",
        filename=filename,
        content=body,
    )

    return MaterialFetchResult(
        url=url,
        status="success",
        storage_ref=ref.storage_ref,
        file_size=len(body),
        content_type=content_type,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_material_fetch(
    *,
    source_links: list[str],
    artifact_store: "ArtifactStore",
    task_id: str,
) -> list[MaterialFetchResult]:
    """Download each source link and return per-link results.

    Parameters
    ----------
    source_links:
        List of URLs to download.
    artifact_store:
        ArtifactStore instance with a write_file method for persisting downloads.
    task_id:
        The task ID used for artifact storage paths.

    Returns
    -------
    A list of MaterialFetchResult, one per source link, in the same order.
    """
    if not source_links:
        return []

    results: list[MaterialFetchResult] = []

    with httpx.Client(timeout=DOWNLOAD_TIMEOUT) as client:
        for url in source_links:
            result = _fetch_single(
                url=url,
                client=client,
                artifact_store=artifact_store,
                task_id=task_id,
            )
            results.append(result)

    return results
