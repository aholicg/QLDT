from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def _read(slot: Any, *names: str) -> Any:
    for name in names:
        if isinstance(slot, Mapping):
            if name in slot:
                return slot[name]
        if hasattr(slot, name):
            return getattr(slot, name)
    return None


def _normalize_day(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    return int(value)


def _overlap(a0: int, a1: int, b0: int, b1: int) -> tuple[int, int] | None:
    start = max(a0, b0)
    end = min(a1, b1)
    if start <= end:
        return start, end
    return None


def find_conflicts(slots: Iterable[Any]) -> list[dict[str, Any]]:
    """Return schedule conflicts between candidate blocks.

    Each slot may be a dict or an object that exposes ordinary timetable fields.
    """
    items = list(slots)
    conflicts: list[dict[str, Any]] = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            left = items[i]
            right = items[j]

            left_day = _normalize_day(_read(left, "dayOfWeek", "day_of_week", "day", "weekday"))
            right_day = _normalize_day(_read(right, "dayOfWeek", "day_of_week", "day", "weekday"))
            if left_day is None or right_day is None or left_day != right_day:
                continue

            left_start = int(_read(left, "startPeriod", "start_period", "startPeriodIndex") or 0)
            left_end = int(_read(left, "endPeriod", "end_period", "endPeriodIndex") or left_start)
            right_start = int(_read(right, "startPeriod", "start_period", "startPeriodIndex") or 0)
            right_end = int(
                _read(right, "endPeriod", "end_period", "endPeriodIndex") or right_start
            )
            overlap_periods = _overlap(left_start, left_end, right_start, right_end)
            if overlap_periods is None:
                continue

            left_week_start = int(_read(left, "startWeek", "start_week", "weekStart") or 1)
            left_week_end = int(_read(left, "endWeek", "end_week", "weekEnd") or left_week_start)
            right_week_start = int(_read(right, "startWeek", "start_week", "weekStart") or 1)
            right_week_end = int(_read(right, "endWeek", "end_week", "weekEnd") or right_week_start)
            overlap_weeks = _overlap(
                left_week_start, left_week_end, right_week_start, right_week_end
            )
            if overlap_weeks is None:
                continue

            left_label = _read(left, "sectionCode", "section_code", "code", "name") or "A"
            right_label = _read(right, "sectionCode", "section_code", "code", "name") or "B"
            conflict_types: list[str] = []
            if _read(left, "roomId", "room_id") is not None and _read(
                left, "roomId", "room_id"
            ) == _read(right, "roomId", "room_id"):
                conflict_types.append("ROOM")
            if _read(left, "lecturerId", "lecturer_id") is not None and _read(
                left, "lecturerId", "lecturer_id"
            ) == _read(right, "lecturerId", "lecturer_id"):
                conflict_types.append("LECTURER")
            if not conflict_types:
                conflict_types.append("STUDENT")

            for conflict_type in conflict_types:
                conflicts.append(
                    {
                        "type": conflict_type,
                        "sectionA": left_label,
                        "sectionB": right_label,
                        "dayOfWeek": left_day,
                        "periods": {"start": overlap_periods[0], "end": overlap_periods[1]},
                        "weeks": {"start": overlap_weeks[0], "end": overlap_weeks[1]},
                        "message": f"[{conflict_type}] Trùng lịch giữa {left_label} và {right_label}",
                    }
                )
    return conflicts


def suggest_timetables(
    slots: Iterable[Any],
    *,
    avoid_early: int | None = None,
    avoid_late: int | None = None,
    blocked_days: Iterable[int] | None = None,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """Generate a small number of conflict-free timetable suggestions."""
    items = list(slots)
    blocked = set(blocked_days or [])
    results: list[dict[str, Any]] = []

    for index, item in enumerate(items):
        day = _normalize_day(_read(item, "dayOfWeek", "day_of_week", "day", "weekday"))
        if day is None or day in blocked:
            continue
        start = int(_read(item, "startPeriod", "start_period") or 0)
        end = int(_read(item, "endPeriod", "end_period") or start)
        if avoid_early is not None and start < avoid_early:
            continue
        if avoid_late is not None and end > avoid_late:
            continue
        results.append(
            {
                "index": index,
                "sectionCode": _read(item, "sectionCode", "section_code", "code") or f"S{index}",
                "dayOfWeek": day,
                "startPeriod": start,
                "endPeriod": end,
                "startWeek": int(_read(item, "startWeek", "start_week") or 1),
                "endWeek": int(_read(item, "endWeek", "end_week") or 1),
            }
        )

    if not results:
        return []

    candidate_conflicts = find_conflicts(results)
    if not candidate_conflicts:
        return results[:max_results]

    filtered: list[dict[str, Any]] = []
    for item in results:
        item_conflicts = [
            conflict
            for conflict in candidate_conflicts
            if conflict["sectionA"] == item["sectionCode"]
            or conflict["sectionB"] == item["sectionCode"]
        ]
        if not item_conflicts:
            filtered.append(item)

    return filtered[:max_results]
