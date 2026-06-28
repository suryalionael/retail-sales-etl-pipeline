from __future__ import annotations

import zipfile
from pathlib import Path

import requests

from etl.logging_utils import get_logger

logger = get_logger(__name__)


def download_dataset(url: str, archive_path: str, extract_dir: str) -> Path:
    archive = Path(archive_path)
    archive.parent.mkdir(parents=True, exist_ok=True)
    target_dir = Path(extract_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    if not archive.exists():
        logger.info("Downloading dataset from %s", url)
        with requests.get(url, stream=True, timeout=120) as response:
            response.raise_for_status()
            with archive.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
    else:
        logger.info("Dataset archive already exists at %s", archive)

    if not any(target_dir.glob("*.xlsx")):
        logger.info("Extracting dataset to %s", target_dir)
        with zipfile.ZipFile(archive) as zip_file:
            zip_file.extractall(target_dir)
    return target_dir
