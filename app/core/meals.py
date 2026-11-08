"""Bảng suất ăn: nhóm bảo mẫu, lớp gộp, lớp ghép."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

CODE_RE = re.compile(r"(\d)\s*[./]\s*(\d)")


@dataclass
class MealRow:
    row: int
    label: str  # nhãn cột J: "hiến", "1.2 ghép", "4.3 ghép 4.4"
    meal_cell: str  # ô số suất, vd. I73
    classes: list[str] = field(default_factory=list)  # lớp cộng nguyên lớp
    o_cell: str | None = None  # số em ghép (chỉ hàng có HS ghép lẻ)
    m_cell: str | None = None  # số em ghép vắng

    @property
    def code(self) -> str | None:
        """Mã nhóm ghép "1.2" (chỉ với hàng nhận HS ghép lẻ)."""
        if not self.o_cell:
            return None
        m = CODE_RE.search(self.label)
        return f"{m.group(1)}.{m.group(2)}" if m else None


@dataclass
class MealLayout:
    rows: list[MealRow] = field(default_factory=list)
    self_classes: list[str] = field(default_factory=list)  # lớp tự ăn tại lớp
    ghep_classes: list[str] = field(default_factory=list)  # lớp chia HS sang nhóm khác
    area: str = ""  # vùng in, vd. G68:O80
    o_values: dict[str, int] = field(default_factory=dict)  # cột O hiện có trong sổ

    def ghep_codes(self, khoi: int | None = None) -> list[str]:
        codes = [r.code for r in self.rows if r.code]
        if khoi is not None:
            codes = [c for c in codes if c.startswith(f"{khoi}.")]
        return codes

    def row_for_code(self, code: str) -> MealRow | None:
        for r in self.rows:
            if r.code == code:
                return r
        return None

    @property
    def is_empty(self) -> bool:
        return not self.rows


@dataclass
class MealLine:
    row: MealRow
    meals: int
    o: int | None = None
    m: int | None = None
    absent_names: list[str] = field(default_factory=list)


@dataclass
class MealSummary:
    lines: list[MealLine]
    self_meals: int
    total_meals: int
    total_present: int
    warnings: list[str] = field(default_factory=list)
    ask: list = field(default_factory=list)  # em ghép vắng chưa rõ ăn nhóm nào: (lớp, em)

    @property
    def group_meals(self) -> int:
        """Tổng suất các nhóm (ô G69 trong sổ); cộng với tự ăn tại lớp ra tổng suất."""
        return self.total_meals - self.self_meals

    @property
    def balanced(self) -> bool:
        return self.total_meals == self.total_present


def compute_meals(
    layout: MealLayout,
    present: dict[str, int],
    ghep_absent: dict[str, list[str]],
    o_values: dict[str, int],
) -> MealSummary:
    """present: hiện diện mỗi lớp; ghep_absent: mã nhóm -> tên em ghép vắng; o_values: mã -> số em ghép."""
    lines = []
    for r in layout.rows:
        meals = sum(present.get(c, 0) for c in r.classes)
        line = MealLine(r, meals)
        if r.code:
            names = ghep_absent.get(r.code, [])
            line.o = o_values.get(r.code, 0)
            line.m = len(names)
            line.absent_names = list(names)
            line.meals += line.o - line.m
        lines.append(line)
    self_meals = sum(present.get(c, 0) for c in layout.self_classes)
    total = sum(x.meals for x in lines) + self_meals
    return MealSummary(lines, self_meals, total, sum(present.values()))
