"""Unit tests for the image downloader (no network: the fetcher is faked).

Covers:
    - Images are written under ``<out>/<source>/<image_id><ext>``.
    - Existing files are skipped, so a stopped run resumes.
    - Dead links are retried once, then reported, without stopping the run.

Owner: Nisarg (cv) · Task: S1-NIS-5 · Requirements: NFR-07
"""

from pathlib import Path

from download_images import ATTEMPTS, download_all, image_path


def _row(image_id: str, url: str, source: str = "scin") -> dict[str, str]:
    return {"image_id": image_id, "source": source, "url": url}


def test_downloads_into_source_folder(tmp_path: Path) -> None:
    report = download_all(
        [_row("1", "https://x/1.png")],
        tmp_path,
        fetch=lambda url, timeout: b"img",
        workers=1,
    )

    assert (tmp_path / "scin" / "1.png").read_bytes() == b"img"
    assert report == {"counts": {"scin:downloaded": 1}, "failed": []}


def test_skips_existing_file(tmp_path: Path) -> None:
    existing = image_path(tmp_path, "scin", "1", "https://x/1.png")
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"old")

    def must_not_fetch(url: str, timeout: float) -> bytes:
        raise AssertionError("fetched an existing file")

    report = download_all(
        [_row("1", "https://x/1.png")], tmp_path, fetch=must_not_fetch
    )

    assert report["counts"] == {"scin:existing": 1}
    assert existing.read_bytes() == b"old"


def test_dead_link_is_reported_after_retry(tmp_path: Path) -> None:
    calls: list[str] = []

    def flaky(url: str, timeout: float) -> bytes:
        calls.append(url)
        if "dead" in url:
            raise OSError("HTTP 404")
        return b"img"

    rows = [
        _row("d", "https://x/dead.jpg", "fitzpatrick17k"),
        _row("ok", "https://x/ok.jpg", "fitzpatrick17k"),
    ]

    report = download_all(rows, tmp_path, fetch=flaky, workers=1)

    assert calls.count("https://x/dead.jpg") == ATTEMPTS
    assert report["counts"] == {
        "fitzpatrick17k:downloaded": 1,
        "fitzpatrick17k:failed": 1,
    }
    assert report["failed"] == [
        {"image_id": "d", "url": "https://x/dead.jpg", "error": "OSError: HTTP 404"}
    ]
    assert not (tmp_path / "fitzpatrick17k" / "d.jpg").exists()


def test_image_path_defaults_to_jpg_without_extension(tmp_path: Path) -> None:
    assert image_path(tmp_path, "scin", "1", "https://x/view?id=1").name == "1.jpg"
