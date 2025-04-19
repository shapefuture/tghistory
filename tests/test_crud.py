from app.crud import get_processing_request
from app.userbot import state

def test_get_processing_request(monkeypatch):
    rid = "testrid"
    state.store_request_data(rid, {
        "user_id": "u",
        "target_chat_id": "c",
        "status": "S",
        "participants_file": "/tmp/foo.txt",
        "summary": "sum",
        "error": None,
    })
    req = get_processing_request(rid)
    assert req.request_id == rid
    assert req.user_id == "u"
    assert req.tasks[0].chat_id == "c"