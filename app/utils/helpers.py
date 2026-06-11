"""
Skolaz v2.0 — Helper Utilities
Pagination, slugification, reference generation, JSON responses
"""
import re
import uuid
import math
from datetime import datetime, timezone
from flask import jsonify, request


# ── JSON Response Helpers ─────────────────────────────────────────────────────

def success_response(data=None, message: str = "Success", code: int = 200):
    """Standard JSON success response."""
    return jsonify(success=True, data=data, message=message, errors=[]), code


def error_response(message: str = "An error occurred", errors=None, code: int = 400):
    """Standard JSON error response."""
    return jsonify(success=False, data=None, message=message,
                   errors=errors or []), code


# ── Pagination ────────────────────────────────────────────────────────────────

class Paginator:
    """Wraps a SQLAlchemy query and paginates it."""

    def __init__(self, query, page: int = 1, per_page: int = 20):
        self.total     = query.count()
        self.per_page  = per_page
        self.page      = max(1, page)
        self.pages     = math.ceil(self.total / per_page) if per_page else 1
        self.items     = query.offset((self.page - 1) * per_page).limit(per_page).all()
        self.has_prev  = self.page > 1
        self.has_next  = self.page < self.pages
        self.prev_num  = self.page - 1 if self.has_prev else None
        self.next_num  = self.page + 1 if self.has_next else None

    def iter_pages(self, left_edge=2, right_edge=2, left_current=2, right_current=3):
        last = 0
        for num in range(1, self.pages + 1):
            if (num <= left_edge
                    or (self.page - left_current - 1 < num < self.page + right_current)
                    or num > self.pages - right_edge):
                if last + 1 != num:
                    yield None  # gap
                yield num
                last = num


def get_page_args():
    """Extract page & per_page from request args safely."""
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        per_page = min(100, max(5, int(request.args.get("per_page", 20))))
    except (ValueError, TypeError):
        per_page = 20
    return page, per_page


# ── String Utilities ──────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text


def generate_reference(prefix: str = "SKZ") -> str:
    """Generate a unique application reference like SKZ-2024-00001."""
    year = datetime.now(timezone.utc).year
    unique = str(uuid.uuid4().int)[:5]
    return f"{prefix}-{year}-{unique}"


def truncate(text: str, length: int = 100) -> str:
    if not text:
        return ""
    return text[:length] + "…" if len(text) > length else text


# ── Date/Time Utilities ───────────────────────────────────────────────────────

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def format_date(dt, fmt: str = "%d %b %Y") -> str:
    if not dt:
        return ""
    if isinstance(dt, datetime):
        return dt.strftime(fmt)
    return str(dt)


# ── File Utilities ────────────────────────────────────────────────────────────

ALLOWED_DOC_EXTENSIONS = {
    "pdf", "doc", "docx", "jpg", "jpeg", "png", "gif", "webp"
}


def allowed_file(filename: str, allowed: set = None) -> bool:
    allowed = allowed or ALLOWED_DOC_EXTENSIONS
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def secure_filename_ext(filename: str) -> str:
    """Return the lowercase extension of a filename."""
    if "." in filename:
        return filename.rsplit(".", 1)[1].lower()
    return ""


def human_filesize(size_bytes: int) -> str:
    if not size_bytes:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# ── Avatar Generation ─────────────────────────────────────────────────────────

def avatar_url(name: str, size: int = 64, bg: str = "1E40AF", fg: str = "FFFFFF") -> str:
    """Generate a UI-Avatars.com URL for a name."""
    safe_name = name.replace(" ", "+") if name else "?"
    return (
        f"https://ui-avatars.com/api/?name={safe_name}"
        f"&size={size}&background={bg}&color={fg}&bold=true&format=png"
    )
