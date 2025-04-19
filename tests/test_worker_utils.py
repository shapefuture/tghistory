from app.worker.utils import clean_message_text

def test_clean_message_text_removes_zero_width():
    s = "A\u200bB\u200cC"
    cleaned = clean_message_text(s)
    assert cleaned == "ABC"

def test_clean_message_text_whitespace():
    s = " \nfoo   bar\n"
    cleaned = clean_message_text(s)
    assert cleaned == "foo bar"