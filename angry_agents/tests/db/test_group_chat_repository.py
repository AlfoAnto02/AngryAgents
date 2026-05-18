from __future__ import annotations

from angry_agents.src.db.repositories import group_chat_repository as repo


class TestCreate:
    def test_returns_chat_with_id(self, db, topic):
        c = repo.create(db, {"id_topic": topic.id})
        assert c.id is not None
        assert c.id_topic == topic.id

    def test_timestamps_set(self, db, topic):
        c = repo.create(db, {"id_topic": topic.id})
        assert c.created_at is not None
        assert c.deleted_at is None

    def test_multiple_chats_same_topic(self, db, topic):
        c1 = repo.create(db, {"id_topic": topic.id})
        c2 = repo.create(db, {"id_topic": topic.id})
        assert c1.id != c2.id


class TestGet:
    def test_returns_correct_chat(self, db, topic):
        c = repo.create(db, {"id_topic": topic.id})
        fetched = repo.get(db, c.id)
        assert fetched.id == c.id
        assert fetched.id_topic == topic.id

    def test_missing_returns_none(self, db):
        assert repo.get(db, 9999) is None


class TestUpdate:
    def test_updates_id_topic(self, db, topic):
        from angry_agents.src.db.repositories import topic_repository as topic_repo
        topic2 = topic_repo.create(db, {"title": "Better Call Saul"})
        c = repo.create(db, {"id_topic": topic.id})
        updated = repo.update(db, c.id, {"id_topic": topic2.id})
        assert updated.id_topic == topic2.id

    def test_empty_patch_is_noop(self, db, topic):
        c = repo.create(db, {"id_topic": topic.id})
        updated = repo.update(db, c.id, {})
        assert updated.id_topic == topic.id


class TestDelete:
    def test_soft_delete_sets_deleted_at(self, db, topic):
        c = repo.create(db, {"id_topic": topic.id})
        repo.delete(db, c.id)
        assert repo.get(db, c.id).deleted_at is not None

    def test_soft_deleted_excluded_from_query(self, db, topic):
        c = repo.create(db, {"id_topic": topic.id})
        repo.delete(db, c.id)
        assert all(r.id != c.id for r in repo.query(db))

    def test_hard_delete_removes_row(self, db, topic):
        c = repo.create(db, {"id_topic": topic.id})
        repo.delete(db, c.id, hard=True)
        assert repo.get(db, c.id) is None


class TestQuery:
    def test_filter_by_id_topic(self, db, topic):
        from angry_agents.src.db.repositories import topic_repository as topic_repo
        topic2 = topic_repo.create(db, {"title": "El Camino"})
        c1 = repo.create(db, {"id_topic": topic.id})
        repo.create(db, {"id_topic": topic2.id})
        results = repo.query(db, filters={"id_topic": topic.id})
        assert len(results) == 1
        assert results[0].id == c1.id

    def test_limit_and_offset(self, db, topic):
        for _ in range(4):
            repo.create(db, {"id_topic": topic.id})
        assert len(repo.query(db, limit=2)) == 2
        assert len(repo.query(db, offset=3)) == 1
