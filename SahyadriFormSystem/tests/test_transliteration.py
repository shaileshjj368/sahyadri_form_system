from src.transliteration.marathi import transliterate


def test_transliteration_returns_marathi():
    out = transliterate('ramesh')
    assert any('ऀ' <= ch <= 'ॿ' for ch in out)


def test_multi_sentence_with_punctuation_is_fully_converted():
    # Regression test: the previous implementation only read the FIRST
    # Google Input Tools "chunk", so anything after the first comma or full
    # stop was silently dropped instead of transliterated.
    out = transliterate('mumbai la ja, ani parat ye.', prefer_online=False)
    assert 'parat' not in out
    assert 'ye' not in out.split()


def test_leading_devanagari_word_does_not_block_the_rest():
    # Regression test: the previous implementation bailed out of
    # transliterating the ENTIRE string the moment any Devanagari character
    # appeared anywhere in it (even a single leading Marathi word).
    out = transliterate('सिंह ahe ani tyacha shikshan changla ahe', prefer_online=False)
    assert out.startswith('सिंह')
    assert 'ahe' not in out


def test_empty_and_whitespace_are_preserved():
    assert transliterate('') == ''
    assert transliterate('   ') == '   '


def test_punctuation_and_digits_are_preserved():
    out = transliterate('sr. no 62283, dinank 12/03/2002.', prefer_online=False)
    assert '62283' in out
    assert '12/03/2002' in out
