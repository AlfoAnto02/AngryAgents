from __future__ import annotations

from angry_agents.src.db.services import ChatMessageService

SECRET = "test-secret-key"


class TestCreate:
    def test_message_stored(self, db, chat):
        svc = ChatMessageService(db, SECRET)
        m = svc.create(chat.id, "Science!", "Jesse", "Pinkman")
        assert m.message == "Science!"
        assert m.id_chat == chat.id

    def test_author_is_not_raw_name(self, db, chat):
        svc = ChatMessageService(db, SECRET)
        m = svc.create(chat.id, "Hello", "Walter", "White")
        assert m.author != "Walter White"
        assert "Walter" in m.author

    def test_author_contains_hmac_digest(self, db, chat):
        svc = ChatMessageService(db, SECRET)
        m = svc.create(chat.id, "Hello", "Walter", "White")
        parts = m.author.split(" ")
        assert len(parts) == 3
        assert len(parts[2]) == 12

    def test_same_agent_same_secret_produces_same_token(self, db, chat):
        svc = ChatMessageService(db, SECRET)
        m1 = svc.create(chat.id, "Msg1", "Walter", "White")
        m2 = svc.create(chat.id, "Msg2", "Walter", "White")
        assert m1.author == m2.author

    def test_different_secret_produces_different_token(self, db, chat):
        m1 = ChatMessageService(db, "secret-A").create(chat.id, "Hi", "Walter", "White")
        m2 = ChatMessageService(db, "secret-B").create(chat.id, "Hi", "Walter", "White")
        assert m1.author != m2.author

    def test_different_agents_produce_different_tokens(self, db, chat):
        svc = ChatMessageService(db, SECRET)
        m1 = svc.create(chat.id, "Hi", "Walter", "White")
        m2 = svc.create(chat.id, "Hi", "Jesse", "Pinkman")
        assert m1.author != m2.author


class TestGet:
    def test_returns_message(self, db, chat):
        svc = ChatMessageService(db, SECRET)
        m = svc.create(chat.id, "Yo", "Jesse", "Pinkman")
        assert svc.get(m.id).id == m.id

    def test_missing_returns_none(self, db):
        assert ChatMessageService(db, SECRET).get(9999) is None


class TestUpdate:
    def test_updates_message_text(self, db, chat):
        svc = ChatMessageService(db, SECRET)
        m = svc.create(chat.id, "Original", "Walter", "White")
        updated = svc.update(m.id, {"message": "Edited"})
        assert updated.message == "Edited"


class TestDelete:
    def test_soft_delete(self, db, chat):
        svc = ChatMessageService(db, SECRET)
        m = svc.create(chat.id, "Bye", "Walter", "White")
        svc.delete(m.id)
        assert svc.get(m.id).deleted_at is not None

    def test_hard_delete(self, db, chat):
        svc = ChatMessageService(db, SECRET)
        m = svc.create(chat.id, "Gone", "Walter", "White")
        svc.delete(m.id, hard=True)
        assert svc.get(m.id) is None
