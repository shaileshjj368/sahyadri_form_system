"""Render sample forms to PDF without the GUI.

    python -m tools.preview_pdf            # Qt text engine (same as the app)
    python -m tools.preview_pdf --pil      # Pillow text engine (no Qt needed)

Output goes to generated_pdfs/preview_*.pdf. Useful for checking the layout
after changing coordinates in src/pdf/layout.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pdf.renderer import PDFRenderer  # noqa: E402
from src.settings import Settings  # noqa: E402

SAMPLES = {
    # Transcribed from the client's handwritten reference forms.
    'rohan_manglik': {
        'sr_no': '62470', 'name': 'ब्रम्हक्षत्रीय रोहन', 'form_date': '21/08/2026',
        'birth_date': '27-02-1996', 'birth_time': '18:50', 'birth_place': 'नाशिक',
        'rashi': 'वृषभ', 'nakshatra': 'मृग-2', 'janmnav': 'वो', 'lagna': '5/6/-',
        'manglik_status': 'मंगळ', 'manglik_degree': '15', 'manglik_minute': '00', 'manglik_house': '7',
        'dasha': 'गुरु 18070434', 'direction': 'शु चं/-',
        'patriketil_dosh': '① विवाहस्थानी कुंभेला रवि-मंगळ राहूच्या नक्षत्री तर शनि अष्टमात शुक्रासह ग्रहणयोगात. ② कुटुंबस्थानी राहू. ③ नवमांशात विवाहाचा कारक गुरु चंद्र-प्लुटोसह कन्येला.',
        'upay': '① उजव्या तर्जनीत "पुष्कराज" रत्न तर अनामिकेत "प्रवाळ" (पोवळा) रत्न धारण करावे. ② लाल रंगांचा (Red Shades) वापर जास्त करावा. ③ बुधवार व शनिवार महत्वाचे निर्णय घेऊ नयेत. ④ हिरवा व काळ्या रंगांचा वापर करु नये.',
        'varn': 'निमगोरा वर्ण', 'unchi': '5\'3"', 'vajan': '64', 'vayatila_farakh': '4',
        'sharirik_yogyata': 'गोल चेहरा, मध्यम बांधा, करारी व्यक्तीमत्व',
        'swabhav': 'कमी व स्पष्ट बोलणारी, धार्मिक, हट्टी, हौशी', 'shikshan': 'पदवीधर',
        'arthik_paristhiti': 'व्यवस्थित', 'naukri_vyavasay': 'नोकरी.',
        'vivah_disha': '90% पश्चिम तर 10% पूर्व दिशेला जमण्याची शक्यता.',
        'vivah_prakar': '(परिचय असू शकेल)', 'vaivahik_jeevan': 'सुरुवातीला साधारण असेल.',
        'vivah_yogya_kalavadhi': '11/12/2026 04/06/2027 09-07-2029 ते दि. 15-06-2030',
        'vivah_tarikh': '26-05-2027 किंवा 24-12-2029',
        'notes': 'विवाहासाठी काळजी पूर्वक प्रयत्न करावे लागतील.',
    },
    'joshi_no_manglik': {
        'sr_no': '62283', 'name': 'जोशी शैलेश', 'form_date': '19/06/2026',
        'birth_date': '12/13-03-2002', 'birth_time': '00:25', 'birth_place': 'देवळाली प्रवरा',
        'rashi': 'कुंभ', 'nakshatra': 'शततारका-3', 'janmnav': 'सी', 'lagna': '8/9/-',
        'manglik_status': 'मंगळ नाही',
        'dasha': 'शनि 26010445', 'direction': 'शु/-',
        'patriketil_dosh': '① विवाहस्थानी वृषभेला शनि चांडाळयोगात तर शुक्र पंचमात क्षीण अवस्थेत. ② कुटुंबेश गुरु अष्टमात निर्बली. ③ साडेसाती व शनि महादशा. ④ नवमांशात विवाहाच्या कारक बुध तनुस्थानी धनेला व कुटुंबस्थानी मित्रस्थ गुरु.',
        'upay': '① उजव्या करंगळीत "मोती" रत्न धारण करावे.\n② लाल रंगाचा (Red Shades) वापर जास्त करावा.\n③ बुधवार व शनिवार महत्वाचे निर्णय घेवू नयेत.\n④ हिरवा व काळा रंग वापर करु नये.',
        'varn': 'निमगोरा वर्ण', 'unchi': '5\'4"', 'vajan': '56', 'vayatila_farakh': '2',
        'sharirik_yogyata': 'गोल चेहरा, मध्यम बांधा, सुंदर व्यक्तिमत्व',
        'swabhav': 'लहरी, हौशी, हट्टी, धार्मिक', 'shikshan': 'ग्रॅज्युएट',
        'arthik_paristhiti': 'व्यवस्थित', 'naukri_vyavasay': 'नोकरी.',
        'vivah_disha': '90% वायव्य दिशेला तर 10% पूर्व दिशेला जमण्याची शक्यता.',
        'vivah_prakar': '(परिचय असेल)', 'vaivahik_jeevan': 'सुरुवातीला साधारण असेल.',
        'vivah_yogya_kalavadhi': '18/11/2028 ते 08/07/2029 20-08-2030 ते दि. 16-07-2031',
        'vivah_tarikh': '06-05-2029 किंवा 24-12-2030',
        'notes': 'विवाहासाठी प्रयत्न करावे लागतील.',
    },
    # The client's own test record (45678) that showed the M problem.
    'client_test_manglik': {
        'sr_no': '45678', 'name': 'शैलेश जोशी', 'form_date': '28/09/2026',
        'rashi': 'कन्या', 'nakshatra': 'विशाखा', 'lagna': '8/5/-',
        'manglik_status': 'मंगळ', 'manglik_degree': '7', 'manglik_minute': '11', 'manglik_house': '4',
    },
    'aditi_manglik': {
        'sr_no': '62456', 'name': 'पोतदार आदिती', 'form_date': '19/08/2026',
        'birth_date': '16-02-2010', 'birth_time': '11:25', 'birth_place': 'लातूर',
        'rashi': 'कुंभ', 'nakshatra': 'पू. भाद्र-2', 'janmnav': 'सो', 'lagna': '1/8/मेष',
        'manglik_status': 'मंगळ', 'manglik_degree': '09', 'manglik_minute': '00', 'manglik_house': '4',
        'dasha': 'शनि 18230237', 'direction': '-/मं रा.',
    },
}


def main(argv: list[str]) -> int:
    backend = 'pil' if '--pil' in argv else 'qt'
    renderer = PDFRenderer(ROOT / 'templates' / 'Shri_Sahyadri.pdf', fonts_dir=ROOT / 'fonts',
                           settings=Settings())
    out_dir = ROOT / 'generated_pdfs'
    for name, data in SAMPLES.items():
        path = renderer.render(data, out_dir / f'preview_{name}.pdf', backend=backend)
        print('wrote', path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
