"""Tin Zalo chép từ máy tính: '[ngày giờ] Người gửi: nội dung'. Tên người/HS đều là tên bịa."""

import datetime as dt

from app.core.parser import parse_messages, split_schedule, split_zalo
from app.core.senders import match_teacher
from tests.test_service import ws  # noqa: F401 - fixture

LOG = """[28/10/2026 07:25:40] Kim Trang: Vắng Duy Mạnh và Hải Long
[28/10/2026 07:26:14] Yến Nhi: Lớp 1D15 :5/6
Vắng Tuấn Anh
[29/10/2026 07:20:01] Yến Nhi: Lớp 1D15 :5/6
Vắng : Khánh Ngọc
[29/10/2026 07:21:00] Kim Trang: Dạ cô
[29/10/2026 07:22:13] Kim Trang: Vắng Duy Mạnh
[29/10/2026 07:40:00] Yến Nhi: Lớp 1D15: 6/6 đủ ạ
[29/10/2026 07:41:00] Lucton: 1d16 đủ
[29/10/2026 10:32:31] Yến Nhi: Lớp 1D15: tháng 11 cắt bán trú Minh Khôi
"""


def test_split_zalo_lines():
    lines = split_zalo(LOG)
    assert len(lines) == 8
    assert lines[1].sender == "Yến Nhi"
    assert lines[1].when == dt.datetime(2026, 10, 28, 7, 26, 14)
    assert lines[1].body == "Lớp 1D15 :5/6\nVắng Tuấn Anh"  # dòng tiếp theo thuộc tin trên
    assert split_zalo("Lớp 1D15: đủ") is None  # dán kiểu cũ


def test_parse_zalo_messages():
    msgs = parse_messages(LOG, {"1D15", "1D16", "2D17"})
    first = msgs[0]
    assert first.cls is None and first.sender == "Kim Trang" and first.names == ["Duy Mạnh", "Hải Long"]
    assert [m.names for m in msgs if m.sender == "Kim Trang"] == [["Duy Mạnh", "Hải Long"], ["Duy Mạnh"]]  # "Dạ cô" bỏ
    last = msgs[-1]
    assert last.cls == "1D15" and last.schedule == "tháng 11 cắt bán trú Minh Khôi"
    assert not last.is_report and last.names == []


def test_split_schedule_keeps_absences():
    rest, sched = split_schedule("29/31 vắng Tuấn Anh, Bảo Ngọc. Từ mai cắt bán trú Minh Khôi")
    assert sched == "Từ mai cắt bán trú Minh Khôi" and "Tuấn Anh" in rest
    assert split_schedule("vắng Cát Tiên, Minh Khôi") == ("vắng Cát Tiên, Minh Khôi", "")  # "Cát" là tên
    assert split_schedule("vắng thêm Minh Khôi")[1] == ""  # "vắng thêm" không phải thêm bán trú
    assert split_schedule("Tháng 11 thêm Hồng Nhung")[1] == "Tháng 11 thêm Hồng Nhung"


def test_match_teacher():
    gv = {
        "2D17": "Lương Thị Kim Trang",
        "1D15": "Mạc Thị Yến Nhi",
        "1D16": "Tôn Văn Lực",
        "3D18": "Đào Anh Thư",
        "4D22": "Ninh Thị Diệp Anh",
        "5D22": "Kha Thị Diệp",
        "5D21": "Hứa Thị Thanh Hà",
        "1D18": "Âu Thị Thu Hà",
    }
    assert match_teacher("Trang Lương", gv) == "2D17"
    assert match_teacher("Kim Trang", gv) == "2D17"
    assert match_teacher("Lucton", gv) == "1D16"  # viết liền, đảo thứ tự
    assert match_teacher("Daoanhthu", gv) == "3D18"
    assert match_teacher("Cô Yến Nhi 🌸", gv) == "1D15"
    assert match_teacher("Thu Hà", gv) == "1D18"
    assert match_teacher("Hà", gv) is None  # 2 cô tên Hà
    assert match_teacher("Diệp Diệp", gv) == "5D22"  # ưu tiên tên gọi
    assert match_teacher("Diệp Anh", gv) == "4D22"
    assert match_teacher("Bông Mexico", gv) is None


def _with_gvcn(ws):  # noqa: F811
    ws.roster.classes["2D17"].gvcn = "Lương Thị Kim Trang"
    ws.roster.classes["1D15"].gvcn = "Mạc Thị Yến Nhi"
    ws.roster.classes["1D16"].gvcn = "Tôn Văn Lực"


def test_paste_zalo_only_open_day(ws):  # noqa: F811
    _with_gvcn(ws)
    ws.load_day(dt.date(2026, 10, 29))
    out = ws.paste(LOG)
    assert ws.paste_skipped == {dt.date(2026, 10, 28): 2}
    st = ws.state
    assert st.absent_names("1D15") == []  # tin 07:40 "đủ" ghi đè tin 07:20
    assert st.cd("1D15").reported
    # tin không ghi lớp: KHÔNG tự xếp lớp, chờ giáo vụ chọn; lớp theo tên Zalo (GVCN) được gợi ý đầu
    m = next(po for po in out if po.message.cls is None and po.message.names == ["Duy Mạnh"])
    assert m.guessed_from[0] == "2D17" and m.message in ws.unplaced
    assert st.absent_names("2D17") == [] and ws.unresolved_count() == 1
    ws.assign_unplaced(m.message, "2D17")
    assert st.absent_names("2D17") == ["Duy Mạnh"]
    assert st.cd("1D16").reported

    sched = [po for po in out if po.message.schedule]
    assert len(sched) == 1 and len(sched[0].suggestions) == 1
    sug = sched[0].suggestions[0]
    assert sug.student.ho_ten == "Tô Minh Khôi" and sug.changes == {"cat_tu": dt.date(2026, 11, 1)}
    note = ws.apply_paste_suggestion(sug)
    assert note == "Tháng 11 cắt bán trú Tô Minh Khôi"
    assert note in st.cd("1D15").note
    assert ws.roster.by_id(sug.student.id).cat_tu == dt.date(2026, 11, 1)
    # dán lại: lịch đã có, không đề nghị nữa
    again = [po for po in ws.paste(LOG) if po.message.schedule]
    assert again[0].schedule_known and not again[0].suggestions


def test_paste_learns_sender_class(ws):  # noqa: F811
    ws.load_day(dt.date(2026, 10, 29))
    ws.paste("[29/10/2026 07:00:00] Bông Mexico: 2D17: vắng Hải Long")
    out = ws.paste("[29/10/2026 07:30:00] Bông Mexico: Vắng Mạnh Viên")  # không ghi lớp, không khớp GVCN
    # vẫn hỏi lớp; lớp người này đã báo lần trước được gợi ý đầu
    assert out[0].message.cls is None and out[0].guessed_from[0] == "2D17"
    assert ws.data_dirty


def test_message_without_class_always_asks(ws):  # noqa: F811
    """Mọi tin không ghi mã lớp đều chờ giáo vụ chọn lớp (không tự xếp, không ghi chú "tự phân lớp")."""
    _with_gvcn(ws)
    ws.load_day(dt.date(2026, 10, 29))
    # người gửi lạ: gợi ý theo tên học sinh; tên Zalo giống GVCN: gợi ý lớp của GVCN
    for text, hint in [("[29/10/2026 07:00:00] Người Lạ: Vắng Duy Mạnh, Hải Long", "2D17"),
                       ("[29/10/2026 07:05:00] Kim Trang: Vắng Duy Mạnh", "2D17"),
                       ("[29/10/2026 07:06:00] Kim Trang: đủ ạ", "2D17")]:
        po = ws.paste(text)[0]
        assert po.message.cls is None and po.guessed_from[0] == hint, text
        assert po.message in ws.unplaced
    assert ws.state.absent_count("2D17") == 0 and not ws.state.cd("2D17").reported
    # chọn lớp: ghi vào lớp đó, nhớ người gửi để lần sau gợi ý đầu
    m = ws.unplaced[1]
    ws.assign_unplaced(m, "2D17")
    assert ws.state.absent_names("2D17") == ["Duy Mạnh"]


def test_private_message_without_class_asks_for_class(ws):  # noqa: F811
    """Tin riêng chép 1 tin (không lớp, không người gửi): không tự xếp lớp, chặn lưu tới khi chọn lớp."""
    ws.load_day(dt.date(2026, 10, 29))
    out = ws.paste("Vắng Duy Mạnh, Hải Long")
    assert out[0].message.cls is None and out[0].guessed_from == ["2D17"]
    assert ws.state.absent_count("2D17") == 0 and ws.unresolved_count() == 2
    for text in ("đủ", "Đủ ạ", "32/34 đủ", "Lớp em đủ", "Dạ cô ơi lớp em đủ ạ"):
        ws.load_day(dt.date(2026, 10, 29))
        out = ws.paste(text)
        assert len(out) == 1, text
        m = out[0].message
        assert m.cls is None and m.full and not m.names, text
        assert ws.unplaced == [m] and ws.unresolved_count() == 1, text
    # tin cuối "Dạ cô ơi lớp em đủ ạ": chọn lớp 1D16 -> lớp đủ, hết chặn lưu
    ws.assign_unplaced(m, "1D16")
    assert ws.state.cd("1D16").reported and ws.state.absent_count("1D16") == 0
    assert ws.unresolved_count() == 0
    # "32/34 đủ": chọn lớp thì giữ số GV báo để đối chiếu
    ws.load_day(dt.date(2026, 10, 29))
    m = ws.paste("32/34 đủ")[0].message
    ws.assign_unplaced(m, "1D16")
    c = ws.state.cd("1D16")
    assert (c.teacher_present, c.teacher_total) == (32, 34)
    # tin có mã lớp vẫn ưu tiên mã lớp
    assert ws.paste("1D15 đủ")[0].message.cls == "1D15"


def test_unresolved_names_and_unplaced_messages(ws):  # noqa: F811
    ws.load_day(dt.date(2026, 10, 29))
    ws.paste("Lớp 1D15: 5/6 vắng Bảo Ngọc")  # 3 em Bảo Ngọc -> chưa rõ
    assert ws.pending_names() == {"1D15": ["Bảo Ngọc"]}
    assert ws.unresolved_count() == 1
    ws.paste("[29/10/2026 07:00:00] Ai Đó: Vắng Xyz Qwe")
    ws.paste("[29/10/2026 07:00:00] Ai Đó: Vắng Xyz Qwe")  # dán lại không nhân đôi
    assert [m.names for m in ws.unplaced] == [["Xyz Qwe"]]
    assert ws.unresolved_count() == 2
    res = ws.assign_unplaced(ws.unplaced[0], "2D17")
    assert ws.unplaced == [] and res[0].status != "ok"
    assert ws.pending_names()["2D17"] == ["Xyz Qwe"]
    assert ws.unresolved_count() == 2
    # mỗi tên chưa rõ đều có lối ra: chọn em / giữ nguyên chữ / bỏ qua -> hết chặn lưu
    for code, r in list(ws.state.pending):
        ws.state.resolve_pending(code, r, None, keep_raw=(code == "1D15"))
    assert ws.unresolved_count() == 0
    ws.load_day(dt.date(2026, 10, 29))
    assert ws.unplaced == [] and ws.unresolved_count() == 0


def test_names_that_look_like_stop_words():
    from app.core.parser import extract_names

    assert extract_names("31/41 (Hoàng Nghi, Gia Lâm)") == ["Hoàng Nghi", "Gia Lâm"]
    assert extract_names("vang Minh Anh, nghi phep Bao Ngoc") == ["Minh Anh", "Bao Ngoc"]
    assert extract_names("Vang Minh Anh") == ["Minh Anh"]
    assert extract_names("vắng: Duy kien, quỳnh anh") == ["Duy kien", "quỳnh anh"]


def test_zalo_multi_line_and_multi_class_messages():
    log = """[30/10/2026 07:34:45] Cô A: 1D16 vắng 2:
- Gia Hưng
- Thanh Vy
4/6
[30/10/2026 07:42:18] Cô B: Lớp 1D19: 2/4( Bảo Ngọc, Gia Hân
[30/10/2026 08:03:21] Cô C: 2D17. 3/4. Vắng Hải Long
1D15 bán trú vắng 1 Tuấn Anh. 5/6
4D19 vắng Hoài Nam nha"""
    got = {m.cls: (m.present, m.total, m.names) for m in parse_messages(log, {"1D15", "1D16", "1D19", "2D17", "4D19"})}
    assert got == {
        "1D16": (4, 6, ["Gia Hưng", "Thanh Vy"]),
        "1D19": (2, 4, ["Bảo Ngọc", "Gia Hân"]),
        "2D17": (3, 4, ["Hải Long"]),
        "1D15": (5, 6, ["Tuấn Anh"]),
        "4D19": (None, None, ["Hoài Nam"]),
    }


def test_add_or_cut_lines_are_not_absent_names():
    """Tin kèm thêm/cắt bán trú: phần đó không phải tên vắng (tin chép riêng và tin Zalo có người gửi)."""
    known = {"2D17", "3D18"}
    cases = [
        ("3D18: 38/41\nVắng 2: Hải Long, Tuấn Kiệt\nThêm mới 1 HS: Nguyễn Văn Mới", ["Hải Long", "Tuấn Kiệt"],
         "Thêm mới 1 HS: Nguyễn Văn Mới"),
        ("3D18: 38/41 vắng Hải Long. Thêm 1 em Văn Mới", ["Hải Long"], "Thêm 1 em Văn Mới"),
        ("2D17 vắng Hải Long, chuyển trường Tuấn Kiệt", ["Hải Long"], "chuyển trường Tuấn Kiệt"),
        ("2D17 vắng Hải Long, Tuấn Kiệt chuyển trường", ["Hải Long"], "Tuấn Kiệt chuyển trường"),
        ("2D17: 30/31 vắng Hải Long. Từ mai bạn Tuấn Kiệt nghỉ ăn", ["Hải Long"], "Từ mai bạn Tuấn Kiệt nghỉ ăn"),
        ("2D17 vắng Hải Long. Phương Thanh thôi ăn từ thứ 2", ["Hải Long"], "Phương Thanh thôi ăn từ thứ 2"),
        ("2D17: bổ sung bán trú em Văn Mới", [], "bổ sung bán trú em Văn Mới"),
        # vẫn là báo vắng
        ("2D17 vắng thêm Hải Long", ["Hải Long"], ""),
        ("2D17 nghỉ: Hải Long, Tuấn Kiệt", ["Hải Long", "Tuấn Kiệt"], ""),
    ]
    for text, names, sched in cases:
        for pre in ("", "[29/10/2026 07:00:00] Cô Lan: "):
            m = parse_messages(pre + text, known)[0]
            assert (m.names, m.schedule) == (names, sched), (pre, text)
    m = parse_messages("2D17 đủ. Cắt bán trú Tuấn Kiệt từ thứ 2", known)[0]
    assert m.full and m.schedule == "Cắt bán trú Tuấn Kiệt từ thứ 2"


def test_not_boarding_name_is_warned_not_counted(ws):  # noqa: F811
    ws.load_day(dt.date(2026, 10, 29))
    ws.paste("1D15: 5/6 vắng Quỳnh Anh")  # Mạc Trần Quỳnh Anh có trong lớp nhưng không ăn bán trú
    st = ws.state
    assert st.absent_count("1D15") == 0 and not ws.pending_names()
    assert "Không ăn BT: Quỳnh Anh" in st.class_warnings("1D15")
    ws.paste("1D15 đủ")
    assert not any("Không ăn BT" in w for w in st.class_warnings("1D15"))
