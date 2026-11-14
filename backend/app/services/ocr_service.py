import io
import os
import shutil
import logging
import re
from typing import Optional, Dict, Any, List
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

try:
    import pytesseract
except ImportError:
    pytesseract = None

from app.utils.config import get_settings

logger = logging.getLogger("adshield.ocr")

COMMON_TESSERACT_PATHS = [
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\ELCOT\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    r"C:\tools\tesseract\tesseract.exe"
]

def get_tesseract_path() -> Optional[str]:
    """
    Locates the Tesseract executable path.
    Checks user setting TESSERACT_CMD first, then standard Linux/Windows install paths, then system PATH.
    """
    settings = get_settings()
    if settings.TESSERACT_CMD:
        cmd = settings.TESSERACT_CMD.strip()
        if shutil.which(cmd) or (os.path.isfile(cmd) and os.access(cmd, os.X_OK)):
            return cmd

    # Check common system paths
    for p in COMMON_TESSERACT_PATHS:
        if shutil.which(p) or (os.path.isfile(p) and os.access(p, os.X_OK)):
            return p

    # Check system PATH
    return shutil.which("tesseract")

def get_tesseract_details() -> Dict[str, Any]:
    """
    Inspects Tesseract availability and version.
    Returns status dictionary for health checks and diagnostics.
    """
    if pytesseract is None:
        return {
            "available": False,
            "version": None,
            "path": None,
            "error": "pytesseract Python wrapper is not installed."
        }

    path = get_tesseract_path()
    if not path:
        return {
            "available": False,
            "version": None,
            "path": None,
            "error": (
                "Tesseract executable not found. Please install Tesseract-OCR on your system "
                "(e.g., via winget install UB-Mannheim.TesseractOCR) or set TESSERACT_CMD in backend/.env."
            )
        }

    try:
        pytesseract.pytesseract.tesseract_cmd = path
        version_str = str(pytesseract.get_tesseract_version()).strip()
        return {
            "available": True,
            "version": version_str,
            "path": path,
            "error": None
        }
    except Exception as e:
        logger.warning(f"Error executing Tesseract binary at '{path}': {e}")
        return {
            "available": False,
            "version": None,
            "path": path,
            "error": f"Failed to execute Tesseract binary: {str(e)}"
        }

def is_tesseract_available() -> bool:
    """Quick boolean check for health endpoints."""
    return get_tesseract_details()["available"]

def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """
    Prepares an image for high-accuracy OCR extraction:
    1. Normalizes EXIF orientation.
    2. Upscales low-resolution images so small typography is legible.
    3. Converts to grayscale.
    4. Enhances contrast and applies thresholding.
    """
    # 1. Correct orientation from camera/mobile EXIF tags
    try:
        image = ImageOps.exif_transpose(image)
    except Exception:
        pass

    # 2. Convert palette or RGBA images with transparency to RGB on a white background
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        bg = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        bg.paste(image, mask=image.split()[-1])
        image = bg
    elif image.mode != "RGB" and image.mode != "L":
        image = image.convert("RGB")

    # 3. Upscale if image is too small for small font detection
    min_dim = min(image.width, image.height)
    if min_dim < 600:
        scale_factor = 2.0 if min_dim >= 300 else 3.0
        new_size = (int(image.width * scale_factor), int(image.height * scale_factor))
        image = image.resize(new_size, resample=Image.Resampling.LANCZOS)

    # 4. Grayscale conversion
    gray = image.convert("L")

    # 5. Contrast and sharpness enhancement
    enhanced = ImageEnhance.Contrast(gray).enhance(2.0)
    enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.5)

    # 6. Noise filtering
    filtered = enhanced.filter(ImageFilter.MedianFilter(size=3))

    return filtered

def extract_text_from_image(image_bytes: bytes) -> Dict[str, Any]:
    """
    Decodes an image, applies computer vision preprocessing, and runs Tesseract OCR.
    Handles uncorrupted images, missing binaries, and no-text images gracefully.
    """
    # Verify image integrity
    try:
        test_img = Image.open(io.BytesIO(image_bytes))
        test_img.verify()
        # Re-open after verify() closes the stream
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        logger.error(f"Image validation/decoding failed: {e}")
        return {
            "status": "CORRUPTED",
            "success": False,
            "text": "",
            "word_count": 0,
            "confidence": 0.0,
            "error": f"The uploaded file is corrupted or not a valid image: {str(e)}"
        }

    # Check Tesseract binary availability
    details = get_tesseract_details()
    if not details["available"]:
        return {
            "status": "UNAVAILABLE",
            "success": False,
            "text": "",
            "word_count": 0,
            "confidence": 0.0,
            "error": details["error"]
        }

    try:
        pytesseract.pytesseract.tesseract_cmd = details["path"]
        processed_img = preprocess_image_for_ocr(image)

        # 1. Run image_to_string for clean text
        raw_text = pytesseract.image_to_string(processed_img, config="--psm 11")
        cleaned_text = re.sub(r"\n{3,}", "\n\n", raw_text.strip())

        # If sparse PSM returned nothing, retry with standard PSM 3
        if not cleaned_text:
            raw_text = pytesseract.image_to_string(processed_img, config="--psm 3")
            cleaned_text = re.sub(r"\n{3,}", "\n\n", raw_text.strip())

        words = [w for w in cleaned_text.split() if any(c.isalnum() for c in w)]

        # 2. Extract confidence scores using image_to_data
        data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT)
        confidences = []
        for conf, w in zip(data.get("conf", []), data.get("text", [])):
            if str(conf).replace(".", "").isdigit() and float(conf) > 0 and w.strip():
                confidences.append(float(conf))

        avg_confidence = round(sum(confidences) / len(confidences), 1) if confidences else (80.0 if words else 0.0)

        # 3. Check if text was detected
        if len(words) == 0:
            return {
                "status": "NO_TEXT_DETECTED",
                "success": True,
                "text": "",
                "word_count": 0,
                "confidence": 0.0,
                "error": None
            }

        return {
            "status": "SUCCESS",
            "success": True,
            "text": cleaned_text,
            "word_count": len(words),
            "confidence": avg_confidence,
            "error": None
        }

    except Exception as e:
        logger.error(f"OCR text extraction failed: {e}", exc_info=True)
        return {
            "status": "FAILED",
            "success": False,
            "text": "",
            "word_count": 0,
            "confidence": 0.0,
            "error": f"OCR processing failed: {str(e)}"
        }
