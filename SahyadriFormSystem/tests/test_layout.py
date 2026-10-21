"""Layout tests. Most use a fake measurer, so they run anywhere (no Qt, no fonts).

The Qt tests at the bottom run on the Windows build machine (they are skipped
where PySide6 is not installed). They check that Qt's font measurements match
the layout's units — the class of bug that once put the मंगळ degree in the
wrong place.
"""
from pathlib import Path

import pytest

from src.pdf import layout as L
from src.pdf.layout import layout_form, prefer_half_forms

BASE = Path(__file__).resolve().parents[1]


class FakeMeasurer:
    """Every glyph is half an em wide; the handwriting font lacks ①."""

    def measure(self, text, size, font=L.HAND):
        return len(text) * 0.5 * size

    def has_glyph(self, ch, font=L.HAND):
        return ch != '①'


def ops_for(data, **kw):
    return layout_form(data, FakeMeasurer(), jitter=kw.get('jitter', False))


def find(ops, text):
    return [op for op in ops if op.text == text]


MANGLIK = {'lagna': '8/5/-', 'manglik_status': 'मंगळ',
           'manglik_degree': '15', 'manglik_minute': '00', 'manglik_house': '7'}


def test_manglik_notation_positions():
    ops = ops_for(MANGLIK)
    (m,) = find(ops, 'M')
    (deg,) = find(ops, '15')
    (mins,) = find(ops, '00')
    (house,) = find(ops, '7')
    cap_top = m.baseline - L.CAP_M * m.size
    # M sits right after the printed "लग्न" label, inside its yellow cell.
    assert 74.25 < m.x < 85
    # अंश: right of the M and raised so it straddles the M's top.
    assert deg.x > m.x + 0.7 * m.size
    assert deg.baseline < m.baseline - 0.8 * (m.baseline - cap_top)
    assert deg.baseline - L.DIGIT * deg.size < cap_top
    # कला: smaller and a step higher than the अंश.
    assert mins.size < deg.size
    assert mins.baseline < deg.baseline
    assert mins.x > deg.x
    # भाव: at the M's foot, below the M baseline.
    assert house.baseline > m.baseline
    assert house.baseline - L.DIGIT * house.size < m.baseline
    # Everything stays within the लग्न row (small overshoot upward like handwriting).
    for op in (m, deg, mins, house):
        assert L.ROW_LAGNA[0] - 2.0 < op.baseline - L.DIGIT * op.size
        assert op.baseline < L.ROW_LAGNA[1]


def test_no_manglik_draws_no_m():
    ops = ops_for({'lagna': '8/9/-', 'manglik_status': 'मंगळ नाही',
                   'manglik_degree': '15', 'manglik_house': '7'})
    assert not find(ops, 'M')
    assert not find(ops, '15')


def test_lagna_parts_sit_between_printed_slashes():
    ops = ops_for({'lagna': '8/5/-'})
    (p1,) = find(ops, '8')
    (p2,) = find(ops, '5')
    (p3,) = find(ops, '—')           # a lone "-" is written as a pen dash
    fm = FakeMeasurer()
    assert p1.x + fm.measure('8', p1.size) <= L.LAGNA_SLASH1[0]
    assert L.LAGNA_SLASH1[1] <= p2.x and p2.x + fm.measure('5', p2.size) <= L.LAGNA_SLASH2[0]
    assert p3.x >= L.LAGNA_SLASH2[1]
    assert not any('/' in op.text for op in ops)   # the template prints the slashes


def test_lagna_with_four_parts_keeps_alignment():
    ops = ops_for({'lagna': '8/9/1/-'})
    assert find(ops, '8') and find(ops, '9') and find(ops, '1/-')


def test_values_sit_inside_their_rows():
    data = {'rashi': 'कुंभ', 'dasha': 'शनि 26010445', 'varn': 'निमगोरा वर्ण',
            'vivah_tarikh': '06-05-2029 किंवा 24-12-2030'}
    ops = ops_for(data)
    rows = {'कुंभ': L.ROW_RASHI, 'शनि': L.ROW_LAGNA, 'निमगोरा': L.ROW_1, '06-05-2029': L.ROW_14}
    for text, (top, bottom) in rows.items():
        (op,) = find(ops, text)
        assert top + L.HEADLINE * op.size < op.baseline < bottom - 0.3 * op.size


def test_name_hangs_from_the_printed_line():
    (op,) = find(ops_for({'name': 'जोशी'}), 'जोशी')
    headline_top = op.baseline - L.HEADLINE * op.size
    assert L.NAME_LINE_Y < headline_top < L.NAME_LINE_Y + 1.0


def test_top_date_year_follows_printed_20():
    ops = ops_for({'form_date': '19/06/2026'})
    (year,) = find(ops, '26')
    assert year.x == pytest.approx(L.DATE_YEAR_X)
    assert find(ops, '19') and find(ops, '06')


def test_long_dosh_wraps_across_rows_and_first_row_follows_label():
    text = ' '.join(['शब्द'] * 60)
    ops = ops_for({'patriketil_dosh': text})
    rows_used = sorted({round(op.baseline) for op in ops})
    assert len(rows_used) >= 3
    first = min(ops, key=lambda op: (op.baseline, op.x))
    assert first.x == pytest.approx(L.DOSH_LINES[0][0])
    fm = FakeMeasurer()
    for op in ops:
        assert op.x + fm.measure(op.text, op.size) <= L.SECTION_X_END + 0.01


def test_typed_line_breaks_start_new_rows():
    ops = ops_for({'upay': 'पहिला\nदुसरा\nतिसरा'})
    lines = [find(ops, w)[0] for w in ('पहिला', 'दुसरा', 'तिसरा')]
    assert lines[0].baseline < lines[1].baseline < lines[2].baseline
    assert lines[1].x == pytest.approx(L.UPAY_LINES[1][0])


def test_overflowing_single_line_is_shrunk_to_fit():
    # About twice what fits at the normal size (the realistic worst case).
    long = 'अ' * 100
    (op,) = find(ops_for({'shikshan': long}), long)
    x, x_end = L.SIMPLE_FIELDS['shikshan'][:2]
    assert op.x + FakeMeasurer().measure(long, op.size) <= x_end + 0.01


def test_symbols_missing_from_handwriting_font_use_fallback():
    ops = ops_for({'upay': '① मोती'})
    (circled,) = find(ops, '①')
    assert circled.font == L.FALLBACK
    assert find(ops, 'मोती')[0].font == L.HAND


def test_half_forms_for_unusual_kalam_conjuncts():
    assert '‍' in prefer_half_forms('रत्न')
    assert '‍' in prefer_half_forms('लग्न')
    assert prefer_half_forms('कुंभ') == 'कुंभ'


def test_wobble_is_deterministic():
    data = {'swabhav': 'लहरी, हौशी, हट्टी, धार्मिक'}
    assert ops_for(data, jitter=True) == ops_for(data, jitter=True)


# ---------------------------------------------------------------- real fonts
def _pil_ready():
    try:
        from PIL import features
        return features.check('raqm')
    except Exception:
        return False


@pytest.mark.skipif(not _pil_ready(), reason='Pillow without libraqm')
def test_pil_backend_renders_pdf(tmp_path):
    from pypdf import PdfReader
    from src.pdf.renderer import PDFRenderer
    r = PDFRenderer(BASE / 'templates' / 'Shri_Sahyadri.pdf', fonts_dir=BASE / 'fonts')
    out = r.render({'name': 'जोशी शैलेश', **MANGLIK}, tmp_path / 'f.pdf', backend='pil')
    assert out.stat().st_size > 1000
    assert len(PdfReader(str(out)).pages) == 1


def _qt_ready():
    try:
        import PySide6  # noqa: F401
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _qt_ready(), reason='PySide6 not installed')
def test_qt_measurements_match_layout_units(tmp_path):
    """Kalam's 'M' is 0.789 em wide. If Qt's measurement in template points
    disagrees, sizes and positions would drift (the old मंगळ bug)."""
    from src.pdf.renderer import PDFRenderer
    r = PDFRenderer(BASE / 'templates' / 'Shri_Sahyadri.pdf', fonts_dir=BASE / 'fonts')
    ops = r.render_overlay({'name': 'जोशी', **MANGLIK}, tmp_path / 'o.png', backend='qt')
    (m,) = find(ops, 'M')
    (deg,) = find(ops, '15')
    gap = deg.x - m.x                         # = M advance + 0.5 pt
    assert gap == pytest.approx(L.M_ADVANCE * m.size + 0.5, rel=0.06)


@pytest.mark.skipif(not (_qt_ready() and _pil_ready()), reason='needs PySide6 and raqm')
def test_qt_and_pil_layouts_agree(tmp_path):
    from src.pdf.renderer import PDFRenderer
    from tools.preview_pdf import SAMPLES
    r = PDFRenderer(BASE / 'templates' / 'Shri_Sahyadri.pdf', fonts_dir=BASE / 'fonts')
    # Symbols such as ① come from each engine's own fallback font (different
    # widths by design), so compare text the handwriting font draws itself.
    data = {k: v.translate({ord(c): None for c in '①②③④'}) for k, v in SAMPLES['rohan_manglik'].items()}
    qt = r.render_overlay(data, tmp_path / 'q.png', backend='qt')
    pil = r.render_overlay(data, tmp_path / 'p.png', backend='pil')
    assert [op.text for op in qt] == [op.text for op in pil]
    for a, b in zip(qt, pil):
        assert abs(a.x - b.x) < 1.5 and abs(a.baseline - b.baseline) < 0.2


@pytest.mark.skipif(not _qt_ready(), reason='PySide6 not installed')
def test_qt_backend_renders_pdf(tmp_path):
    from pypdf import PdfReader
    from src.pdf.renderer import PDFRenderer
    r = PDFRenderer(BASE / 'templates' / 'Shri_Sahyadri.pdf', fonts_dir=BASE / 'fonts')
    out = r.render({'name': 'जोशी शैलेश', **MANGLIK}, tmp_path / 'f.pdf', backend='qt')
    assert out.stat().st_size > 1000
    assert len(PdfReader(str(out)).pages) == 1
