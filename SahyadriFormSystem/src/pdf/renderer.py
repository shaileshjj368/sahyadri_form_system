"""Fill the Shri Sahyadri template and write a one-page A4 PDF.

Positions come from `layout.py` (shared, backend-independent). This module
only draws those positions:

* backend 'qt'  – production. Uses Qt's text engine (HarfBuzz shaping), so
                  Marathi conjuncts render correctly on every Windows PC.
* backend 'pil' – preview / automated tests without Qt. Uses Pillow + libraqm
                  (also HarfBuzz) and draws exactly the same layout.

The filled text is rendered at 300 dpi into a transparent overlay that is
placed over the untouched original vector template.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pypdf import PdfReader, PdfWriter, PageObject, Transformation
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

from src.settings import Settings
from .layout import (  # re-exported for callers/tests
    FALLBACK, HAND, TextOp, layout_form,
    _normalise_year, _parts_date, _parts_date_with_printed_20,
    _range_dates, _range_dates_with_note,
)

SOURCE_W, SOURCE_H = 594.0, 936.0
A4_W, A4_H = A4
PX_PER_PT = 300.0 / 72.0          # overlay resolution: 300 dpi

FORM_SCALE = min(A4_W / SOURCE_W, A4_H / SOURCE_H)
FORM_XOFF = (A4_W - SOURCE_W * FORM_SCALE) / 2.0
FORM_YOFF = (A4_H - SOURCE_H * FORM_SCALE) / 2.0


class PDFRenderer:
    """Render the original form on A4 and overlay the entered data."""

    def __init__(self, template_path: str | Path,
                 font_path: str | Path | None = None,
                 bold_font_path: str | Path | None = None,
                 fonts_dir: str | Path | None = None,
                 settings: Settings | None = None):
        self.template_path = Path(template_path)
        self.font_path = Path(font_path) if font_path else None
        self.bold_font_path = Path(bold_font_path) if bold_font_path else None
        if fonts_dir:
            self.fonts_dir = Path(fonts_dir)
        elif self.font_path:
            self.fonts_dir = self.font_path.parent
        else:
            self.fonts_dir = self.template_path.parent.parent / 'fonts'
        self.settings = settings or Settings()

    # ------------------------------------------------------------------ fonts
    def font_files(self) -> dict[str, Path]:
        """Font file for each role, following the settings."""
        d = self.fonts_dir
        kalam = d / ('Kalam-Bold.ttf' if self.settings.handwriting_weight == 'bold' else 'Kalam-Regular.ttf')
        noto_regular = self.font_path or d / 'NotoSansDevanagari-Regular.ttf'
        noto_bold = self.bold_font_path or d / 'NotoSansDevanagari-Bold.ttf'
        if self.settings.handwriting and kalam.exists():
            return {HAND: kalam, FALLBACK: noto_regular}
        return {HAND: noto_bold if noto_bold.exists() else noto_regular, FALLBACK: noto_regular}

    # ----------------------------------------------------------------- render
    def render(self, data: dict, output_path: str | Path, backend: str = 'qt') -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        reader = PdfReader(str(self.template_path))
        src = reader.pages[0]
        bg = PageObject.create_blank_page(width=A4_W, height=A4_H)
        src.add_transformation(Transformation().scale(FORM_SCALE).translate(FORM_XOFF, FORM_YOFF))
        bg.merge_page(src)

        overlay_png = output_path.with_suffix('.overlay.png')
        overlay_pdf = output_path.with_suffix('.overlay.pdf')
        try:
            self.render_overlay(data, overlay_png, backend=backend)
            c = canvas.Canvas(str(overlay_pdf), pagesize=A4)
            c.drawImage(ImageReader(str(overlay_png)), 0, 0, width=A4_W, height=A4_H,
                        preserveAspectRatio=False, mask='auto')
            c.save()
            bg.merge_page(PdfReader(str(overlay_pdf)).pages[0])
            writer = PdfWriter()
            writer.add_page(bg)
            with output_path.open('wb') as f:
                writer.write(f)
        finally:
            overlay_png.unlink(missing_ok=True)
            overlay_pdf.unlink(missing_ok=True)
        return output_path

    def render_overlay(self, data: dict, png_path: str | Path, backend: str = 'qt') -> list[TextOp]:
        if backend == 'pil':
            return _render_overlay_pil(self, data, Path(png_path))
        return _render_overlay_qt(self, data, Path(png_path))


# ============================================================================
# Qt backend (production)
# ============================================================================
_QT_FAMILIES: dict[str, str] = {}   # font file -> Qt family name


def _render_overlay_qt(renderer: PDFRenderer, data: dict, png_path: Path) -> list[TextOp]:
    from PySide6.QtCore import Qt, QPointF
    from PySide6.QtGui import (QColor, QFont, QFontDatabase, QFontMetricsF,
                               QGuiApplication, QImage, QPainter)

    app = QGuiApplication.instance()
    owns_app = False
    if app is None:
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        app = QGuiApplication([])
        owns_app = True

    try:
        families: dict[str, str] = {}
        bold: dict[str, bool] = {}
        for role, path in renderer.font_files().items():
            family = ''
            if path and Path(path).exists():
                key = str(Path(path).resolve())
                if key not in _QT_FAMILIES:          # register each font file once
                    font_id = QFontDatabase.addApplicationFont(key)
                    fams = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
                    _QT_FAMILIES[key] = fams[0] if fams else ''
                family = _QT_FAMILIES[key]
            families[role] = family
            bold[role] = Path(path).stem.lower().endswith('bold') if path else False
        if not families.get(HAND):
            for candidate in ('Nirmala UI', 'Mangal'):
                if candidate in QFontDatabase.families():
                    families[HAND] = candidate
                    break
            else:
                raise RuntimeError('A Devanagari font could not be loaded for PDF generation.')

        k = FORM_SCALE * PX_PER_PT              # pixels per template point
        ox, oy = FORM_XOFF * PX_PER_PT, FORM_YOFF * PX_PER_PT
        width, height = int(round(A4_W * PX_PER_PT)), int(round(A4_H * PX_PER_PT))
        image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        # With the image at 300 dpi, a font of P points is exactly P*300/72 px.
        dpm = int(round(72.0 * PX_PER_PT / 0.0254))
        image.setDotsPerMeterX(dpm)
        image.setDotsPerMeterY(dpm)

        def base_font(role: str) -> QFont:
            f = QFont(families.get(role) or families[HAND])
            f.setBold(bold.get(role, False))
            f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            f.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
            return f

        # Self-check: a P-point font on this 300-dpi image must be P*300/72 px.
        # Compare against an explicit pixel-size font; if the platform reports
        # a different resolution, correct every size so text and positions
        # stay exactly where the layout put them.
        probe_pt, probe_px = base_font(HAND), base_font(HAND)
        probe_pt.setPointSizeF(100.0 * FORM_SCALE)
        probe_px.setPixelSize(int(round(100.0 * k)))
        adv_pt = QFontMetricsF(probe_pt, image).horizontalAdvance('0000')
        adv_px = QFontMetricsF(probe_px, image).horizontalAdvance('0000')
        size_fix = (adv_px / adv_pt) if adv_pt > 0 and abs(adv_px / adv_pt - 1.0) > 0.02 else 1.0

        @lru_cache(maxsize=None)
        def qfont(role: str, size: float) -> QFont:
            f = base_font(role)
            f.setPointSizeF(size * FORM_SCALE * size_fix)   # template pt -> A4 pt
            return f

        @lru_cache(maxsize=None)
        def metrics(role: str, size: float) -> QFontMetricsF:
            return QFontMetricsF(qfont(role, size), image)

        class QtMeasurer:
            def measure(self, text: str, size: float, font: str = HAND) -> float:
                return metrics(font, round(size, 3)).horizontalAdvance(text) / k

            def has_glyph(self, ch: str, font: str = HAND) -> bool:
                return metrics(font, 12.0).inFontUcs4(ord(ch))

        ops = layout_form(data, QtMeasurer(), jitter=renderer.settings.handwriting_wobble)

        painter = QPainter(image)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            painter.setPen(QColor(*renderer.settings.ink_rgb()))
            for op in ops:
                painter.setFont(qfont(op.font, round(op.size, 3)))
                painter.drawText(QPointF(ox + op.x * k, oy + op.baseline * k), op.text)
        finally:
            painter.end()
        if not image.save(str(png_path), 'PNG'):
            raise RuntimeError(f'Could not write PDF text overlay: {png_path}')
        return ops
    finally:
        if owns_app:
            app.quit()


# ============================================================================
# Pillow backend (preview / tests)
# ============================================================================
def _render_overlay_pil(renderer: PDFRenderer, data: dict, png_path: Path) -> list[TextOp]:
    from PIL import Image, ImageDraw, ImageFont, features

    if not features.check('raqm'):
        raise RuntimeError('Pillow was built without libraqm; Marathi text cannot be shaped.')
    files = renderer.font_files()
    fallback_candidates = [Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'), files[FALLBACK]]
    fallback = next((p for p in fallback_candidates if p.exists()), files[FALLBACK])
    paths = {HAND: Path(files[HAND]), FALLBACK: fallback}

    k = FORM_SCALE * PX_PER_PT
    ox, oy = FORM_XOFF * PX_PER_PT, FORM_YOFF * PX_PER_PT

    @lru_cache(maxsize=None)
    def pfont(role: str, size: float):
        return ImageFont.truetype(str(paths[role]), size=size * k, layout_engine=ImageFont.Layout.RAQM)

    @lru_cache(maxsize=None)
    def cmap(role: str):
        try:
            from fontTools.ttLib import TTFont
            return set(TTFont(str(paths[role])).getBestCmap())
        except Exception:
            return None

    class PilMeasurer:
        def measure(self, text: str, size: float, font: str = HAND) -> float:
            return pfont(font, round(size, 3)).getlength(text) / k

        def has_glyph(self, ch: str, font: str = HAND) -> bool:
            cm = cmap(font)
            return True if cm is None else ord(ch) in cm

    ops = layout_form(data, PilMeasurer(), jitter=renderer.settings.handwriting_wobble)
    image = Image.new('RGBA', (int(round(A4_W * PX_PER_PT)), int(round(A4_H * PX_PER_PT))), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    colour = renderer.settings.ink_rgb() + (255,)
    for op in ops:
        draw.text((ox + op.x * k, oy + op.baseline * k), op.text,
                  font=pfont(op.font, round(op.size, 3)), fill=colour, anchor='ls')
    image.save(str(png_path), 'PNG')
    return ops
