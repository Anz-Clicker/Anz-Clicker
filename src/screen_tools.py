from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

from PIL import Image, ImageChops, ImageGrab

try:
    import pytesseract
except ImportError:
    pytesseract = None

from actions import ScreenArea


TESSERACT_CMD: Path | None = None
TESSDATA_DIR: Path | None = None


def configure_ocr(root: str | Path) -> None:
    global TESSERACT_CMD
    global TESSDATA_DIR
    root_path = Path(root)
    roots = [root_path, root_path / "vendor"]
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        roots.insert(0, Path(bundle_dir))
    for root_path in roots:
        tesseract_exe = root_path / "tesseract" / "tesseract.exe"
        tessdata_dir = root_path / "tesseract" / "tessdata"
        if tesseract_exe.exists():
            TESSERACT_CMD = tesseract_exe
            if pytesseract is not None:
                pytesseract.pytesseract.tesseract_cmd = str(tesseract_exe)
        if tessdata_dir.exists():
            TESSDATA_DIR = tessdata_dir
            os.environ["TESSDATA_PREFIX"] = str(tessdata_dir)
        if tesseract_exe.exists() or tessdata_dir.exists():
            return


def ocr_available() -> bool:
    return pytesseract is not None or bool(TESSERACT_CMD and TESSERACT_CMD.exists())


def capture_area(area: ScreenArea) -> Image.Image:
    if not area.is_valid():
        raise ValueError("A valid screen area is required.")
    return ImageGrab.grab(bbox=area.normalized().as_tuple(), all_screens=True)


def read_text_in_area(area: ScreenArea) -> str:
    image = capture_area(area)
    if pytesseract is not None:
        return pytesseract.image_to_string(image, config="--psm 6").strip()
    if not TESSERACT_CMD or not TESSERACT_CMD.exists():
        raise RuntimeError("OCR is not available. Bundle Tesseract to use Wait for Screen Text.")
    return _read_text_with_tesseract(image)


def _read_text_with_tesseract(image: Image.Image) -> str:
    temp_dir = Path.cwd() / "captures" / "ocr_temp" / uuid.uuid4().hex
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        image_path = temp_dir / "screen_text.png"
        output_base = Path(temp_dir) / "screen_text"
        image.save(image_path)
        env = os.environ.copy()
        if TESSDATA_DIR and TESSDATA_DIR.exists():
            env["TESSDATA_PREFIX"] = str(TESSDATA_DIR)
        subprocess.run(
            [str(TESSERACT_CMD), str(image_path), str(output_base), "--psm", "6"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            env=env,
        )
        output_path = output_base.with_suffix(".txt")
        return output_path.read_text(encoding="utf-8", errors="ignore").strip() if output_path.exists() else ""
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def changed_percent(first: Image.Image, second: Image.Image) -> float:
    left = first.convert("RGB")
    right = second.convert("RGB")
    if left.size != right.size:
        right = right.resize(left.size)
    diff = ImageChops.difference(left, right).convert("L")
    mask = diff.point(lambda value: 255 if value else 0)
    histogram = mask.histogram()
    changed_pixels = histogram[255] if len(histogram) > 255 else 0
    total_pixels = max(1, left.width * left.height)
    return changed_pixels / total_pixels * 100.0


def capture_screen_pixel(x: int, y: int) -> tuple[int, int, int]:
    image = ImageGrab.grab(bbox=(x, y, x + 1, y + 1), all_screens=True).convert("RGB")
    return image.getpixel((0, 0))


def pixel_matches(actual: tuple[int, int, int], expected: tuple[int, int, int], tolerance_percent: float) -> bool:
    percent = color_difference_percent(actual, expected)
    return percent <= max(0.0, tolerance_percent)


def load_picture(path: str | Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def save_image(image: Image.Image, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def find_picture(
    area: ScreenArea,
    picture_path: str,
    tolerance_percent: float,
    should_stop: Callable[[], bool] | None = None,
) -> tuple[int, int, int, int] | None:
    haystack = capture_area(area).convert("RGB")
    needle = load_picture(picture_path)
    if needle.width > haystack.width or needle.height > haystack.height:
        return None

    area_normalized = area.normalized()
    haystack_pixels = haystack.load()
    needle_pixels = needle.load()
    best_score = 100.0
    best_match: tuple[int, int, int, int] | None = None
    x_limit = haystack.width - needle.width + 1
    y_limit = haystack.height - needle.height + 1
    total_pixels = needle.width * needle.height
    sample_step = 1 if total_pixels <= 2500 else (2 if total_pixels <= 12000 else 3)
    anchor_points = _anchor_points(needle.width, needle.height)
    anchor_tolerance = max(2.0, tolerance_percent * 1.75)

    for offset_y in range(y_limit):
        if should_stop and should_stop():
            return None
        for offset_x in range(x_limit):
            if should_stop and should_stop():
                return None
            if not _anchor_points_match(
                haystack_pixels,
                needle_pixels,
                offset_x,
                offset_y,
                anchor_points,
                anchor_tolerance,
            ):
                continue
            score = image_difference_percent_at(
                haystack_pixels,
                needle_pixels,
                offset_x,
                offset_y,
                needle.width,
                needle.height,
                sample_step,
                tolerance_percent,
                should_stop,
            )
            if score is None:
                return None
            if score < best_score:
                best_score = score
                best_match = (
                    area_normalized.left + offset_x,
                    area_normalized.top + offset_y,
                    needle.width,
                    needle.height,
                )
                if best_score <= tolerance_percent:
                    return best_match
    return best_match if best_match and best_score <= tolerance_percent else None


def color_difference_percent(left: tuple[int, int, int], right: tuple[int, int, int]) -> float:
    total_delta = sum(abs(left[index] - right[index]) for index in range(3))
    return total_delta / (255 * 3) * 100.0


def image_difference_percent(left: Image.Image, right: Image.Image, sample_step: int = 1) -> float:
    first = left.convert("RGB")
    second = right.convert("RGB")
    if first.size != second.size:
        second = second.resize(first.size)

    total = 0.0
    samples = 0
    for y in range(0, first.height, sample_step):
        for x in range(0, first.width, sample_step):
            total += color_difference_percent(first.getpixel((x, y)), second.getpixel((x, y)))
            samples += 1
    return total / max(1, samples)


def _anchor_points(width: int, height: int) -> list[tuple[int, int]]:
    points = {
        (0, 0),
        (max(0, width - 1), 0),
        (0, max(0, height - 1)),
        (max(0, width - 1), max(0, height - 1)),
        (width // 2, height // 2),
        (width // 3, height // 3),
        ((width * 2) // 3, height // 3),
        (width // 3, (height * 2) // 3),
        ((width * 2) // 3, (height * 2) // 3),
    }
    return list(points)


def _anchor_points_match(
    haystack_pixels,
    needle_pixels,
    offset_x: int,
    offset_y: int,
    anchor_points: list[tuple[int, int]],
    tolerance_percent: float,
) -> bool:
    for point_x, point_y in anchor_points:
        haystack_pixel = haystack_pixels[offset_x + point_x, offset_y + point_y]
        needle_pixel = needle_pixels[point_x, point_y]
        if color_difference_percent(haystack_pixel, needle_pixel) > tolerance_percent:
            return False
    return True


def image_difference_percent_at(
    haystack_pixels,
    needle_pixels,
    offset_x: int,
    offset_y: int,
    width: int,
    height: int,
    sample_step: int,
    cutoff_percent: float,
    should_stop: Callable[[], bool] | None = None,
) -> float | None:
    total = 0.0
    samples = 0
    for y in range(0, height, sample_step):
        if should_stop and should_stop():
            return None
        for x in range(0, width, sample_step):
            total += color_difference_percent(
                haystack_pixels[offset_x + x, offset_y + y],
                needle_pixels[x, y],
            )
            samples += 1
            if samples >= 8 and total / samples > cutoff_percent:
                return total / samples
    return total / max(1, samples)
