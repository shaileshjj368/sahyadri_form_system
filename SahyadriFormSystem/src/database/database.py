from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

# Keep the legacy `lagna` column for existing records, while the new
# manglik fields are stored separately so old SQLite databases remain usable.
FIELDS = [
    'sr_no','name','form_date','birth_date','birth_time','birth_place','rashi','nakshatra','janmnav','lagna',
    'manglik_status','manglik_house','manglik_degree','manglik_minute',
    'dasha','direction','patriketil_dosh','upay','varn','unchi','vajan','vayatila_farakh',
    'sharirik_yogyata','swabhav','shikshan','arthik_paristhiti','naukri_vyavasay','vivah_disha',
    'vivah_prakar','vaivahik_jeevan','vivah_yogya_kalavadhi','vivah_tarikh','notes'
]

class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        # Create the current schema if this is a new database.
        columns = ',\n'.join(f"{f} TEXT NOT NULL DEFAULT ''" for f in FIELDS)
        self.conn.execute(f"""CREATE TABLE IF NOT EXISTS forms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {columns},
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        # Migrate databases created by earlier v0.2.0 builds.
        existing = {row[1] for row in self.conn.execute('PRAGMA table_info(forms)').fetchall()}
        for field in ('manglik_status', 'manglik_house', 'manglik_degree', 'manglik_minute'):
            if field not in existing:
                self.conn.execute(f"ALTER TABLE forms ADD COLUMN {field} TEXT NOT NULL DEFAULT ''")
        self.conn.commit()

    def save(self, data: dict[str, Any], form_id: int | None = None) -> int:
        values = {f: str(data.get(f, '') or '') for f in FIELDS}
        # `lagna` is an independent user-entered field.  Manglik details are
        # stored separately and must never overwrite or clear the existing lagna value.
        if values['manglik_status'] != 'मंगळ':
            values['manglik_house'] = values['manglik_degree'] = values['manglik_minute'] = ''

        if form_id:
            sets = ', '.join(f'{f} = ?' for f in FIELDS)
            self.conn.execute(
                f"UPDATE forms SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                [values[f] for f in FIELDS] + [form_id]
            )
            self.conn.commit()
            return form_id
        cols = ', '.join(FIELDS)
        marks = ', '.join('?' for _ in FIELDS)
        cur = self.conn.execute(
            f"INSERT INTO forms ({cols}) VALUES ({marks})",
            [values[f] for f in FIELDS]
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def get(self, form_id: int) -> dict[str, Any] | None:
        row = self.conn.execute('SELECT * FROM forms WHERE id=?', (form_id,)).fetchone()
        return dict(row) if row else None

    def search(self, text: str = '', transliteration_fn=None) -> list[dict[str, Any]]:
        text = text.strip()
        if not text:
            rows = self.conn.execute('SELECT * FROM forms ORDER BY updated_at DESC, id DESC').fetchall()
        else:
            like = f'%{text}%'
            variants = [text]
            if transliteration_fn and not any('\u0900' <= ch <= '\u097f' for ch in text):
                try:
                    translated = transliteration_fn(text)
                    if translated and translated not in variants:
                        variants.append(translated)
                except Exception:
                    pass
            clauses = []
            params = []
            for variant in variants:
                vlike = f'%{variant}%'
                clauses.append('(sr_no LIKE ? OR name LIKE ? OR birth_place LIKE ? OR rashi LIKE ? OR nakshatra LIKE ?)')
                params.extend([vlike, vlike, vlike, vlike, vlike])
            rows = self.conn.execute(
                'SELECT * FROM forms WHERE ' + ' OR '.join(clauses) + ' ORDER BY updated_at DESC, id DESC', params
            ).fetchall()
        return [dict(r) for r in rows]

    def delete(self, form_id: int):
        self.conn.execute('DELETE FROM forms WHERE id=?', (form_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()
