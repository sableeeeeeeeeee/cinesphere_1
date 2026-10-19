"""Theatre layout: validation, seat generation, and safe modification.

Layout JSON shape stored on Screen.layout:
{
  "row_labels": ["A", "B", ...],          # one per grid row (custom labels allowed: A, AA, ...)
  "cols": 12,                              # number of grid columns
  "cells": [                               # rows x cols; null = empty space / aisle
     [ {"n": "1", "c": "standard", "d": false}, null, ... ],
  ]
}
"""
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import utcnow
from app.models import BookingSeat, Screen, Seat, SeatLock, Show
from app.models.catalog import SEAT_CATEGORIES

MAX_ROWS, MAX_COLS = 40, 60


class LayoutError(ValueError):
    def __init__(self, message: str, details: list | None = None):
        super().__init__(message)
        self.details = details or []


def validate_layout(layout: dict) -> None:
    errors: list[str] = []
    labels = layout.get("row_labels")
    cols = layout.get("cols")
    cells = layout.get("cells")
    if not isinstance(labels, list) or not isinstance(cells, list) or not isinstance(cols, int):
        raise LayoutError("Layout must contain row_labels, cols and cells")
    if not (1 <= len(labels) <= MAX_ROWS):
        errors.append(f"Rows must be between 1 and {MAX_ROWS}")
    if not (1 <= cols <= MAX_COLS):
        errors.append(f"Columns must be between 1 and {MAX_COLS}")
    if len(cells) != len(labels):
        errors.append("cells must have one entry per row label")
    if any(not str(l).strip() or len(str(l)) > 4 for l in labels):
        errors.append("Row labels must be 1-4 characters")
    if len(set(labels)) != len(labels):
        errors.append("Row labels must be unique")
    if errors:
        raise LayoutError("Invalid layout", errors)

    seat_count = 0
    for r, row in enumerate(cells):
        if not isinstance(row, list) or len(row) != cols:
            errors.append(f"Row {labels[r]} must have exactly {cols} cells")
            continue
        numbers = []
        for c, cell in enumerate(row):
            if cell is None:
                continue
            seat_count += 1
            n = str(cell.get("n", "")).strip()
            if not n or len(n) > 6:
                errors.append(f"Seat at {labels[r]} column {c + 1} needs a number (max 6 chars)")
            if cell.get("c") not in SEAT_CATEGORIES:
                errors.append(f"Seat {labels[r]}{n} has unknown category '{cell.get('c')}'")
            numbers.append(n)
        dupes = [k for k, v in Counter(numbers).items() if v > 1]
        if dupes:
            errors.append(f"Row {labels[r]} has duplicate seat numbers: {', '.join(dupes)}")
    if seat_count == 0:
        errors.append("A screen needs at least one seat")
    if errors:
        raise LayoutError("Invalid layout", errors)


def layout_summary(layout: dict) -> dict:
    counts: Counter = Counter()
    total = 0
    for row in layout["cells"]:
        for cell in row:
            if cell:
                total += 1
                counts[cell["c"]] += 1
    return {"total_seats": total, "by_category": dict(counts)}


def default_layout(rows: int = 8, cols: int = 12) -> dict:
    labels = [chr(ord("A") + i) for i in range(rows)]
    cells = []
    for r in range(rows):
        cat = "premium" if r >= rows - 2 else "standard"
        cells.append([{"n": str(c + 1), "c": cat, "d": False} for c in range(cols)])
    return {"row_labels": labels, "cols": cols, "cells": cells}


def _desired_seats(layout: dict) -> dict[tuple[str, str], dict]:
    out = {}
    for r, row in enumerate(layout["cells"]):
        for c, cell in enumerate(row):
            if cell:
                key = (str(layout["row_labels"][r]), str(cell["n"]).strip())
                out[key] = {"grid_row": r, "grid_col": c, "category": cell["c"], "disabled": bool(cell.get("d"))}
    return out


def apply_layout(db: Session, screen: Screen, layout: dict) -> dict:
    """Validate, then create/update Seat rows. Refuses changes that would harm live shows."""
    validate_layout(layout)
    desired = _desired_seats(layout)
    existing = {(s.row_label, s.number_label): s for s in
                db.scalars(select(Seat).where(Seat.screen_id == screen.id)).all()}

    # Which existing seats are in use by upcoming, non-cancelled shows?
    in_use: set[int] = set()
    if existing:
        ids = [s.id for s in existing.values()]
        now = utcnow()
        booked = db.scalars(
            select(BookingSeat.seat_id).join(Show, Show.id == BookingSeat.show_id)
            .where(BookingSeat.seat_id.in_(ids), BookingSeat.is_active.is_(True),
                   Show.starts_at > now, Show.status == "scheduled")).all()
        locked = db.scalars(select(SeatLock.seat_id).where(SeatLock.seat_id.in_(ids), SeatLock.expires_at > now)).all()
        in_use = set(booked) | set(locked)

    problems = []
    for key, seat in existing.items():
        if seat.id not in in_use or not seat.is_active:
            continue
        want = desired.get(key)
        if want is None:
            problems.append(f"Seat {seat.label} cannot be removed: it has active bookings or holds")
        elif want["category"] != seat.category:
            problems.append(f"Seat {seat.label} cannot change category: it has active bookings or holds")
        elif want["disabled"] and not seat.is_disabled:
            problems.append(f"Seat {seat.label} cannot be disabled: it has active bookings or holds")
    if problems:
        raise LayoutError("Layout change blocked by existing bookings", problems)

    for key, want in desired.items():
        seat = existing.get(key)
        if seat is None:
            db.add(Seat(screen_id=screen.id, row_label=key[0], number_label=key[1],
                        grid_row=want["grid_row"], grid_col=want["grid_col"],
                        category=want["category"], is_disabled=want["disabled"]))
        else:
            seat.grid_row, seat.grid_col = want["grid_row"], want["grid_col"]
            seat.category, seat.is_disabled, seat.is_active = want["category"], want["disabled"], True
    for key, seat in existing.items():
        if key not in desired:
            seat.is_active = False  # soft-remove: history and old bookings stay valid

    screen.layout = layout
    screen.layout_version = (screen.layout_version or 0) + 1
    db.flush()
    return layout_summary(layout)
