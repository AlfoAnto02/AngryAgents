from __future__ import annotations

import pytest

from angry_agents.src.db.repositories import agents_repository as repo


def _make(db, name="Walter", surname="White", slug="walter-white", topic_id=None):
    return repo.create(db, {"name": name, "surname": surname, "slug": slug, "id_topic": topic_id})


class TestCreate:
    def test_returns_agent_with_id(self, db, topic):
        a = _make(db, topic_id=topic.id)
        assert a.id is not None
        assert a.name == "Walter"
        assert a.surname == "White"

    def test_slug_stored(self, db):
        a = _make(db, slug="heisenberg")
        assert a.slug == "heisenberg"

    def test_topic_linked(self, db, topic):
        a = _make(db, topic_id=topic.id)
        assert a.id_topic == topic.id

    def test_summary_optional(self, db):
        a = _make(db)
        assert a.summary is None

    def test_duplicate_slug_raises(self, db):
        _make(db, slug="unique-slug")
        with pytest.raises(Exception):
            _make(db, name="Jesse", surname="Pinkman", slug="unique-slug")

    def test_timestamps_set(self, db):
        a = _make(db)
        assert a.created_at is not None
        assert a.deleted_at is None


class TestGet:
    def test_returns_correct_agent(self, db):
        a = _make(db, slug="get-test")
        fetched = repo.get(db, a.id)
        assert fetched.id == a.id
        assert fetched.slug == "get-test"

    def test_missing_returns_none(self, db):
        assert repo.get(db, 9999) is None


class TestUpdate:
    def test_updates_name(self, db):
        a = _make(db, slug="upd-slug")
        updated = repo.update(db, a.id, {"name": "Gustavo"})
        assert updated.name == "Gustavo"

    def test_updates_summary(self, db):
        a = _make(db, slug="sum-slug")
        updated = repo.update(db, a.id, {"summary": '["cook meth"]'})
        assert updated.summary == '["cook meth"]'

    def test_updates_topic(self, db, topic):
        a = _make(db, slug="topic-upd")
        updated = repo.update(db, a.id, {"id_topic": topic.id})
        assert updated.id_topic == topic.id

    def test_empty_patch_is_noop(self, db):
        a = _make(db, slug="noop-slug")
        updated = repo.update(db, a.id, {})
        assert updated.name == "Walter"


class TestDelete:
    def test_soft_delete_sets_deleted_at(self, db):
        a = _make(db, slug="soft-del")
        repo.delete(db, a.id)
        assert repo.get(db, a.id).deleted_at is not None

    def test_soft_deleted_excluded_from_query(self, db):
        a = _make(db, slug="excl-del")
        repo.delete(db, a.id)
        assert all(r.id != a.id for r in repo.query(db))

    def test_hard_delete_removes_row(self, db):
        a = _make(db, slug="hard-del")
        repo.delete(db, a.id, hard=True)
        assert repo.get(db, a.id) is None


class TestQuery:
    def test_filter_by_id_topic(self, db, topic):
        a1 = _make(db, slug="q-a1", topic_id=topic.id)
        _make(db, name="Other", surname="Guy", slug="q-a2")
        results = repo.query(db, filters={"id_topic": topic.id})
        assert len(results) == 1
        assert results[0].id == a1.id

    def test_limit_and_offset(self, db):
        for i in range(4):
            _make(db, name=f"Agent{i}", surname="X", slug=f"agent-{i}-x")
        assert len(repo.query(db, limit=2)) == 2
        assert len(repo.query(db, offset=2)) == 2
