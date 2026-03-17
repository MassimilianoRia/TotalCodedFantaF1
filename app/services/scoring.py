RACE_POINTS = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}
SPRINT_POINTS = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}
TOP10_CONSTRUCTOR_EXACT = {0: 10, 1: 8, 2: 6, 3: 5, 4: 5, 5: 6}


def quali_points(pos: int | None) -> float:
    if pos is None:
        return 0
    if pos == 1:
        return 5
    if 2 <= pos <= 5:
        return 3
    if 6 <= pos <= 10:
        return 2
    if 11 <= pos <= 16:
        return 1
    return 0


def status_points(status: str) -> float:
    if status in {"dnf", "dns"}:
        return -10
    if status == "dsq":
        return -15
    return 0


def bucket_from_total(total: float) -> str:
    if total <= 40:
        return "LE40"
    if total <= 80:
        return "MID80"
    return "GT80"
