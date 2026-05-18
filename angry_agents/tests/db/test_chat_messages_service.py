from __future__ import annotations

import pytest

from angry_agents.src.db.repositories import agents_repository as agents_repo
from angry_agents.src.db.services import ChatMessageService

SECRET = "test-secret-key"


@pytest.fixture
def walter(db):
    return agents_repo.create(db, {"name": "Walter", "surname": "White", "slug": "walter-white"})


@pytest.fixture
def jesse(db):
    return agents_repo.create(db, {"name": "Jesse", "surname": "Pinkman", "slug": "jesse-pinkman"})


class TestCreate:
    def test_message_stored(self, db, chat, walter):
        m = ChatMessageService(db, SECRET).create(chat.id, "Science!", walter.id)
        assert m.message == "Science!"
        assert m.id_chat == chat.id

    def test_author_contains_no_plain_text_name(self, db, chat, walter):
        m = ChatMessageService(db, SECRET).create(chat.id, "Hello", walter.id)
        assert "Walter" not in m.author
        assert "White" not in m.author

    def test_author_is_full_sha256_hex(self, db, chat, walter):
        m = ChatMessageService(db, SECRET).create(chat.id, "Hello", walter.id)
        assert len(m.author) == 64
        assert m.author.isalnum()

    def test_same_agent_same_secret_produces_same_token(self, db, chat, walter):
        svc = ChatMessageService(db, SECRET)
        m1 = svc.create(chat.id, "Msg1", walter.id)
        m2 = svc.create(chat.id, "Msg2", walter.id)
        assert m1.author == m2.author

    def test_different_secret_produces_different_token(self, db, chat, walter):
        m1 = ChatMessageService(db, "secret-A").create(chat.id, "Hi", walter.id)
        m2 = ChatMessageService(db, "secret-B").create(chat.id, "Hi", walter.id)
        assert m1.author != m2.author

    def test_different_agents_produce_different_tokens(self, db, chat, walter, jesse):
        svc = ChatMessageService(db, SECRET)
        m1 = svc.create(chat.id, "Hi", walter.id)
        m2 = svc.create(chat.id, "Hi", jesse.id)
        assert m1.author != m2.author

    def test_nonexistent_agent_raises_value_error(self, db, chat):
        with pytest.raises(ValueError, match="not found"):
            ChatMessageService(db, SECRET).create(chat.id, "Hi", agent_id=9999)

    def test_author_is_opaque_to_caller(self, db, chat, walter):
        # Caller passes only agent_id. The author field must not reveal name or surname.
        m = ChatMessageService(db, SECRET).create(chat.id, "Yo", walter.id)
        assert "Walter" not in m.author
        assert "White" not in m.author
        assert len(m.author) == 64


class TestGet:
    def test_returns_message(self, db, chat, walter):
        svc = ChatMessageService(db, SECRET)
        m = svc.create(chat.id, "Yo", walter.id)
        assert svc.get(m.id).id == m.id

    def test_missing_returns_none(self, db):
        assert ChatMessageService(db, SECRET).get(9999) is None


class TestUpdate:
    def test_updates_message_text(self, db, chat, walter):
        svc = ChatMessageService(db, SECRET)
        m = svc.create(chat.id, "Original", walter.id)
        updated = svc.update(m.id, {"message": "Edited"})
        assert updated.message == "Edited"


class TestDelete:
    def test_soft_delete(self, db, chat, walter):
        svc = ChatMessageService(db, SECRET)
        m = svc.create(chat.id, "Bye", walter.id)
        svc.delete(m.id)
        assert svc.get(m.id).deleted_at is not None

    def test_hard_delete(self, db, chat, walter):
        svc = ChatMessageService(db, SECRET)
        m = svc.create(chat.id, "Gone", walter.id)
        svc.delete(m.id, hard=True)
        assert svc.get(m.id) is None
