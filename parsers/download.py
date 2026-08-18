import tempfile
import time
from pathlib import Path

import httpx

from backend.config import settings

_last_download = 0.0


def download_pdf(url: str, *, retries: int = 3) -> Path:
    """Download PDF to a temp file with rate limiting and retries."""
    global _last_download
    elapsed = time.monotonic() - _last_download
    if elapsed < settings.psx_request_delay_seconds:
        time.sleep(settings.psx_request_delay_seconds - elapsed)

    headers = {"User-Agent": settings.psx_user_agent}
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with httpx.Client(timeout=60.0, headers=headers, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()
                suffix = ".pdf" if ".pdf" in url.lower() else ".bin"
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                tmp.write(response.content)
                tmp.close()
                _last_download = time.monotonic()
                return Path(tmp.name)
        except Exception as exc:
            last_error = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"Failed to download {url}: {last_error}")
