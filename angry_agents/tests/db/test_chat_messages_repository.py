from __future__ import annotations

from angry_agents.src.db.repositories import chat_messages_repository as repo


def _msg(db, chat_id, message="Hello", author="walter white abc123"):
    return repo.create(db, {"id_chat": chat_id, "message": message, "author": author})


class TestCreate:
    def test_returns_message_with_id(self, db, chat):
        m = _msg(db, chat.id)
        assert m.id is not None
        assert m.id_chat == chat.id
        assert m.message == "Hello"
        assert m.author == "walter white abc123"

    def test_timestamps_set(self, db, chat):
        m = _msg(db, chat.id)
        assert m.created_at is not None
        assert m.deleted_at is None


class TestGet:
    def test_returns_correct_message(self, db, chat):
        m = _msg(db, chat.id, message="Science!")
        fetched = repo.get(db, m.id)
        assert fetched.id == m.id
        assert fetched.message == "Science!"

    def test_missing_returns_none(self, db):
        assert repo.get(db, 9999) is None


class TestUpdate:
    def test_updates_message_text(self, db, chat):
        m = _msg(db, chat.id, message="Original")
        updated = repo.update(db, m.id, {"message": "Revised"})
        assert updated.message == "Revised"

    def test_author_cannot_be_updated(self, db, chat):
        m = _msg(db, chat.id, author="original-author")
        updated = repo.update(db, m.id, {"author": "tampered-author"})
        assert updated.author == "original-author"

    def test_empty_patch_is_noop(self, db, chat):
        m = _msg(db, chat.id, message="Unchanged")
        updated = repo.update(db, m.id, {})
        assert updated.message == "Unchanged"


class TestDelete:
    def test_soft_delete_sets_deleted_at(self, db, chat):
        m = _msg(db, chat.id)
        repo.delete(db, m.id)
        assert repo.get(db, m.id).deleted_at is not None

    def test_soft_deleted_excluded_from_query(self, db, chat):
        m = _msg(db, chat.id)
        repo.delete(db, m.id)
        assert all(r.id != m.id for r in repo.query(db))

    def test_hard_delete_removes_row(self, db, chat):
        m = _msg(db, chat.id)
        repo.delete(db, m.id, hard=True)
        assert repo.get(db, m.id) is None


class TestQuery:
    def test_filter_by_id_chat(self, db, chat, topic):
        from angry_agents.src.db.repositories import group_chat_repository as chat_repo
        other_chat = chat_repo.create(db, {"id_topic": topic.id})
        m1 = _msg(db, chat.id, message="In chat1")
        _msg(db, other_chat.id, message="In chat2")
        results = repo.query(db, filters={"id_chat": chat.id})
        assert len(results) == 1
        assert results[0].id == m1.id

    def test_ordered_by_id_asc(self, db, chat):
        m1 = _msg(db, chat.id, message="First")
        m2 = _msg(db, chat.id, message="Second")
        m3 = _msg(db, chat.id, message="Third")
        results = repo.query(db, filters={"id_chat": chat.id})
        ids = [r.id for r in results]
        assert ids == sorted(ids)

    def test_limit_and_offset(self, db, chat):
        for i in range(5):
            _msg(db, chat.id, message=f"msg{i}")
        assert len(repo.query(db, limit=3)) == 3
        assert len(repo.query(db, offset=3)) == 2
