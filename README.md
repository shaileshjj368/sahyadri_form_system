# Sahyadri Form System v0.2.3

Windows desktop application for the Shri Sahyadri form: enter a record, save
it, and print it onto the original form as a PDF that looks filled in by hand.

**Setup and delivery steps: see [SETUP_AND_DELIVERY.md](SETUP_AND_DELIVERY.md).**

## What works offline and what needs internet

| Feature | Internet |
|---|---|
| Entering, saving, searching records (SQLite, `data\sahyadri.db`) | Not needed |
| Generating PDFs (`generated_pdfs\`) | Not needed |
| 🎤 Speech-to-text (Google, Marathi `mr-IN`) | **Needed** |
| **अ** English-to-Marathi conversion | Better online (Google Input Tools); simple offline fallback |

## PDF output

- Values are written in **Kalam**, an open-licence Devanagari handwriting font
  (SIL OFL, `fonts/Kalam-OFL.txt`), in ballpoint blue, at the same sizes as
  before.
- Positions come from `src/pdf/layout.py`, measured from the template: values
  sit on the ruled lines, the name and सूचना 6 hang from their printed lines,
  dates and लग्न are written between the printed `/` marks, and पत्रिकेतील दोष /
  उपाय / शारीरिक पात्रता / विवाह दिशा wrap from line to line.
- मंगळ: `M` right after the लग्न label, अंश raised at its top-right, कला
  smaller and a step higher, भाव at its foot.

## Settings (`settings.json`, created beside the app on first run)

| Key | Default | Meaning |
|---|---|---|
| `handwriting` | `true` | `false` = old printed (Noto Sans) look |
| `handwriting_weight` | `"regular"` | `"bold"` for a thicker, marker-like pen |
| `ink_color` | `"#1c3096"` | pen colour |
| `handwriting_wobble` | `true` | tiny natural per-word baseline variation |
| `speech_engine` | `"online"` | `"auto"` = online, offline model if no internet; `"offline"` |
| `speech_language` | `"mr-IN"` | Google language code |
| `google_cloud_api_key` | `""` | optional official Google Cloud Speech-to-Text key |

## Developer notes

- `python -m src.main` runs the app; `pytest` runs the tests.
- `python -m tools.preview_pdf` renders sample forms to `generated_pdfs\preview_*.pdf`
  (add `--pil` to use Pillow instead of Qt).
- The Qt renderer (app) and the Pillow renderer (preview) draw the same layout,
  so layout changes can be checked without the GUI.
