from __future__ import annotations

import pytest
from sqlite3 import IntegrityError

from angry_agents.src.db.services import TopicService


class TestCreate:
    def test_returns_topic_with_id(self, db):
        t = TopicService(db).create("Breaking Bad")
        assert t.id is not None
        assert t.title == "Breaking Bad"

    def test_description_optional(self, db):
        t = TopicService(db).create("Bare")
        assert t.description is None

    def test_description_stored(self, db):
        t = TopicService(db).create("Topic", description="Some desc")
        assert t.description == "Some desc"

    def test_created_by_stored(self, db, topic):
        # Reuse the existing user fixture indirectly via topic fixture's DB state.
        # Create a user row to reference.
        from angry_agents.src.db.repositories import user_repository as ur
        u = ur.create(db, {
            "username": "u1", "password": "pw", "name": "A", "surname": "B",
            "email": "a@x.com", "slug": "a-b"
        })
        t = TopicService(db).create("Owned", created_by=u.id)
        assert t.created_by == u.id

    def test_timestamps_set(self, db):
        t = TopicService(db).create("TS")
        assert t.created_at is not None
        assert t.deleted_at is None

    def test_duplicate_title_raises(self, db):
        TopicService(db).create("Unique")
        with pytest.raises(IntegrityError):
            TopicService(db).create("Unique")


class TestGet:
    def test_returns_correct_topic(self, db):
        t = TopicService(db).create("Get Test")
        fetched = TopicService(db).get(t.id)
        assert fetched.title == "Get Test"

    def test_missing_returns_none(self, db):
        assert TopicService(db).get(9999) is None


class TestUpdate:
    def test_updates_title(self, db):
        t = TopicService(db).create("Old Title")
        updated = TopicService(db).update(t.id, {"title": "New Title"})
        assert updated.title == "New Title"

    def test_updates_description(self, db):
        t = TopicService(db).create("Desc Test")
        updated = TopicService(db).update(t.id, {"description": "Added desc"})
        assert updated.description == "Added desc"

    def test_empty_patch_is_noop(self, db):
        t = TopicService(db).create("Noop")
        updated = TopicService(db).update(t.id, {})
        assert updated.title == "Noop"


class TestDelete:
    def test_soft_delete_sets_deleted_at(self, db):
        t = TopicService(db).create("Soft Del")
        TopicService(db).delete(t.id)
        from angry_agents.src.db.repositories import topic_repository as r
        assert r.get(db, t.id).deleted_at is not None

    def test_hard_delete_removes_row(self, db):
        t = TopicService(db).create("Hard Del")
        TopicService(db).delete(t.id, hard=True)
        assert TopicService(db).get(t.id) is None


class TestQuery:
    def test_returns_active_topics(self, db):
        TopicService(db).create("Q1")
        TopicService(db).create("Q2")
        assert len(TopicService(db).query()) == 2

    def test_filter_by_title(self, db):
        TopicService(db).create("Alpha")
        TopicService(db).create("Beta")
        results = TopicService(db).query(filters={"title": "Alpha"})
        assert len(results) == 1
        assert results[0].title == "Alpha"

    def test_limit_and_offset(self, db):
        svc = TopicService(db)
        for i in range(4):
            svc.create(f"Topic{i}")
        assert len(svc.query(limit=2)) == 2
        assert len(svc.query(offset=2)) == 2

    def test_soft_deleted_excluded(self, db):
        t = TopicService(db).create("Deleted")
        TopicService(db).delete(t.id)
        assert TopicService(db).query() == []
