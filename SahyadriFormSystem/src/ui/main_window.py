from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QIntValidator
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem,
    QMessageBox, QScrollArea, QFrame, QComboBox
)

from src.database.database import Database
from src.transliteration.marathi import transliterate
from src.speech.manager import SpeechManager
from src.pdf.renderer import PDFRenderer
from src.settings import Settings

FIELD_LABELS = {
    'sr_no':'Sr.No.','name':'नाव','form_date':'Date','birth_date':'जन्म दिनांक','birth_time':'जन्म वेळ','birth_place':'जन्म स्थळ',
    'rashi':'जन्मराशी','nakshatra':'नक्षत्र','janmnav':'जन्मनाव','lagna':'लग्न','dasha':'दशा','direction':'दिशा',
    'patriketil_dosh':'पत्रिकेतील दोष','upay':'उपाय','varn':'वर्ण','unchi':'उंची','vajan':'वजन','vayatila_farakh':'वयातील फरक',
    'sharirik_yogyata':'शारीरिक पात्रता','swabhav':'स्वभाव','shikshan':'शिक्षण','arthik_paristhiti':'आर्थिक परिस्थिती',
    'naukri_vyavasay':'नोकरी / व्यवसाय','vivah_disha':'विवाह दिशा : जन्मस्थळापासून किंवा दिर्घ वास्तव्यापासून',
    'vivah_prakar':'विवाह प्रकार','vaivahik_jeevan':'वैवाहिक जीवन कसे असेल','vivah_yogya_kalavadhi':'विवाह योग्या कालावधी',
    'vivah_tarikh':'विवाह तारीख','notes':'नोंदी'
}

RASHI_OPTIONS = ['मेष','वृषभ','मिथुन','कर्क','सिंह','कन्या','तूळ','वृश्चिक','धनु','मकर','कुंभ','मीन']
NAKSHATRA_OPTIONS = ['अश्विनी','भरणी','कृत्तिका','रोहिणी','मृगशिरा','आर्द्रा','पुनर्वसु','पुष्य','आश्लेषा','पूर्वा फाल्गुनी','उत्तरा फाल्गुनी','हस्त','चित्रा','स्वाति','विशाखा','अनुराधा','ज्येष्ठा','मूल','पूर्वाषाढा','उत्तराषाढा','श्रवण','धनिष्ठा','शतभिषा','उत्तरा भाद्रपद','रेवती','पूर्वा भाद्रपद','मघा']

APP_STYLE = """
QMainWindow, QWidget { background: #ffffff; color: #202124; }
QLabel { color: #202124; font-size: 15px; }
QLineEdit, QTextEdit, QComboBox, QTableWidget { background: #ffffff; color: #202124; border: 1px solid #b9b9b9; border-radius: 6px; padding: 8px; font-size: 16px; }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 2px solid #4a78c2; }
QPushButton { background: #f5f5f5; color: #202124; border: 1px solid #b5b5b5; border-radius: 6px; padding: 9px 15px; font-size: 15px; min-height: 22px; }
QPushButton:hover { background: #eaeaea; }
QPushButton:pressed { background: #dddddd; }
QPushButton:disabled { color: #888888; background: #eeeeee; }
QHeaderView::section { background: #f1f3f4; color: #202124; padding: 9px; border: 1px solid #d0d0d0; font-size: 15px; font-weight: 600; }
QTableWidget { gridline-color: #dddddd; }
QTableWidget::item:selected { background: #dbe7f7; color: #202124; }
QScrollArea { background: #ffffff; border: none; }
QFrame { background: #ffffff; }
"""


class SpeechWorker(QThread):
    done = Signal(str, str)
    error = Signal(str)
    def __init__(self, manager):
        super().__init__(); self.manager = manager
    def run(self):
        try:
            text, mode = self.manager.recognize()
            self.done.emit(text, mode)
        except Exception as exc:
            self.error.emit(str(exc))


class FieldWidget(QFrame):
    def __init__(self, key, label, multiline=False, numeric=False):
        super().__init__(); self.key = key
        self.setFrameShape(QFrame.StyledPanel)
        lay = QVBoxLayout(self); lay.setContentsMargins(8, 7, 8, 8); lay.setSpacing(5)
        top = QHBoxLayout(); lbl = QLabel(label); lbl.setStyleSheet('font-weight:600; font-size:16px;'); top.addWidget(lbl); top.addStretch()
        self.trans_btn = QPushButton('अ'); self.trans_btn.setToolTip('English phonetic text → Marathi')
        self.speech_btn = QPushButton('🎤'); self.speech_btn.setToolTip('Speak Marathi into this field')
        self.trans_btn.setFixedWidth(42); self.speech_btn.setFixedWidth(48)
        top.addWidget(self.trans_btn); top.addWidget(self.speech_btn); lay.addLayout(top)
        self.editor = QTextEdit() if multiline else QLineEdit()
        if multiline: self.editor.setMinimumHeight(84)
        else: self.editor.setMinimumHeight(40)
        if numeric:
            self.editor.setValidator(QIntValidator(0, 360, self.editor))
        self.editor.setFont(QFont('Noto Sans Devanagari', 14)); lay.addWidget(self.editor)
        self.trans_btn.clicked.connect(self._transliterate)

    def _transliterate(self):
        before = self.text()
        if not before.strip():
            QMessageBox.information(self, 'Marathi conversion', 'Please enter English phonetic text first.')
            return
        try:
            after = transliterate(before, prefer_online=True)
            self.setText(after)
            QMessageBox.information(self, 'Success', 'Text converted to Marathi successfully.')
        except Exception as exc:
            QMessageBox.critical(self, 'Marathi conversion error', str(exc))

    def text(self):
        return self.editor.text() if isinstance(self.editor, QLineEdit) else self.editor.toPlainText()
    def setText(self, text):
        if isinstance(self.editor, QLineEdit): self.editor.setText(text or '')
        else: self.editor.setPlainText(text or '')
    def set_speech_handler(self, fn):
        self.speech_btn.clicked.connect(lambda: fn(self.key, self))


class ChoiceFieldWidget(QFrame):
    def __init__(self, key, label, options):
        super().__init__(); self.key = key; self.options = options
        self.setFrameShape(QFrame.StyledPanel)
        lay = QVBoxLayout(self); lay.setContentsMargins(8, 7, 8, 8); lay.setSpacing(5)
        top = QHBoxLayout(); lbl = QLabel(label); lbl.setStyleSheet('font-weight:600; font-size:16px;'); top.addWidget(lbl); top.addStretch()
        self.speech_btn = QPushButton('🎤'); self.speech_btn.setFixedWidth(48); self.speech_btn.setToolTip('Speak the Marathi option')
        top.addWidget(self.speech_btn); lay.addLayout(top)
        self.editor = QComboBox(); self.editor.addItem('')
        self.editor.addItems(options); self.editor.setMinimumHeight(42); self.editor.setFont(QFont('Noto Sans Devanagari', 14)); lay.addWidget(self.editor)

    def text(self): return self.editor.currentText().strip()
    def setText(self, text):
        text = str(text or '').strip()
        idx = self.editor.findText(text, Qt.MatchExactly)
        self.editor.setCurrentIndex(idx if idx >= 0 else 0)
    def set_speech_handler(self, fn):
        self.speech_btn.clicked.connect(lambda: fn(self.key, self))
    def accept_speech(self, text: str):
        t = transliterate(text, prefer_online=False).strip()
        idx = self.editor.findText(t, Qt.MatchExactly)
        if idx < 0:
            # Speech engines may add punctuation; compare normalized text.
            norm = ''.join(ch for ch in t if not ch.isspace())
            for i in range(1, self.editor.count()):
                candidate = ''.join(ch for ch in self.editor.itemText(i) if not ch.isspace())
                if candidate == norm:
                    idx = i; break
        if idx < 0:
            import difflib
            norm = ''.join(ch for ch in t if not ch.isspace() and ch not in '.,!?।')
            options = [''.join(ch for ch in self.editor.itemText(i) if not ch.isspace()) for i in range(1, self.editor.count())]
            prefix = [i for i, o in enumerate(options) if norm and (o.startswith(norm) or norm.startswith(o))]
            close = difflib.get_close_matches(norm, options, n=1, cutoff=0.6)
            if len(prefix) == 1: idx = prefix[0] + 1
            elif close: idx = options.index(close[0]) + 1
        if idx >= 0: self.editor.setCurrentIndex(idx); return True
        return False


class ManglikPanel(QFrame):
    def __init__(self, app):
        super().__init__(); self.app = app; self.setFrameShape(QFrame.StyledPanel)
        lay = QVBoxLayout(self); lay.setContentsMargins(8, 7, 8, 8); lay.setSpacing(5)
        title = QLabel('मंगळ'); title.setStyleSheet('font-weight:600; font-size:16px;'); lay.addWidget(title)
        row = QHBoxLayout()
        self.status = QComboBox(); self.status.addItems(['', 'मंगळ', 'मंगळ नाही']); self.status.setMinimumHeight(42); self.status.setFont(QFont('Noto Sans Devanagari', 14)); row.addWidget(self.status, 1)
        self.status.currentTextChanged.connect(self._toggle)
        lay.addLayout(row)
        self.details = QWidget(); d = QGridLayout(self.details); d.setContentsMargins(0, 0, 0, 0); d.setHorizontalSpacing(5)
        self.degree = self._numeric('मंगळ अंश (0-29)', 0, 29); self.minute = self._numeric('मंगळ कला (0-59)', 0, 59); self.house = self._numeric('मंगळ भाव (1-12)', 1, 12)
        d.addWidget(self.degree[0], 0, 0); d.addWidget(self.minute[0], 0, 1); d.addWidget(self.house[0], 0, 2)
        lay.addWidget(self.details)
        self._toggle(self.status.currentText())

    def _numeric(self, label, lo=0, hi=360):
        # अंश = degree within the rashi (0-29), कला = minutes (0-59), भाव = house (1-12).
        w = QLineEdit(); w.setPlaceholderText(label); w.setMinimumHeight(40); w.setFont(QFont('Noto Sans Devanagari', 14)); w.setValidator(QIntValidator(lo, hi, w))
        return w, label
    def _toggle(self, value): self.details.setVisible(value == 'मंगळ')
    def data(self):
        status = self.status.currentText()
        return {'manglik_status': status, 'manglik_house': self.house[0].text().strip() if status == 'मंगळ' else '', 'manglik_degree': self.degree[0].text().strip() if status == 'मंगळ' else '', 'manglik_minute': self.minute[0].text().strip() if status == 'मंगळ' else ''}
    def load(self, data):
        status = data.get('manglik_status','')
        if not status and data.get('lagna'):
            status = 'मंगळ' if ('मं' in str(data.get('lagna')) or 'M' in str(data.get('lagna')).upper()) else ''
            if status == 'मंगळ':
                parts = [x.strip() for x in str(data.get('lagna')).replace('मं','').replace('M','').split('/')]
                for w, val in zip((self.degree[0], self.minute[0], self.house[0]), parts[:3]): w.setText(val)
        self.status.setCurrentText(status if status in ('मंगळ','मंगळ नाही') else '')
        self._toggle(self.status.currentText())
        self.house[0].setText(str(data.get('manglik_house','') or '')); self.degree[0].setText(str(data.get('manglik_degree','') or '')); self.minute[0].setText(str(data.get('manglik_minute','') or ''))
    def setFocus(self): self.status.setFocus()


class FormPage(QWidget):
    saved = Signal()
    def __init__(self, app):
        super().__init__(); self.app = app; self.form_id = None; self.fields = {}
        root = QVBoxLayout(self); root.setSpacing(10)
        header = QHBoxLayout(); title = QLabel('श्री Sahyadri — Digital Form'); title.setStyleSheet('font-size:28px;font-weight:700;')
        header.addWidget(title); header.addStretch()
        self.new_btn = QPushButton('Clear / New'); self.save_btn = QPushButton('Save Form'); self.pdf_btn = QPushButton('Generate PDF'); self.back_btn = QPushButton('Back to Dashboard')
        for b in (self.new_btn, self.save_btn, self.pdf_btn, self.back_btn): b.setMinimumHeight(44)
        header.addWidget(self.new_btn); header.addWidget(self.save_btn); header.addWidget(self.pdf_btn); header.addWidget(self.back_btn); root.addLayout(header)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        container = QWidget(); grid = QGridLayout(container); grid.setColumnStretch(0,1); grid.setColumnStretch(1,1); grid.setHorizontalSpacing(10); grid.setVerticalSpacing(10)
        keys = ['sr_no','name','form_date','birth_date','birth_time','birth_place','rashi','nakshatra','janmnav','lagna','dasha','direction','patriketil_dosh','upay','varn','unchi','vajan','vayatila_farakh','sharirik_yogyata','swabhav','shikshan','arthik_paristhiti','naukri_vyavasay','vivah_disha','vivah_prakar','vaivahik_jeevan','vivah_yogya_kalavadhi','vivah_tarikh','notes']
        multiline = {'patriketil_dosh','upay','sharirik_yogyata','vivah_disha','notes'}
        for i, key in enumerate(keys):
            if key == 'rashi': fw = ChoiceFieldWidget(key, FIELD_LABELS[key], RASHI_OPTIONS)
            elif key == 'nakshatra': fw = ChoiceFieldWidget(key, FIELD_LABELS[key], NAKSHATRA_OPTIONS)
            else: fw = FieldWidget(key, FIELD_LABELS[key], key in multiline)
            fw.set_speech_handler(self.app.start_speech); self.fields[key] = fw; grid.addWidget(fw, i//2, i%2)
            if key == 'vivah_yogya_kalavadhi':
                fw.editor.setPlaceholderText('उदा. 12/07/2029 12/12/2030 अतिरिक्त वाक्य')
                fw.editor.setToolTip('पहिल्या दोन तारखा पूर्ण वर्षासह द्या. दुसऱ्या तारखेनंतरचे अतिरिक्त वाक्य PDF मध्ये पुढील ओळीवर छापले जाईल.')
        manglik_row = (len(keys) + 1) // 2
        self.manglik = ManglikPanel(self.app); grid.addWidget(self.manglik, manglik_row, 0, 1, 2)
        scroll.setWidget(container); root.addWidget(scroll)
        self.new_btn.clicked.connect(self.clear_form); self.save_btn.clicked.connect(self.save_form); self.pdf_btn.clicked.connect(self.generate_pdf); self.back_btn.clicked.connect(lambda: self.app.show_dashboard())

    def data(self):
        data = {k: w.text() for k,w in self.fields.items()}; data.update(self.manglik.data()); return data
    def load(self, data):
        self.form_id = data.get('id')
        for k,w in self.fields.items(): w.setText(data.get(k,''))
        self.manglik.load(data)
    def clear_form(self):
        self.form_id = None
        for w in self.fields.values(): w.setText('')
        self.manglik.load({})
        self.fields['form_date'].setText(datetime.now().strftime('%d/%m/%Y')); self.fields['sr_no'].editor.setFocus(); QMessageBox.information(self,'New form','A new blank form is ready.')
    def validate(self):
        data = self.data()
        if not data['name'].strip(): QMessageBox.warning(self,'Required field','Please enter the name before saving.'); return None
        if data['manglik_status'] == 'मंगळ' and not (data['manglik_degree'].strip() and data['manglik_house'].strip()):
            QMessageBox.warning(self,'Required field','For मंगळ, please enter मंगळ अंश and मंगळ भाव. मंगळ कला is optional.'); return None
        return data
    def save_form(self):
        data=self.validate()
        if data is None:return
        try:
            self.form_id=self.app.db.save(data,self.form_id); QMessageBox.information(self,'Success',f'Form saved successfully.\n\nRecord ID: {self.form_id}'); self.saved.emit(); self.app.show_dashboard()
        except Exception as exc: QMessageBox.critical(self,'Save error',f'Form could not be saved.\n\n{exc}')
    def generate_pdf(self):
        data=self.validate()
        if data is None:return
        try:
            self.form_id=self.app.db.save(data,self.form_id); pdf=self.app.generate_pdf(data,self.form_id); self.app.open_file(pdf); QMessageBox.information(self,'Success',f'PDF generated successfully.\n\n{pdf}')
        except Exception as exc: QMessageBox.critical(self,'PDF generation error',f'PDF could not be generated.\n\n{exc}')


class DashboardPage(QWidget):
    def __init__(self, app):
        super().__init__(); self.app=app; root=QVBoxLayout(self); root.setSpacing(12)
        top=QHBoxLayout(); title=QLabel('Sahyadri Form Dashboard'); title.setStyleSheet('font-size:30px;font-weight:700;'); top.addWidget(title); top.addStretch(); new=QPushButton('+ New Form'); new.setMinimumHeight(44); new.clicked.connect(self.new_form); top.addWidget(new); root.addLayout(top)
        searchrow=QHBoxLayout(); self.search=QLineEdit(); self.search.setPlaceholderText('Search English or Marathi: Ramesh / रमेश / Sr.No. / Birth Place...'); self.search.setMinimumHeight(44); btn=QPushButton('Search'); btn.setMinimumHeight(44); btn.clicked.connect(self.refresh); self.search.returnPressed.connect(self.refresh); searchrow.addWidget(self.search); searchrow.addWidget(btn); root.addLayout(searchrow)
        self.table=QTableWidget(0,5); self.table.setHorizontalHeaderLabels(['ID','Sr.No.','Name','Birth Place','Updated']); self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.setFont(QFont('Noto Sans Devanagari',14)); self.table.doubleClicked.connect(self.edit_selected); root.addWidget(self.table)
        actions=QHBoxLayout(); edit=QPushButton('Edit Selected'); edit.clicked.connect(self.edit_selected); view=QPushButton('View PDF'); view.clicked.connect(self.view_selected); delete=QPushButton('Delete'); delete.clicked.connect(self.delete_selected); [b.setMinimumHeight(44) for b in (edit,view,delete)]; actions.addWidget(edit); actions.addWidget(view); actions.addWidget(delete); actions.addStretch(); root.addLayout(actions)
    def refresh(self):
        try:
            rows=self.app.db.search(self.search.text(),transliteration_fn=lambda s: transliterate(s,prefer_online=True)); self.table.setRowCount(len(rows))
            for r,row in enumerate(rows):
                vals=[row['id'],row['sr_no'],row['name'],row['birth_place'],row['updated_at']]
                for c,v in enumerate(vals): self.table.setItem(r,c,QTableWidgetItem(str(v)))
            self.table.resizeColumnsToContents(); self.app.statusBar().showMessage(f'{len(rows)} record(s) found.')
        except Exception as exc: QMessageBox.critical(self,'Search error',str(exc))
    def selected_id(self):
        r=self.table.currentRow(); return int(self.table.item(r,0).text()) if r>=0 else None
    def new_form(self): self.app.show_form(None)
    def edit_selected(self):
        i=self.selected_id(); self.app.show_form(i) if i else QMessageBox.information(self,'Edit','Please select a record first.')
    def view_selected(self):
        i=self.selected_id()
        if not i: QMessageBox.information(self,'View PDF','Please select a record first.'); return
        try:
            row=self.app.db.get(i); pdf=self.app.generate_pdf(row,i); self.app.open_file(pdf); QMessageBox.information(self,'Success',f'PDF opened successfully.\n\n{pdf}')
        except Exception as exc: QMessageBox.critical(self,'PDF error',str(exc))
    def delete_selected(self):
        i=self.selected_id()
        if not i: QMessageBox.information(self,'Delete','Please select a record first.'); return
        if QMessageBox.question(self,'Delete','Delete this form?')==QMessageBox.Yes:
            try: self.app.db.delete(i); self.refresh(); QMessageBox.information(self,'Success','Form deleted successfully.')
            except Exception as exc: QMessageBox.critical(self,'Delete error',str(exc))


class MainWindow(QMainWindow):
    def __init__(self, base_dir: Path, resource_dir: Path | None = None):
        super().__init__(); self.base_dir=base_dir; self.resource_dir=resource_dir or base_dir; self.setWindowTitle('Shri Sahyadri Form System'); self.resize(1440,960); self.setMinimumSize(1100,760); self.setStyleSheet(APP_STYLE)
        # settings.json lives beside the app (created with defaults on first run).
        self.settings=Settings.load(base_dir/'settings.json')
        self.db=Database(base_dir/'data'/'sahyadri.db'); fonts=self.resource_dir/'fonts'
        self.renderer=PDFRenderer(self.resource_dir/'templates'/'Shri_Sahyadri.pdf',fonts/'NotoSansDevanagari-Regular.ttf',fonts/'NotoSansDevanagari-Bold.ttf',fonts_dir=fonts,settings=self.settings)
        # Speech: online Google recognition by default. An offline model is used only if
        # settings.json says "auto"/"offline" and the optional model folder is installed.
        model_candidates=[self.resource_dir/'models'/'whisper-small', self.resource_dir/'models'/'whisper-medium', self.resource_dir/'models'/'whisper-base', base_dir/'models'/'whisper-small', base_dir/'models'/'whisper-base']
        model_path=next((p for p in model_candidates if p.exists()), None)
        self.speech=SpeechManager(settings=self.settings, model_path=str(model_path) if model_path else None)
        self.stack=QStackedWidget(); self.dashboard=DashboardPage(self); self.form=FormPage(self); self.stack.addWidget(self.dashboard); self.stack.addWidget(self.form); self.setCentralWidget(self.stack); self.statusBar().showMessage(f'Ready — records and PDFs are saved on this computer; speech uses {self.speech.engine_label}.'); self.show_dashboard()
    def show_dashboard(self): self.dashboard.refresh(); self.stack.setCurrentWidget(self.dashboard)
    def show_form(self, form_id):
        if form_id:
            data=self.db.get(form_id)
            if not data: QMessageBox.warning(self,'Load error','The selected form no longer exists.'); return
            self.form.load(data)
        else: self.form.clear_form()
        self.stack.setCurrentWidget(self.form)
    def start_speech(self,key,widget):
        widget.speech_btn.setEnabled(False); widget.speech_btn.setText('...'); self.statusBar().showMessage('Listening… speak now in Marathi.'); worker=SpeechWorker(self.speech); self._speech_worker=worker
        worker.done.connect(lambda text,mode:self._speech_done(widget,text,mode)); worker.error.connect(lambda msg:self._speech_error(widget,msg)); worker.finished.connect(lambda:(widget.speech_btn.setEnabled(True),widget.speech_btn.setText('🎤'))); worker.start()
    def _speech_done(self,widget,text,mode):
        if isinstance(widget,ChoiceFieldWidget):
            if widget.accept_speech(text): QMessageBox.information(self,'Speech-to-text',f'Marathi speech recognized successfully ({mode}).')
            else: QMessageBox.warning(self,'Speech-to-text',f'Recognized text "{text}" does not match an available option.')
        elif text:
            widget.setText((widget.text().rstrip()+' '+text).strip()); self.statusBar().showMessage(f'Speech converted ({mode}): {text}'); QMessageBox.information(self,'Speech-to-text',f'Marathi speech converted successfully ({mode}).')
        else: QMessageBox.warning(self,'Speech-to-text','No speech was recognized.')
    def _speech_error(self,widget,msg): self.statusBar().showMessage('Speech-to-text failed.'); QMessageBox.critical(self,'Speech-to-text error',msg)
    def generate_pdf(self,data,form_id):
        name=(data.get('name') or 'form').strip().replace('/','-').replace('\\','-')[:40]; path=self.base_dir/'generated_pdfs'/f'{data.get("sr_no") or form_id}_{name}.pdf'; result=self.renderer.render(data,path)
        if not result.exists() or result.stat().st_size<1000: raise RuntimeError('PDF renderer returned without creating a valid PDF file.')
        return result
    def open_file(self,path):
        try:
            if sys.platform.startswith('win'): os.startfile(str(path))
            elif sys.platform=='darwin': os.system(f'open "{path}"')
            else: os.system(f'xdg-open "{path}" >/dev/null 2>&1')
        except Exception as exc: raise RuntimeError(f'Could not open PDF: {exc}') from exc
