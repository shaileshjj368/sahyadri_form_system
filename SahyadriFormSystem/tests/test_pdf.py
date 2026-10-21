from pathlib import Path

import pytest
from pypdf import PdfReader

from src.pdf.renderer import PDFRenderer, A4_W, A4_H, _parts_date, _range_dates, _range_dates_with_note

BASE = Path(__file__).resolve().parents[1]


def test_pdf_template_is_one_page_a4():
    reader = PdfReader(str(BASE / 'templates' / 'Shri_Sahyadri.pdf'))
    assert len(reader.pages) == 1
    assert A4_W == pytest.approx(595.2756, abs=0.1)
    assert A4_H == pytest.approx(841.8898, abs=0.1)


def test_pdf_renderer_has_devanagari_font():
    renderer = PDFRenderer(BASE / 'templates' / 'Shri_Sahyadri.pdf', BASE / 'fonts' / 'NotoSansDevanagari-Regular.ttf')
    assert renderer.font_path.exists()


def test_date_parts_keep_template_separators():
    assert _parts_date('23/08/2026') == ('23', '08', '2026')
    assert _parts_date('1-2-2027') == ('01', '02', '2027')
    assert _parts_date('14/12/30') == ('14', '12', '2030')


def test_marriage_period_date_parts():
    assert _range_dates('01/01/2027 ते 31/12/2027') == (('01', '01', '2027'), ('31', '12', '2027'))


def test_marriage_period_keeps_optional_sentence():
    first, second, note = _range_dates_with_note('12/07/2029 12/12/2030 any sentence')
    assert first == ('12', '07', '2029')
    assert second == ('12', '12', '2030')
    assert note == 'any sentence'



def test_manglik_status_values_are_distinct():
    assert 'मंगळ' != 'मंगळ नाही'


def test_date_parts_keep_four_digit_year():
    assert _parts_date('26-05-2027') == ('26', '05', '2027')
