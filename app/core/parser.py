"""Đọc tin nhắn báo sĩ số của GVCN (dán từ Zalo).

Hiểu các dạng thường gặp:
    Lớp 1D15 : 29/31 Vắng : Hồ Khánh Ngọc ,Tuấn Anh
    Lớp 4D18: 38/41( lan, khuê, thanh mai)
    4D19.     37/38( vắng 1 Hoài Nam)
    Lớp 5D20: đủ          2D21: 10/10          4D22: vắng Toàn
    Vắng Duy Mạnh, tuấn Kiệt , Hải Long      (không ghi lớp)
Có thể dán nhiều tin một lúc; dòng tên người gửi ("cô Lan 1D15") và giờ gửi tự bỏ qua.

Tin chép từ Zalo trên máy tính có dòng đầu dạng
    [27/10/2026 07:29:30] Cô Mai: Lớp 1D15 :28/31
    Vắng Hồ Khánh Ngọc ,Tuấn Anh            (dòng không có [...] là phần tiếp của tin trên)
App giữ ngày giờ và người gửi của từng tin để lọc theo ngày và đoán lớp khi tin không ghi mã lớp.
Tin báo lịch ("tháng 11 cắt bán trú Gia Huy") được tách riêng, không tính là vắng.
"""

from __future__ import annotations

import datetime as dt
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
    # lời chào, xưng hô trong tin nhắn: "Dạ cô ơi lớp em đủ ạ"
    "dạ", "ơi", "vâng", "mình", "ok", "oke", "nhá", "nhen", "thêm",
}
STOP_FOLD = {"vang", "nghi", "phep", "khong", "om", "benh", "gom", "cac", "hom", "nay", "oi"}


@dataclass
class ParsedMessage:
    raw: str
    cls: str | None = None  # 1D15
    present: int | None = None
    total: int | None = None
    names: list[str] = field(default_factory=list)
    full: bool = False  # lớp báo đủ
    when: dt.datetime | None = None  # giờ gửi (tin chép từ Zalo máy tính)
    sender: str = ""  # tên Zalo người gửi
    schedule: str = ""  # phần báo lịch thêm/cắt bán trú trong tin, vd. "tháng 11 cắt bán trú Gia Huy"
    sender_class: str | None = None  # mã lớp ghi trong tên Zalo người gửi ("1D15 Cô Lan")

    @property
    def is_report(self) -> bool:
        """Tin có báo sĩ số / vắng (không chỉ báo lịch)."""
        return bool(self.names) or self.full or self.present is not None

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
        tokens = chunk.split()
        for i, w in enumerate(tokens):
            lw = lower(w)
            if lw in STOP or lw.isdigit():
                continue
            # chữ không dấu "vang/nghi/phep…": chỉ bỏ khi viết thường hoặc đứng đầu cụm ("Nghi phep Minh");
            # viết hoa giữa cụm là tên ("Hoàng Nghi")
            if fold(w) in STOP_FOLD and (w == w.lower() or (i == 0 and len(tokens) > 1)):
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


_ZALO_HEAD = re.compile(
    r"^\s*\[\s*(\d{1,2})/(\d{1,2})/(\d{2,4})[\s,]+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*\]\s?(.*)$"
)
_REPORT_WORD = re.compile(r"(?<!\w)(vang|nghi|du|ss|si so|hien dien)(?!\w)")
# Báo thêm/cắt bán trú (không phải báo vắng): "cắt …" (đúng dấu: "Cát Tiên" là tên), "tháng 11 thêm …",
# "thêm bán trú …", "thêm mới 1 HS: …", "bổ sung …", "chuyển trường …", "thôi ăn", "từ mai … nghỉ ăn".
# Không đụng tới "vắng thêm …" và "nghỉ: A, B" (là báo vắng).
_SCHED = re.compile(
    r"(?<!\w)(?:(?:từ\s*(?:ngày\s*)?)?\d{1,2}\s*/\s*\d{1,2}\s*|(?:tháng|t)\s*\d{1,2}\s*"
    r"|từ\s*(?:ngày\s*)?mai\s*|(?:đầu\s*)?tháng\s*sau\s*)?"
    r"(?:cắt|(?<!vắng )(?<!nghỉ )thêm(?=\s*bán\s*trú))(?!\w)"
    r"|(?<!\w)(?:(?:từ\s*(?:ngày\s*)?)?\d{1,2}\s*/\s*\d{1,2}|(?:tháng|t)\s*\d{1,2}|(?:đầu\s*)?tháng\s*sau)\s*thêm(?!\w)"
    r"|(?<!\w)(?<!vắng )(?<!nghỉ )thêm\s+(?:mới|\d+\s*(?:em|hs|học\s*sinh|bạn)|em|hs|học\s*sinh|bạn)(?!\w)"
    r"|(?<!\w)bổ\s*sung(?!\w)"
    r"|(?<!\w)chuyển\s*(?:trường|lớp|đi)(?!\w)"
    r"|(?<!\w)(?:thôi|ngưng|dừng)\s*ăn(?!\w)"
    r"|(?<!\w)không\s*ăn(?:\s*bán\s*trú)?\s*nữa(?!\w)"
    r"|(?<!\w)nghỉ\s*ăn(?=\s*(?:bán\s*trú|từ|luôn|hẳn|nữa))"
    r"|(?<!\w)từ\s*(?:ngày\s*)?mai(?=[^\n.]*?(?:nghỉ|thôi|không)\s*ăn)"
)
_SCHED_END = re.compile(r"(?i)(?<!\w)(vắng|nghỉ)(?!\w)(?!\s*ăn)")
# Báo cắt mà tên em đứng TRƯỚC: "Mai Thanh thôi ăn từ thứ 2", "Tuấn Kiệt chuyển trường"
_NAME_BEFORE = re.compile(r"(?:thôi|ngưng|dừng|nghỉ|không)\s*ăn|chuyển\s*(?:trường|lớp|đi)")


@dataclass
class ZaloLine:
    when: dt.datetime | None
    sender: str
    body: str


def split_zalo(text: str) -> list[ZaloLine] | None:
    """Tách tin chép từ Zalo máy tính theo dòng '[ngày giờ] Người gửi: nội dung'.

    Trả về None nếu đoạn dán không có dòng nào dạng đó (dán kiểu cũ)."""
    out: list[ZaloLine] = []
    lead: list[str] = []
    for line in nfc(text).splitlines():
        m = _ZALO_HEAD.match(line)
        if not m:
            if out:
                out[-1].body += "\n" + line
            else:
                lead.append(line)
            continue
        d, mo, y, hh, mm, ss, rest = m.groups()
        year = int(y) + (2000 if len(y) == 2 else 0)
        try:
            when = dt.datetime(year, int(mo), int(d), int(hh), int(mm), int(ss or 0))
        except ValueError:
            when = None
        sender, body = "", rest
        if ":" in rest:
            head, tail = rest.split(":", 1)
            if head.strip() and len(head) <= 40 and not CLASS_RE.search(head):
                sender, body = head.strip(), tail
            elif head.strip() and len(head) <= 40 and not _COUNT.search(head) and fold(head).startswith(_HEADER_START):
                sender, body = head.strip(), tail  # tên Zalo có mã lớp, vd. "Cô Lan 1D15"
        out.append(ZaloLine(when, sender, body.strip()))
    if not out:
        return None
    if any(x.strip() for x in lead):
        out.insert(0, ZaloLine(None, "", "\n".join(lead)))
    return out


def split_schedule(body: str) -> tuple[str, str]:
    """Tách các phần báo thêm/cắt bán trú ra khỏi tin. Trả về (phần còn lại, các phần báo lịch nối bằng "; ").

    Mỗi phần báo lịch kéo tới hết câu/dòng, hoặc tới chữ "vắng/nghỉ" phía sau nếu có."""
    text = nfc(body)
    found: list[str] = []
    while True:
        m = _SCHED.search(text.lower())
        if not m:
            break
        start = m.start()
        if _NAME_BEFORE.match(text.lower(), start):
            # lấy cả tên em phía trước, tới đầu vế câu (sau dấu câu, chữ "vắng/nghỉ" hay mã lớp)
            cut = max(text.rfind(ch, 0, start) for ch in ".;,:\n") + 1
            head = text[cut:start]
            ends = [x.end() for x in _SCHED_END.finditer(head)] + [x.end() for x in CLASS_RE.finditer(head)]
            start = cut + max(ends, default=0)
            while start < m.start() and text[start].isspace():
                start += 1
        line_end = text.find("\n", m.start())
        line_end = len(text) if line_end < 0 else line_end
        stop = _SCHED_END.search(text, m.end(), line_end)
        end = stop.start() if stop and stop.start() > m.end() else line_end
        part = text[start:end].strip(" ,.;:()-\n")
        if part:
            found.append(part)
        text = (text[:start] + " " + text[end:]).strip()
    return text, "; ".join(found)


def parse_messages(text: str, known_classes: set[str] | None = None) -> list[ParsedMessage]:
    """Tách và đọc các tin nhắn trong đoạn văn bản dán vào."""
    zl = split_zalo(text)
    if zl is not None:
        return _parse_zalo(zl, known_classes)
    return _parse_plain(text, known_classes)


def _parse_zalo(lines: list[ZaloLine], known_classes: set[str] | None) -> list[ParsedMessage]:
    known = set(known_classes) if known_classes else None
    out: list[ParsedMessage] = []
    for z in sorted(lines, key=lambda x: x.when or dt.datetime.min):
        rest, sched = split_schedule(z.body)
        sender_codes = _class_codes(z.sender, known) if z.sender else []
        sender_class = f"{sender_codes[0].group(1)}D{sender_codes[0].group(2)}" if sender_codes else None
        msgs = _parse_plain(rest, known_classes) if rest.strip() else []
        if not msgs:
            body = _preclean(rest, known)
            m = _parse_segment(rest, body, None)
            has_word = _REPORT_WORD.search(fold(body)) is not None
            if m.full or m.present is not None or (m.names and has_word) or sched:
                if not has_word and m.present is None and not m.full:
                    m.names = []  # chỉ báo lịch, phần còn lại là lời chào…
                msgs = [m]
        else:
            # tin không ghi lớp mà cũng không có chữ "vắng/nghỉ…": lời chào, cảm ơn… -> bỏ
            msgs = [m for m in msgs if m.cls or m.present is not None or m.full
                    or _REPORT_WORD.search(fold(m.raw))]
            if sched and not msgs:
                msgs = [ParsedMessage(raw=rest.strip())]
        for i, m in enumerate(msgs):
            m.when, m.sender, m.sender_class = z.when, z.sender, sender_class
            if i == 0 and sched:
                m.schedule = sched
                if m.cls is None:
                    codes = _class_codes(z.body, known)
                    if codes:
                        m.cls = f"{codes[0].group(1)}D{codes[0].group(2)}"
            out.append(m)
    return out


def _parse_plain(text: str, known_classes: set[str] | None = None) -> list[ParsedMessage]:
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
        # phần báo thêm/cắt ("Thêm mới 1 HS: …", "Cắt bán trú …") không phải tên vắng
        raw, sched = split_schedule(raw)
        rest = ""
        if cls:
            raw, rest = _cut_complete(raw)
        body = CLASS_RE.sub(" ", raw) if cls else raw
        msg = _parse_segment(raw, body, cls)
        msg.schedule = sched
        # tin riêng không ghi lớp: "đủ", "32/34 đủ" cũng là tin báo (giáo vụ sẽ chọn lớp)
        if cls is not None or msg.is_report:
            out.append(msg)
        if rest.strip():
            extra = _parse_segment(rest, rest, None)
            if extra.is_report:
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
