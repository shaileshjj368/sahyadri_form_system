"""Marathi phonetic transliteration.

Online: Google Input Tools Marathi transliteration endpoint (no API key).
Offline: local fallback dictionary/phonetic converter.

This is transliteration ("kumbh" -> "कुंभ"), not semantic translation.

Design note (v0.2.2 fix): the whole input string is walked token by token —
Devanagari runs, punctuation/digits/whitespace, and Latin words are each
classified separately, and every Latin word is converted independently.
This fixes two bugs from the previous version:

1. A single Google Input Tools call returns one "chunk" per word, and the
   previous code only ever read the FIRST chunk (`chunks[0]`), so anything
   after the first comma/full stop (which starts a new chunk) was silently
   dropped instead of converted.
2. The previous code bailed out of transliteration for the ENTIRE string the
   moment any Devanagari character appeared anywhere in it, so a sentence
   that already had one Marathi word at the start never had the rest of the
   sentence converted at all.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

GOOGLE_INPUT_URL = "https://inputtools.google.com/request"

# Common Marathi words/terms where generic phonetic rules can be ambiguous.
COMMON = {
    "kumbh": "कुंभ", "ramesh": "रमेश", "patil": "पाटील", "suresh": "सुरेश",
    "mahesh": "महेश", "janm": "जन्म", "janma": "जन्म", "sthal": "स्थळ",
    "naam": "नाव", "nav": "नाव", "rashi": "राशी", "nakshatra": "नक्षत्र",
    "lagna": "लग्न", "dasha": "दशा", "vivah": "विवाह", "tarikh": "तारीख",
    "shikshan": "शिक्षण", "naukri": "नोकरी", "vyavasay": "व्यवसाय",
}

# Segments text into: Devanagari runs | Latin word runs | everything else
# (punctuation, digits, whitespace). Each segment is handled on its own, so a
# Devanagari word never gets sent to the transliteration API, and punctuation
# never stops the rest of the string from being converted.
_TOKEN_RE = re.compile(r"[ऀ-ॿ]+|[A-Za-z]+|[^ऀ-ॿA-Za-z]+")


def _has_devanagari(text: str) -> bool:
    return any("ऀ" <= ch <= "ॿ" for ch in text)


def _is_latin_word(token: str) -> bool:
    return bool(token) and token.isascii() and token.isalpha()


def google_transliterate(word: str, timeout: float = 1.5) -> str | None:
    """Transliterate a SINGLE Latin word using Google's public Input Tools
    endpoint when internet is available. Returns None on any failure so the
    caller can fall back to the offline converter without hanging the UI.
    """
    if not word or not _is_latin_word(word):
        return None
    params = {
        "text": word,
        "itc": "mr-t-i0-und",
        "num": "1",
        "cp": "0",
        "cs": "1",
        "ie": "utf-8",
        "oe": "utf-8",
        "app": "demopage",
    }
    url = GOOGLE_INPUT_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "SahyadriFormSystem/0.2"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        # Expected: ["SUCCESS", [[input, [suggestions...], ...]]]
        if payload and payload[0] == "SUCCESS":
            chunks = payload[1]
            if chunks and chunks[0][1]:
                return chunks[0][1][0]
    except Exception:
        return None
    return None


def transliterate(text: str, prefer_online: bool = True) -> str:
    """Convert every Latin (English-phonetic) word in ``text`` to Marathi,
    leaving Devanagari words, punctuation, digits and whitespace untouched,
    and processing the FULL string regardless of commas or full stops.
    """
    text = text if text is not None else ""
    if not text.strip():
        return text

    online_available = prefer_online
    out: list[str] = []
    for token in _TOKEN_RE.findall(text):
        if not token:
            continue
        if not _is_latin_word(token):
            # Devanagari text, punctuation, digits, whitespace: keep as-is.
            out.append(token)
            continue
        result = None
        if online_available:
            result = google_transliterate(token)
            if result is None:
                # Network unavailable or the endpoint failed: don't keep
                # retrying (and timing out) for every remaining word in this
                # same call — switch to the offline converter for the rest.
                online_available = False
        if result is None:
            result = _fallback(token)
        out.append(result)
    return "".join(out)


def _fallback(word: str) -> str:
    lw = word.lower()
    if lw in COMMON:
        return COMMON[lw]
    return _phonetic_word(lw)


def _phonetic_word(word: str) -> str:
    # Small deterministic Marathi-oriented fallback.
    table = {
        "ksh": "क्ष", "dny": "ज्ञ", "gy": "ज्ञ", "tr": "त्र", "shr": "श्र",
        "kh": "ख", "gh": "घ", "chh": "छ", "ch": "च", "jh": "झ", "th": "थ",
        "dh": "ध", "ph": "फ", "bh": "भ", "sh": "श", "ng": "ं",
        "k": "क", "g": "ग", "j": "ज", "t": "त", "d": "द", "n": "न",
        "p": "प", "b": "ब", "m": "म", "y": "य", "r": "र", "l": "ल",
        "v": "व", "w": "व", "s": "स", "h": "ह", "f": "फ", "q": "क",
        "x": "क्स", "z": "झ",
    }
    vowels = {"aa": "ा", "ii": "ी", "ee": "ी", "uu": "ू", "oo": "ू",
              "ai": "ै", "au": "ौ", "i": "ि", "u": "ु", "e": "े", "o": "ो"}
    independent = {"a": "अ", "aa": "आ", "i": "इ", "ii": "ई", "ee": "ई",
                   "u": "उ", "uu": "ऊ", "oo": "ऊ", "e": "ए", "ai": "ऐ", "o": "ओ", "au": "औ"}
    out, i, pending_consonant = [], 0, False
    while i < len(word):
        match = None
        for n in (3, 2, 1):
            p = word[i:i+n]
            if p in table or p in vowels or p in independent:
                match = p
                break
        if match is None:
            out.append(word[i]); i += 1; pending_consonant = False; continue
        if match in vowels and pending_consonant:
            out.append(vowels[match])
        elif match in independent and not pending_consonant:
            out.append(independent[match])
        elif match in table:
            out.append(table[match]); pending_consonant = True; i += len(match); continue
        else:
            out.append(independent.get(match, match))
        pending_consonant = False
        i += len(match)
    return "".join(out)
