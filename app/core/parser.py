"""Đọc tin nhắn báo sĩ số của GVCN (dán từ Zalo).

Hiểu các dạng thường gặp:
    Lớp 1D15 : 29/31 Vắng : Hồ Khánh Ngọc ,Tuấn Anh
    Lớp 4D18: 38/41( lan, khuê, thanh mai)
    4D19.     37/38( vắng 1 Hoài Nam)
    Lớp 5D20: đủ          2D21: 10/10          4D22: vắng Toàn
    Vắng Duy Mạnh, tuấn Kiệt , Hải Long      (không ghi lớp)
Có thể dán nhiều tin một lúc; dòng tên người gửi ("cô Lan 1D15") và giờ gửi tự bỏ qua.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .text import CLASS_RE, fold, lower, nfc

_TIME = re.compile(r"(?<![\w/])\d{1,2}:\d{2}(?::\d{2})?(?![\d/])")
_DATE_FULL = re.compile(r"(?<![\w/])\d{1,2}/\d{1,2}/\d{2,4}(?![\d/])")
_WEEKDAY_DATE = re.compile(r"(?i)\b(?:T[2-7]|CN)\s*,\s*\d{1,2}/\d{1,2}(?!\d|\s*/)")
_COUNT = re.compile(r"(?<!\d)(\d{1,3})\s*/\s*(\d{1,3})(?!\d)")
_KHOI_ROLE = re.compile(
    r"(?i)\(?\s*kh[ốôo]i\s*(?:tr[ưu][ởo]ng|ph[óo]|t[^\s,;:)]*(?:\.\.\.|…))\s*\)?"
)
_LOP_WORD = re.compile(r"(?i)(?<!\w)l[ớo]p(?!\w)")
_HOC_SINH = re.compile(r"(?i)(?<!\w)h[ọo]c\s+sinh(?!\w)")
_ABBR = re.compile(r"(?<![^\W\d_])([^\W\d_])\.\s*(?=[^\W\d_])")
_SPLIT = re.compile(r"[,;:()\[\]{}\n\r/+.!?…\-–—]|\s+(?:và|va|vs)\s+", re.IGNORECASE)
_HEADER_START = ("co ", "thay ", "gv ", "gvcn ", "c ", "t ")

STOP = {
    "vắng", "nghỉ", "nghĩ", "em", "hs", "các", "gồm", "có", "không", "phép", "đủ",
    "sĩ", "số", "ss", "cp", "kp", "ốm", "bệnh", "sốt", "lý", "do", "bạn", "là", "ạ",
    "nha", "nhé", "cô", "thầy", "ăn", "bán", "trú", "bt", "hôm", "nay", "sáng", "ngày",
    "tổng", "hiện", "diện", "còn", "chỉ", "thôi",
}
STOP_FOLD = {"vang", "nghi", "phep", "khong", "om", "benh", "gom", "cac", "hom", "nay"}


@dataclass
class ParsedMessage:
    raw: str
    cls: str | None = None  # 1D15
    present: int | None = None
    total: int | None = None
    names: list[str] = field(default_factory=list)
    full: bool = False  # lớp báo đủ
    guessed: bool = False  # lớp do app đoán (tin không ghi lớp)

    @property
    def reported_absent(self) -> int | None:
        if self.present is not None and self.total is not None:
            return self.total - self.present
        return None


def _strip_symbols(text: str) -> str:
    out = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat in ("So", "Cs", "Co", "Cn") or 0xFE00 <= ord(ch) <= 0xFE0F or ord(ch) == 0x200D:
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


def _class_codes(text: str, known: set[str] | None) -> list[re.Match]:
    out = []
    for m in CLASS_RE.finditer(text):
        code = f"{m.group(1)}D{m.group(2)}"
        if not known or code in known:
            out.append(m)
    return out


def _is_header_line(line: str, known: set[str] | None) -> bool:
    """Dòng tên người gửi trong Zalo: 'cô Lan 1D15', 'thầy Nuôi 3D19'."""
    f = fold(line)
    if not f.startswith(_HEADER_START):
        return False
    if not _class_codes(line, known):
        return False
    return ":" not in line and not _COUNT.search(line)


def _preclean(text: str, known: set[str] | None) -> str:
    text = _strip_symbols(nfc(text))
    text = _DATE_FULL.sub(" ", text)
    text = _WEEKDAY_DATE.sub(" ", text)
    text = _TIME.sub(" ", text)
    text = _KHOI_ROLE.sub(" ", text)
    lines = []
    for line in text.splitlines():
        if _is_header_line(line, known):
            m = _class_codes(line, known)[0]
            line = f"{m.group(1)}D{m.group(2)}"
        lines.append(line)
    return "\n".join(lines)


def extract_names(body: str) -> list[str]:
    body = _LOP_WORD.sub(" ", body)
    body = _HOC_SINH.sub(" ", body)
    body = _COUNT.sub(" ", body)
    body = _ABBR.sub(lambda m: m.group(1) + " ", body)
    names = []
    for chunk in _SPLIT.split(body):
        if not chunk:
            continue
        kept = []
        for w in chunk.split():
            lw = lower(w)
            if lw in STOP or fold(w) in STOP_FOLD or lw.isdigit():
                continue
            if not any(ch.isalpha() for ch in w):
                continue
            kept.append(w)
        if kept:
            names.append(" ".join(kept))
    return names


def _parse_segment(raw: str, body: str, cls: str | None) -> ParsedMessage:
    msg = ParsedMessage(raw=raw.strip(), cls=cls)
    m = _COUNT.search(body)
    if m:
        msg.present, msg.total = int(m.group(1)), int(m.group(2))
    msg.names = extract_names(body)
    said_full = re.search(r"(?<!\w)đủ(?!\w)", lower(body)) is not None or (
        re.search(r"(?<!\w)du(?!\w)", fold(body)) is not None and not msg.names
    )
    count_full = msg.present is not None and msg.present == msg.total
    msg.full = not msg.names and (said_full or count_full)
    return msg


def parse_messages(text: str, known_classes: set[str] | None = None) -> list[ParsedMessage]:
    """Tách và đọc các tin nhắn trong đoạn văn bản dán vào."""
    known = set(known_classes) if known_classes else None
    text = _preclean(text, known)
    matches = _class_codes(text, known)

    segments: list[tuple[str | None, int, int]] = []  # (lớp, đầu, cuối)
    if not matches:
        for para in re.split(r"\n\s*\n", text):
            if para.strip():
                start = text.find(para)
                segments.append((None, start, start + len(para)))
    else:
        if text[: matches[0].start()].strip():
            segments.append((None, 0, matches[0].start()))
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            segments.append((f"{m.group(1)}D{m.group(2)}", m.start(), end))

    # Gộp các đoạn liền nhau cùng lớp (dòng tên người gửi + nội dung tin)
    merged: list[tuple[str | None, int, int]] = []
    for seg in segments:
        if merged and seg[0] is not None and merged[-1][0] == seg[0]:
            merged[-1] = (seg[0], merged[-1][1], seg[2])
        else:
            merged.append(seg)

    out = []
    for cls, start, end in merged:
        raw = text[start:end]
        rest = ""
        if cls:
            raw, rest = _cut_complete(raw)
        body = CLASS_RE.sub(" ", raw) if cls else raw
        msg = _parse_segment(raw, body, cls)
        if cls is not None or msg.names:
            out.append(msg)
        if rest.strip():
            extra = _parse_segment(rest, rest, None)
            if extra.names:
                out.append(extra)
    return out


def _is_complete(msg: ParsedMessage, next_line: str) -> bool:
    """Tin của lớp đã đủ ý chưa (để biết dòng sau là tin khác)."""
    if msg.full:
        return True
    if msg.reported_absent is not None:
        return len(msg.names) >= msg.reported_absent
    return bool(msg.names) and fold(next_line).startswith("vang")


def _cut_complete(raw: str) -> tuple[str, str]:
    """Tách phần thuộc tin của lớp và phần dòng phía sau là tin khác (không ghi lớp)."""
    lines = raw.split("\n")
    for i in range(len(lines)):
        rest = [x for x in lines[i + 1:] if x.strip()]
        if not rest:
            break
        part = "\n".join(lines[: i + 1])
        msg = _parse_segment(part, CLASS_RE.sub(" ", part), "x")
        if _is_complete(msg, rest[0]):
            return part, "\n".join(lines[i + 1:])
    return raw, ""
