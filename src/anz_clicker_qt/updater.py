from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


GITHUB_OWNER = "Anz-Clicker"
GITHUB_REPOSITORY = "Anz-Clicker"
LATEST_RELEASE_URL = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPOSITORY}/releases/latest"
)
API_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2026-03-10",
    "User-Agent": "Anz-Clicker-Updater",
}
ALLOWED_DOWNLOAD_HOSTS = {
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
}
VERSION_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$", re.IGNORECASE)


class UpdateError(RuntimeError):
    pass


class UpdateCancelled(UpdateError):
    pass


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    installer_name: str
    installer_url: str
    release_url: str
    digest: str = ""
    size: int = 0


def parse_version(value: str) -> tuple[int, int, int]:
    match = VERSION_PATTERN.fullmatch(value.strip())
    if not match:
        raise UpdateError(f'GitHub returned an invalid version number: "{value}".')
    return tuple(int(part) for part in match.groups())


def is_newer_version(candidate: str, current: str) -> bool:
    return parse_version(candidate) > parse_version(current)


def release_from_payload(payload: dict) -> ReleaseInfo:
    version = str(payload.get("tag_name", "")).strip().removeprefix("v")
    parse_version(version)
    assets = payload.get("assets")
    if not isinstance(assets, list):
        assets = []

    installers = [
        asset
        for asset in assets
        if isinstance(asset, dict)
        and str(asset.get("name", "")).lower().endswith(".exe")
        and str(asset.get("browser_download_url", "")).strip()
    ]
    installers = [
        asset
        for asset in installers
        if _normalized_asset_name(str(asset.get("name", ""))).find("anzclickersetup") >= 0
    ]
    if not installers:
        raise UpdateError(
            f"Version {version} is published, but it does not include an Anz Clicker installer."
        )

    asset = installers[0]
    installer_url = str(asset["browser_download_url"]).strip()
    _validate_download_url(installer_url)
    return ReleaseInfo(
        version=version,
        installer_name=Path(str(asset["name"])).name,
        installer_url=installer_url,
        release_url=str(payload.get("html_url", "")).strip(),
        digest=str(asset.get("digest", "") or "").strip(),
        size=max(0, int(asset.get("size", 0) or 0)),
    )


def fetch_latest_release(timeout: float = 15.0) -> ReleaseInfo:
    request = Request(LATEST_RELEASE_URL, headers=API_HEADERS)
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as exc:
        if exc.code == 404:
            raise UpdateError("No published Anz Clicker release was found on GitHub.") from exc
        raise UpdateError(f"GitHub returned HTTP {exc.code} while checking for updates.") from exc
    except (URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise UpdateError(f"Could not reach GitHub: {reason}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise UpdateError("GitHub returned an unreadable update response.") from exc
    if not isinstance(payload, dict):
        raise UpdateError("GitHub returned an unexpected update response.")
    return release_from_payload(payload)


def download_installer(
    release: ReleaseInfo,
    progress: Callable[[int, int], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    timeout: float = 30.0,
) -> Path:
    _validate_download_url(release.installer_url)
    update_dir = Path(tempfile.gettempdir()) / "Anz Clicker Updates" / f"v{release.version}"
    update_dir.mkdir(parents=True, exist_ok=True)
    destination = update_dir / Path(release.installer_name).name
    temporary = destination.with_suffix(destination.suffix + ".download")
    request = Request(release.installer_url, headers={"User-Agent": API_HEADERS["User-Agent"]})
    hasher = hashlib.sha256()
    downloaded = 0

    try:
        with urlopen(request, timeout=timeout) as response, temporary.open("wb") as output:
            _validate_download_url(response.geturl())
            total = max(release.size, int(response.headers.get("Content-Length", 0) or 0))
            while True:
                if should_cancel and should_cancel():
                    raise UpdateCancelled("The update download was cancelled.")
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                output.write(chunk)
                hasher.update(chunk)
                downloaded += len(chunk)
                if progress:
                    progress(downloaded, total)
        _verify_digest(release.digest, hasher.hexdigest())
        temporary.replace(destination)
        return destination
    except UpdateCancelled:
        temporary.unlink(missing_ok=True)
        raise
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        temporary.unlink(missing_ok=True)
        reason = getattr(exc, "reason", exc)
        raise UpdateError(f"Could not download the update: {reason}") from exc
    except UpdateError:
        temporary.unlink(missing_ok=True)
        raise


def installer_command(installer_path: Path) -> list[str]:
    return [
        str(installer_path),
        "/SILENT",
        "/CLOSEAPPLICATIONS",
        "/RESTARTAPPLICATIONS",
        "/NORESTART",
    ]


def launch_installer(installer_path: Path) -> None:
    if not installer_path.is_file():
        raise UpdateError("The downloaded installer could not be found.")
    try:
        subprocess.Popen(installer_command(installer_path), close_fds=True)
    except OSError as exc:
        raise UpdateError(f"Could not start the update installer: {exc}") from exc


def _validate_download_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https" or parsed.hostname not in ALLOWED_DOWNLOAD_HOSTS:
        raise UpdateError("GitHub returned an unsafe installer download address.")


def _normalized_asset_name(name: str) -> str:
    return "".join(character for character in name.lower() if character.isalnum())


def _verify_digest(expected: str, actual_sha256: str) -> None:
    if not expected:
        return
    algorithm, separator, digest = expected.partition(":")
    if separator and algorithm.lower() == "sha256":
        if not digest or digest.lower() != actual_sha256.lower():
            raise UpdateError("The downloaded installer failed its SHA-256 integrity check.")


__all__ = [
    "ReleaseInfo",
    "UpdateCancelled",
    "UpdateError",
    "download_installer",
    "fetch_latest_release",
    "installer_command",
    "is_newer_version",
    "launch_installer",
    "parse_version",
    "release_from_payload",
]
