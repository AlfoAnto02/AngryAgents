from __future__ import annotations

import pytest

from angry_agents.src.db.services import GroupChatService


class TestCreate:
    def test_returns_chat_with_id(self, db, topic):
        c = GroupChatService(db).create(topic.id)
        assert c.id is not None
        assert c.id_topic == topic.id

    def test_created_by_optional(self, db, topic):
        c = GroupChatService(db).create(topic.id)
        assert c.created_by is None

    def test_created_by_stored(self, db, topic):
        from angry_agents.src.db.repositories import user_repository as ur
        u = ur.create(db, {
            "username": "u1", "password": "pw", "name": "A", "surname": "B",
            "email": "a@x.com", "slug": "a-b",
        })
        c = GroupChatService(db).create(topic.id, created_by=u.id)
        assert c.created_by == u.id

    def test_timestamps_set(self, db, topic):
        c = GroupChatService(db).create(topic.id)
        assert c.created_at is not None
        assert c.deleted_at is None


class TestGet:
    def test_returns_correct_chat(self, db, topic):
        c = GroupChatService(db).create(topic.id)
        fetched = GroupChatService(db).get(c.id)
        assert fetched.id == c.id

    def test_missing_returns_none(self, db):
        assert GroupChatService(db).get(9999) is None


class TestUpdate:
    def test_updates_id_topic(self, db, topic):
        from angry_agents.src.db.repositories import topic_repository as tr
        other = tr.create(db, {"title": "Better Call Saul"})
        c = GroupChatService(db).create(topic.id)
        updated = GroupChatService(db).update(c.id, {"id_topic": other.id})
        assert updated.id_topic == other.id

    def test_empty_patch_is_noop(self, db, topic):
        c = GroupChatService(db).create(topic.id)
        updated = GroupChatService(db).update(c.id, {})
        assert updated.id_topic == topic.id


class TestDelete:
    def test_soft_delete_sets_deleted_at(self, db, topic):
        c = GroupChatService(db).create(topic.id)
        GroupChatService(db).delete(c.id)
        from angry_agents.src.db.repositories import group_chat_repository as r
        assert r.get(db, c.id).deleted_at is not None

    def test_hard_delete_removes_row(self, db, topic):
        c = GroupChatService(db).create(topic.id)
        GroupChatService(db).delete(c.id, hard=True)
        assert GroupChatService(db).get(c.id) is None


class TestQuery:
    def test_filter_by_id_topic(self, db, topic):
        from angry_agents.src.db.repositories import topic_repository as tr
        other = tr.create(db, {"title": "Better Call Saul"})
        GroupChatService(db).create(topic.id)
        GroupChatService(db).create(other.id)
        results = GroupChatService(db).query(filters={"id_topic": topic.id})
        assert len(results) == 1
        assert results[0].id_topic == topic.id

    def test_limit_and_offset(self, db, topic):
        svc = GroupChatService(db)
        for _ in range(4):
            svc.create(topic.id)
        assert len(svc.query(limit=2)) == 2
        assert len(svc.query(offset=2)) == 2

    def test_soft_deleted_excluded(self, db, topic):
        c = GroupChatService(db).create(topic.id)
        GroupChatService(db).delete(c.id)
        assert GroupChatService(db).query() == []
