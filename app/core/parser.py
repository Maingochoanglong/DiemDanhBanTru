"""Tách tên học sinh từ chữ: ô "Tên học sinh vắng" trong sổ, ghi chú lớp.

    "Hồ Khánh Ngọc ,Tuấn Anh"            -> ["Hồ Khánh Ngọc", "Tuấn Anh"]
    "31/41 (Hoàng Nghi, Gia Lâm)"        -> ["Hoàng Nghi", "Gia Lâm"]
    "vang Minh Anh, nghi phep Bao Ngoc"  -> ["Minh Anh", "Bao Ngoc"]
"""

from __future__ import annotations

import re

from .text import fold, lower

_COUNT = re.compile(r"(?<!\d)(\d{1,3})\s*/\s*(\d{1,3})(?!\d)")
_LOP_WORD = re.compile(r"(?i)(?<!\w)l[ớo]p(?!\w)")
_HOC_SINH = re.compile(r"(?i)(?<!\w)h[ọo]c\s+sinh(?!\w)")
_ABBR = re.compile(r"(?<![^\W\d_])([^\W\d_])\.\s*(?=[^\W\d_])")
_SPLIT = re.compile(r"[,;:()\[\]{}\n\r/+.!?…\-–—]|\s+(?:và|va|vs)\s+", re.IGNORECASE)

STOP = {
    "vắng", "nghỉ", "nghĩ", "em", "hs", "các", "gồm", "có", "không", "phép", "đủ",
    "sĩ", "số", "ss", "cp", "kp", "ốm", "bệnh", "sốt", "lý", "do", "bạn", "là", "ạ",
    "nha", "nhé", "cô", "thầy", "ăn", "bán", "trú", "bt", "hôm", "nay", "sáng", "ngày",
    "tổng", "hiện", "diện", "còn", "chỉ", "thôi",
    # lời chào, xưng hô trong tin nhắn: "Dạ cô ơi lớp em đủ ạ"
    "dạ", "ơi", "vâng", "mình", "ok", "oke", "nhá", "nhen", "thêm",
}
STOP_FOLD = {"vang", "nghi", "phep", "khong", "om", "benh", "gom", "cac", "hom", "nay", "oi"}


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
