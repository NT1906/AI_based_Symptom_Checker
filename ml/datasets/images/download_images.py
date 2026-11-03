"""Download the images listed in the split manifest (run on Kaggle or Colab).

Responsibilities:
    - Fetch every manifest image into ``<out>/<source>/<image_id><ext>``,
      skipping files already there, so a stopped run can resume.
    - Log and count dead links instead of retrying them forever
      (docs/cv-plan.md §4); write ``download_report.json``.

Images go to a git-ignored folder (``ml/data/`` or ``/kaggle/working``) and
are never committed, shown or logged.

Usage::

    python ml/datasets/images/download_images.py --out /kaggle/working/images

Owner: Nisarg (cv) · Task: S1-NIS-5 · Requirements: NFR-07
"""

import argparse
import csv
import json
import logging
import urllib.request
from collections import Counter
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
DEFAULT_MANIFEST = HERE / "manifest" / "split_v1.csv"
DEFAULT_OUT = HERE.parents[1] / "data" / "images"
USER_AGENT = "symptom-checker-dataset/1 (student project; github.com/NT1906)"
ATTEMPTS = 2

log = logging.getLogger("images.download")

Fetch = Callable[[str, float], bytes]


def fetch_url(url: str, timeout: float) -> bytes:
    """Download one URL (redirects followed).

    Args:
        url: Image URL from the manifest.
        timeout: Seconds before giving up on the request.

    Returns:
        The response body.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body: bytes = response.read()
    return body


def image_path(out: Path, source: str, image_id: str, url: str) -> Path:
    """Local file for one manifest row; the extension comes from the URL.

    Example:
        >>> image_path(Path("img"), "scin", "42", "https://x/y/42.png").as_posix()
        'img/scin/42.png'
    """
    suffix = PurePosixPath(urlparse(url).path).suffix.lower() or ".jpg"
    return out / source / f"{image_id}{suffix}"


def download_one(
    row: dict[str, str], out: Path, fetch: Fetch, timeout: float
) -> tuple[str, str | None]:
    """Download one row unless its file exists.

    Returns:
        ``(status, error)``: status is ``downloaded``, ``existing`` or
        ``failed``; error is set only for ``failed``.
    """
    path = image_path(out, row["source"], row["image_id"], row["url"])
    if path.exists() and path.stat().st_size > 0:
        return "existing", None
    error = "unknown"
    for _ in range(ATTEMPTS):
        try:
            body = fetch(row["url"], timeout)
        except OSError as exc:  # URLError, HTTPError and timeouts are OSErrors
            error = f"{type(exc).__name__}: {exc}"
            continue
        if not body:
            error = "empty response"
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_suffix(path.suffix + ".part")
        partial.write_bytes(body)
        partial.replace(path)
        return "downloaded", None
    return "failed", error


def download_all(
    rows: Sequence[dict[str, str]],
    out: Path,
    fetch: Fetch = fetch_url,
    workers: int = 4,
    timeout: float = 20.0,
) -> dict[str, object]:
    """Download every row and return the report.

    Args:
        rows: Manifest rows.
        out: Image root folder.
        fetch: Downloader, replaceable in tests.
        workers: Parallel downloads.
        timeout: Per-request timeout in seconds.

    Returns:
        Counts per source and status, and the failed rows.
    """
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda r: download_one(r, out, fetch, timeout), rows))
    counts: Counter[str] = Counter()
    failed: list[dict[str, str]] = []
    for row, (status, error) in zip(rows, results, strict=True):
        counts[f"{row['source']}:{status}"] += 1
        if error is not None:
            failed.append(
                {"image_id": row["image_id"], "url": row["url"], "error": error}
            )
    return {"counts": dict(sorted(counts.items())), "failed": failed}


def main(argv: Sequence[str] | None = None) -> int:
    """Download the manifest images and write ``download_report.json``.

    Args:
        argv: Command-line arguments; defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code (0 even with dead links; they are in the report).
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    with args.manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    report = download_all(rows, args.out, workers=args.workers, timeout=args.timeout)
    args.out.mkdir(parents=True, exist_ok=True)
    report_path = args.out / "download_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    log.info("counts: %s", report["counts"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
