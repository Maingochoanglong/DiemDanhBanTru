from app.core.search import matches


def test_match_without_accents_by_word_start():
    name = "Khổng Hải Long"
    for q in ("long", "hai long", "h long", "LONG", "  ", ""):
        assert matches(q, name), q
    assert not matches("ong", name)  # giữa chữ "Long": không khớp
    assert not matches("long hai x", name)
    assert matches("ong", "Ông Minh Thư")
    assert matches("ngoc", "Lý Thảo Ngọc  (nghỉ T6)")
