"""Handwriting-style layout for the Shri Sahyadri form.

All geometry is in TEMPLATE points, measured from the top-left of the original
594 x 936 pt source page (`templates/Shri_Sahyadri.pdf`). Every ruled line,
label cell and printed separator used below was measured from a 288-dpi
raster of that template (see docs/field_map.md).

This module is deliberately backend-independent. It only needs a *measurer*
object with two methods:

    measure(text, size, font) -> advance width in template points
    has_glyph(ch, font)       -> True if the font has a glyph for ch

and returns a flat list of `TextOp`s (text, x, baseline, size, font). The
production renderer (Qt) and the preview/test renderer (Pillow) both draw
exactly these ops, so what is verified in the preview is the same layout the
application prints.

Placement rules (chosen to look like the handwritten reference forms):

* Values sit ON the row's bottom rule like pen writing, rather than being
  vertically centred in a box.
* Where the template prints a writing line at headline height (नाव, सूचना 6)
  the Marathi text hangs from that line, the way Devanagari is written.
* Values around printed separators ("/", "/20", "दि. / /") are split into
  parts and written between the separators.
* मंगळ is written as in the client's forms: a handwritten "M" right after the
  लग्न label, the अंश (degree) as a small raised number at the top-right of
  the M, the कला (minutes) smaller and a step higher, and the भाव (house) as a
  small number at the M's foot.
* A tiny deterministic per-word baseline wobble gives the line a natural pen
  feel; the same input always produces the same PDF.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Protocol

# --------------------------------------------------------------------------
# Font roles and metrics
# --------------------------------------------------------------------------
HAND = 'hand'          # handwriting font (Kalam)
FALLBACK = 'fallback'  # used only for characters the handwriting font lacks

# Kalam metrics as fractions of the em size (measured from Kalam-Regular.ttf).
HEADLINE = 0.645       # top of the Devanagari headline (शिरोरेषा) above baseline
DIGIT = 0.727          # height of 0-9 above baseline
CAP_M = 0.718          # height of "M" above baseline
M_ADVANCE = 0.789      # advance width of "M"

JITTER_PT = 0.28       # max per-word baseline wobble (template pt)


@dataclass(frozen=True)
class TextOp:
    text: str
    x: float           # left edge of the text's advance box (template pt)
    baseline: float    # baseline y (template pt, from top of page)
    size: float        # font em size (template pt)
    font: str = HAND


class Measurer(Protocol):
    def measure(self, text: str, size: float, font: str = HAND) -> float: ...
    def has_glyph(self, ch: str, font: str = HAND) -> bool: ...


# --------------------------------------------------------------------------
# Template geometry (template pt)
# --------------------------------------------------------------------------
# Header box
SR_BOX = (95.5, 193.5, 166.25, 221.0)          # x0, top, x1, bottom (inside border)
NAME_LINE_Y = 201.07                            # printed writing line after "नाव :"
NAME_X, NAME_X_END = 206.0, 434.0
DATE_BASELINE = 208.2                           # printed "Date :  /  /20" baseline 207.95
DATE_DAY_CENTER, DATE_MONTH_CENTER, DATE_YEAR_X = 480.6, 507.6, 534.4

# Top three rows: label cells 54-106 | value 106.5-228 | label 228-280 |
# value 280.5-402 | label 402-454 | value 454.5-567.75
ROW_BIRTH = (227.75, 247.75)
ROW_RASHI = (247.75, 268.0)
ROW_LAGNA = (268.0, 288.0)

# लग्न: label "लग्न" ends at 74.25; its yellow cell ends at 106.25.
# Printed slashes: 128.75-133.5 and 152.5-157.25.
LAGNA_M_X = 78.3
LAGNA_SLASH1 = (128.75, 133.5)
LAGNA_SLASH2 = (152.5, 157.25)
LAGNA_VALUE_X0, LAGNA_VALUE_X1 = 107.5, 226.0
LAGNA_SLASH_GAP = 3.4           # pen gap each side of a printed slash

# पत्रिकेतील दोष: four writing rows; label ends at 123.75.
DOSH_LINES = [(127.5, 296.0, 318.5), (62.0, 318.5, 341.5),
              (62.0, 341.5, 364.5), (62.0, 364.5, 385.5)]
# उपाय: four writing rows; label ends at 91.25.
UPAY_LINES = [(95.5, 385.5, 410.75), (62.0, 410.75, 433.75),
              (62.0, 433.75, 456.75), (62.0, 456.75, 479.75)]
SECTION_X_END = 564.0

# भावी जीवनसाथीचे वर्णन table (value column 208-567.75)
ROW_1 = (499.88, 520.25)        # वर्ण | ऊंची (label ends 444)
ROW_2 = (520.25, 540.25)        # वजन ... "Kgs" at 357.25 | वयातील फरक (479-504) वर्षे
ROW_5 = [(540.25, 559.0), (559.0, 577.5)]
ROW_6 = (577.5, 602.0)
ROW_7 = (602.0, 627.0)
ROW_8 = (627.0, 651.88)
ROW_9 = (651.88, 672.0)
ROW_10 = [(672.0, 692.0), (692.0, 712.25)]
ROW_11 = (712.25, 732.25)       # printed "ठरवून" 216.5-238.25
ROW_12 = (732.25, 752.25)
ROW_13 = (752.25, 772.5)        # दि. __/__/____ ते दि. __/__/____ या काळात...
ROW_13_NOTE = (772.5, 792.5)
ROW_14 = (792.5, 813.25)        # "(जन्मवेळ अचुक असल्यास)" starts 482.75
TABLE_X_END = 565.0

# Row 13 printed separators: slashes 246.5-252 | 272-277.5 | 385.5-391 | 411-416.5
PERIOD_DAY1_C, PERIOD_MONTH1_C, PERIOD_YEAR1_X = 238.75, 262.5, 279.3
PERIOD_DAY2_C, PERIOD_MONTH2_C, PERIOD_YEAR2_X = 376.0, 400.8, 418.3

NOTES_LINE_Y = 865.5            # सूचना "6)" writing line
NOTES_X, NOTES_X_END = 99.0, 490.0

# Single-line fields: key -> (x, x_end, (top, bottom), size, align)
# x positions are the ones the client already approved; align "center" uses
# x as the centre point and x_end as the half-width limit.
SIMPLE_FIELDS = {
    'birth_date':        (151.65, 44.0, ROW_BIRTH, 11.2, 'center'),
    'birth_time':        (319.5, 38.0, ROW_BIRTH, 11.2, 'center'),
    'birth_place':       (462.5, 566.0, ROW_BIRTH, 11.2, 'left'),
    'rashi':             (114.7, 226.0, ROW_RASHI, 13.2, 'left'),
    'nakshatra':         (289.8, 400.0, ROW_RASHI, 13.2, 'left'),
    'janmnav':           (463.5, 566.0, ROW_RASHI, 13.2, 'left'),
    'dasha':             (293.2, 400.0, ROW_LAGNA, 13.2, 'left'),
    'direction':         (465.9, 566.0, ROW_LAGNA, 13.2, 'left'),
    'varn':              (218.3, 384.0, ROW_1, 13.2, 'left'),
    'unchi':             (449.0, 566.0, ROW_1, 12.0, 'left'),
    'vajan':             (352.6, 212.0, ROW_2, 12.0, 'right'),   # ends a space before "Kgs"
    'vayatila_farakh':   (491.5, 11.5, ROW_2, 12.0, 'center'),  # between फरक and वर्षे
    'swabhav':           (223.1, TABLE_X_END, ROW_6, 13.2, 'left'),
    'shikshan':          (229.8, TABLE_X_END, ROW_7, 13.2, 'left'),
    'arthik_paristhiti': (218.3, TABLE_X_END, ROW_8, 13.2, 'left'),
    'naukri_vyavasay':   (228.4, TABLE_X_END, ROW_9, 13.2, 'left'),
    'vivah_prakar':      (263.4, TABLE_X_END, ROW_11, 13.2, 'left'),
    'vaivahik_jeevan':   (219.3, TABLE_X_END, ROW_12, 13.2, 'left'),
    'vivah_tarikh':      (226.0, 480.0, ROW_14, 13.2, 'left'),
}

# Multi-line fields: key -> (list of (x_start, top, bottom), x_end, size)
WRAPPED_FIELDS = {
    'patriketil_dosh':  (DOSH_LINES, SECTION_X_END, 12.5),
    'upay':             (UPAY_LINES, SECTION_X_END, 12.5),
    'sharirik_yogyata': ([(224.0,) + ROW_5[0], (224.0,) + ROW_5[1]], TABLE_X_END, 12.5),
    'vivah_disha':      ([(228.0,) + ROW_10[0], (228.0,) + ROW_10[1]], TABLE_X_END, 12.5),
}

VALUE_SIZES = {
    'name': 14.0, 'sr_no': 11.5, 'form_date': 11.2, 'lagna': 12.5,
    'period_date': 10.8, 'period_note': 12.5, 'notes': 13.2,
}

# मंगळ notation sizes (template pt). The M matches the handwritten M height
# (~8.3 pt cap height); the numbers keep the proportions of the client's forms.
MANGLIK_M_SIZE = 11.5
MANGLIK_DEGREE_SIZE = 7.0
MANGLIK_MINUTE_SIZE = 5.6
MANGLIK_HOUSE_SIZE = 7.0

MIN_SIZE = 6.0            # smallest size a too-long value is shrunk to (fits ~2x the space)


# --------------------------------------------------------------------------
# Date helpers (kept here so every backend shares them)
# --------------------------------------------------------------------------
_DEVA_DIGITS = '०१२३४५६७८९'


def _is_deva_number(s: str) -> bool:
    return bool(s) and all(ch in _DEVA_DIGITS for ch in s)


def _pad2(s: str) -> str:
    s = str(s or '')
    if len(s) >= 2:
        return s[-2:]
    return ('०' if _is_deva_number(s) else '0') + s if s else ''


def _normalise_year(year: str) -> str:
    """Always return a four-digit display year for the user-entered date."""
    year = str(year or '').strip()
    if len(year) == 2:
        return ('२०' if _is_deva_number(year) else '20') + year
    if len(year) == 4:
        return year
    return year.zfill(4) if year else ''


def _parts_date(value: str) -> tuple[str, str, str]:
    """Return day, month and a four-digit year for dd/mm/yyyy-like input."""
    nums = re.findall(r'\d{1,4}', value or '')
    if len(nums) >= 3:
        d, m, y = nums[0], nums[1], nums[2]
        return _pad2(d), _pad2(m), _normalise_year(y)
    return '', '', ''


def _parts_date_with_printed_20(value: str) -> tuple[str, str, str]:
    """Day, month and only the last two year digits (the form prints '/20')."""
    d, m, y = _parts_date(value)
    return d, m, y[-2:] if len(y) == 4 else y


def _range_dates_with_note(value: str):
    """Two dates plus any trailing sentence from the marriage-period field.

    Accepts e.g. "12/07/2029 12/12/2030", "12/07/2029 ते 12/12/2030 any text".
    """
    text = str(value or '').strip()
    pattern = re.compile(r'(\d{1,2})\s*[/.-]\s*(\d{1,2})\s*[/.-]\s*(\d{2,4})')
    matches = list(pattern.finditer(text))
    if len(matches) >= 2:
        def norm(match):
            d, m, y = match.groups()
            return _pad2(d), _pad2(m), _normalise_year(y)
        note = text[matches[1].end():].strip()
        note = re.sub(r'^(?:ते|to|TO|[-,:;])\s*', '', note).strip()
        return norm(matches[0]), norm(matches[1]), note
    return ('', '', ''), ('', '', ''), text


def _range_dates(value: str):
    first, second, _ = _range_dates_with_note(value)
    return first, second


# --------------------------------------------------------------------------
# Placement primitives
# --------------------------------------------------------------------------
def row_baseline(top: float, bottom: float, size: float) -> float:
    """Baseline for pen writing sitting on a row's bottom rule.

    Leaves room below for descending matras (ु ू ृ ्) and keeps the body a
    touch below the row's centre, like the handwritten forms.
    """
    height = bottom - top
    return min(bottom - 0.36 * size, top + (height + HEADLINE * size) / 2 + 0.06 * height)


def hang_baseline(line_y: float, size: float) -> float:
    """Baseline for Devanagari hanging from a printed writing line."""
    return line_y + 0.35 + HEADLINE * size


_ZWJ = '\u200d'
# Kalam draws these conjuncts as stacked ligatures that Marathi readers are not
# used to (रत्न looks like "रन्न"). A zero-width joiner asks for the usual
# half-letter form instead: रत्न, प्रयत्न, लग्न, स्नान.
_HALF_FORM_PAIRS = ('त्न', 'ग्न', 'स्न')


def prefer_half_forms(text: str) -> str:
    for pair in _HALF_FORM_PAIRS:
        text = text.replace(pair, pair[:2] + _ZWJ + pair[2:])
    return text


def _jitter(*parts) -> float:
    digest = hashlib.md5('|'.join(str(p) for p in parts).encode('utf-8')).digest()
    return (digest[0] / 255.0 * 2.0 - 1.0) * JITTER_PT


class Layout:
    """Builds the list of TextOps for one form."""

    def __init__(self, measurer: Measurer, jitter: bool = True):
        self.m = measurer
        self.jitter = jitter
        self.ops: list[TextOp] = []

    # ---- low-level ---------------------------------------------------------
    def width(self, text: str, size: float) -> float:
        return sum(self.m.measure(run, size, font) for font, run in self._runs(text))

    def _runs(self, text: str):
        """Split text into runs the handwriting font can draw and runs that
        need the fallback font (e.g. ① or other symbols)."""
        runs: list[list] = []
        for ch in text:
            font = HAND if (ch.isspace() or ch in '\u200c\u200d'
                            or self.m.has_glyph(ch, HAND)) else FALLBACK
            if runs and runs[-1][0] == font:
                runs[-1][1] += ch
            else:
                runs.append([font, ch])
        return [(f, t) for f, t in runs]

    def fit(self, text: str, size: float, max_width: float) -> float:
        if max_width <= 0:
            return size
        w = self.width(text, size)
        if w <= max_width:
            return size
        s = max(MIN_SIZE, size * max_width / w)
        while s > MIN_SIZE and self.width(text, s) > max_width:
            s -= 0.1
        return s

    def emit(self, key: str, text: str, x: float, baseline: float, size: float,
             line_no: int = 0) -> float:
        """Emit text word by word (with a subtle baseline wobble); return end x."""
        words = text.split(' ')
        space = self.m.measure(' ', size, HAND)
        cx = x
        for i, word in enumerate(words):
            if word:
                dy = _jitter(key, line_no, i, word) if self.jitter else 0.0
                for font, run in self._runs(word):
                    self.ops.append(TextOp(run, cx, baseline + dy, size, font))
                    cx += self.m.measure(run, size, font)
            if i < len(words) - 1:
                cx += space
        return cx

    # ---- field kinds -------------------------------------------------------
    def simple(self, key: str, text: str, x: float, x_end: float, row, size: float,
               align: str = 'left'):
        text = ' '.join(str(text or '').split())
        if not text:
            return
        top, bottom = row
        if align == 'center':
            half = x_end
            s = self.fit(text, size, 2 * half)
            w = self.width(text, s)
            start = x - w / 2
        elif align == 'right':
            s = self.fit(text, size, x - x_end)
            start = x - self.width(text, s)
        else:
            s = self.fit(text, size, x_end - x)
            start = x
        self.emit(key, text, start, row_baseline(top, bottom, s), s)

    def centered_at(self, key: str, text: str, cx: float, baseline: float, size: float,
                    max_width: float):
        text = str(text or '').strip()
        if not text:
            return
        s = self.fit(text, size, max_width)
        self.emit(key, text, cx - self.width(text, s) / 2, baseline, s)

    def wrapped(self, key: str, text: str, lines, x_end: float, size: float,
                min_size: float = 9.0):
        text = str(text or '').strip()
        if not text:
            return
        paragraphs = [' '.join(p.split()) for p in text.splitlines() if p.strip()]
        s = size
        placed = self._wrap(paragraphs, lines, x_end, s)
        while placed is None and s > min_size:
            s = round(s - 0.25, 2)
            placed = self._wrap(paragraphs, lines, x_end, s)
        if placed is None:
            placed = self._wrap(paragraphs, lines, x_end, s, force=True)
        for i, line_text in enumerate(placed):
            if not line_text:
                continue
            x, top, bottom = lines[i]
            ls = self.fit(line_text, s, x_end - x)
            self.emit(key, line_text, x, row_baseline(top, bottom, ls), ls, line_no=i)

    def _wrap(self, paragraphs, lines, x_end, size, force=False):
        """Greedy word wrap over the writing rows. Each typed paragraph (line
        break) starts on a new row. Returns None if the text does not fit,
        unless `force`, in which case the overflow goes onto the last row
        (which is then shrunk to fit by the caller)."""
        n = len(lines)
        out = [''] * n
        widths = [0.0] * n
        space = self.m.measure(' ', size, HAND)
        li = -1
        for para in paragraphs:
            li += 1
            if li >= n:
                if not force:
                    return None
                li = n - 1
            for word in para.split(' '):
                ww = self.width(word, size)
                cap = x_end - lines[li][0]
                if not out[li]:
                    if ww > cap and not force:
                        return None
                    out[li], widths[li] = word, ww
                elif widths[li] + space + ww <= cap:
                    out[li] += ' ' + word
                    widths[li] += space + ww
                elif li + 1 < n:
                    li += 1
                    if ww > x_end - lines[li][0] and not force:
                        return None
                    out[li], widths[li] = word, ww
                else:
                    if not force:
                        return None
                    out[li] += ' ' + word
                    widths[li] += space + ww
        return out

    # ---- special fields ----------------------------------------------------
    def sr_no(self, text: str):
        text = str(text or '').strip()
        if not text:
            return
        x0, top, x1, bottom = SR_BOX
        s = self.fit(text, VALUE_SIZES['sr_no'], x1 - x0 - 4)
        baseline = (top + bottom) / 2 + DIGIT * s / 2
        self.emit('sr_no', text, (x0 + x1) / 2 - self.width(text, s) / 2, baseline, s)

    def name(self, text: str):
        text = ' '.join(str(text or '').split())
        if not text:
            return
        s = self.fit(text, VALUE_SIZES['name'], NAME_X_END - NAME_X)
        self.emit('name', text, NAME_X, hang_baseline(NAME_LINE_Y, s), s)

    def notes(self, text: str):
        text = ' '.join(str(text or '').split())
        if not text:
            return
        s = self.fit(text, VALUE_SIZES['notes'], NOTES_X_END - NOTES_X)
        self.emit('notes', text, NOTES_X, hang_baseline(NOTES_LINE_Y, s), s)

    def form_date(self, value: str):
        d, m, y = _parts_date_with_printed_20(value)
        s = VALUE_SIZES['form_date']
        self.centered_at('form_date_d', d, DATE_DAY_CENTER, DATE_BASELINE, s, 24.0)
        self.centered_at('form_date_m', m, DATE_MONTH_CENTER, DATE_BASELINE, s, 24.0)
        if y:
            ys = self.fit(y, s, 30.0)
            self.emit('form_date_y', y, DATE_YEAR_X, DATE_BASELINE, ys)

    def lagna(self, value: str, manglik: dict | None):
        top, bottom = ROW_LAGNA
        size = VALUE_SIZES['lagna']
        baseline = row_baseline(top, bottom, size)
        if manglik:
            self.manglik(baseline, **manglik)
        value = ' '.join(str(value or '').split())
        if not value:
            return
        parts = [p.strip() for p in value.split('/')]
        if len(parts) < 2:
            # Free text (no slashes): write it in the value cell.
            s = self.fit(value, size, LAGNA_VALUE_X1 - LAGNA_VALUE_X0)
            self.emit('lagna', value, LAGNA_VALUE_X0 + 1.0, row_baseline(top, bottom, s), s)
            return
        if len(parts) > 3:
            parts = parts[:2] + ['/'.join(parts[2:])]
        while len(parts) < 3:
            parts.append('')
        parts = ['—' if p in ('-', '--', '–') else p for p in parts]
        p1, p2, p3 = parts
        # Part 1 ends a pen-gap before the first printed slash, part 2 is centred
        # between the slashes and part 3 starts a pen-gap after the second —
        # evenly spaced like the handwritten "8 / 9 / —".
        if p1:
            right = LAGNA_SLASH1[0] - LAGNA_SLASH_GAP
            s = self.fit(p1, size, right - LAGNA_VALUE_X0)
            self.emit('lagna1', p1, right - self.width(p1, s), row_baseline(top, bottom, s), s)
        if p2:
            gap = LAGNA_SLASH2[0] - LAGNA_SLASH1[1]
            cx = (LAGNA_SLASH1[1] + LAGNA_SLASH2[0]) / 2
            s = self.fit(p2, size, gap - 1.0)
            self.emit('lagna2', p2, cx - self.width(p2, s) / 2, row_baseline(top, bottom, s), s)
        if p3:
            left = LAGNA_SLASH2[1] + LAGNA_SLASH_GAP
            s = self.fit(p3, size, LAGNA_VALUE_X1 - left)
            self.emit('lagna3', p3, left, row_baseline(top, bottom, s), s)

    def manglik(self, lagna_baseline: float, degree: str = '', minute: str = '', house: str = ''):
        """M with अंश raised at its top-right, कला smaller and a step higher,
        and भाव at its foot — proportions taken from the handwritten forms."""
        degree, minute, house = (str(v or '').strip() for v in (degree, minute, house))
        if not (degree or minute or house):
            return
        sm = MANGLIK_M_SIZE
        cap = CAP_M * sm
        yb = lagna_baseline
        x_m = LAGNA_M_X
        self.ops.append(TextOp('M', x_m, yb, sm, HAND))
        x_num = x_m + M_ADVANCE * sm + 0.5
        # अंश: its baseline sits just under the top of the M, so the number
        # straddles the M's top-right corner.
        sd = MANGLIK_DEGREE_SIZE
        y_deg = yb - 0.95 * cap
        if degree:
            self.ops.append(TextOp(degree, x_num, y_deg, sd, HAND))
        # कला: smaller, stepping up from the top of the अंश.
        if minute:
            smin = MANGLIK_MINUTE_SIZE
            x_min = x_num + (self.width(degree, sd) + 0.4 if degree else 0.0)
            y_min = y_deg - DIGIT * sd + 0.9
            self.ops.append(TextOp(minute, x_min, y_min, smin, HAND))
        # भाव: at the M's foot, straddling its baseline.
        if house:
            self.ops.append(TextOp(house, x_num - 0.3, yb + 0.25 * cap, MANGLIK_HOUSE_SIZE, HAND))

    def marriage_period(self, value: str):
        (d1, m1, y1), (d2, m2, y2), note = _range_dates_with_note(value)
        top, bottom = ROW_13
        s = VALUE_SIZES['period_date']
        base = row_baseline(top, bottom, s)
        self.centered_at('p_d1', d1, PERIOD_DAY1_C, base, s, 19.0)
        self.centered_at('p_m1', m1, PERIOD_MONTH1_C, base, s, 19.0)
        if y1:
            self.emit('p_y1', y1, PERIOD_YEAR1_X, base, self.fit(y1, s, 48.0))
        self.centered_at('p_d2', d2, PERIOD_DAY2_C, base, s, 18.0)
        self.centered_at('p_m2', m2, PERIOD_MONTH2_C, base, s, 18.0)
        if y2:
            self.emit('p_y2', y2, PERIOD_YEAR2_X, base, self.fit(y2, s, 52.0))
        if note:
            self.simple('period_note', note, 232.0, TABLE_X_END, ROW_13_NOTE,
                        VALUE_SIZES['period_note'])


def layout_form(data: dict, measurer: Measurer, jitter: bool = True) -> list[TextOp]:
    """Return every text operation needed to fill the form for `data`."""
    lay = Layout(measurer, jitter=jitter)

    def get(key: str) -> str:
        return prefer_half_forms(str(data.get(key, '') or '').strip())

    lay.sr_no(get('sr_no'))
    lay.name(get('name'))
    lay.form_date(get('form_date'))

    manglik = None
    if get('manglik_status') == 'मंगळ':
        manglik = {'degree': get('manglik_degree'), 'minute': get('manglik_minute'),
                   'house': get('manglik_house')}
    lay.lagna(get('lagna'), manglik)

    for key, (x, x_end, row, size, align) in SIMPLE_FIELDS.items():
        lay.simple(key, get(key), x, x_end, row, size, align)
    for key, (lines, x_end, size) in WRAPPED_FIELDS.items():
        lay.wrapped(key, get(key), lines, x_end, size)

    lay.marriage_period(get('vivah_yogya_kalavadhi'))
    lay.notes(get('notes'))
    return lay.ops
