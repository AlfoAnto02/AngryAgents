from __future__ import annotations

import pytest

from angry_agents.src.db.services import AgentService


class TestCreate:
    def test_slug_auto_generated(self, db, topic):
        svc = AgentService(db)
        a = svc.create("Walter", "White", id_topic=topic.id)
        assert a.slug == "walter-white"

    def test_slug_lowercased_and_hyphenated(self, db):
        a = AgentService(db).create("Breaking", "Bad")
        assert a.slug == "breaking-bad"

    def test_slug_special_chars_stripped(self, db):
        a = AgentService(db).create("O'Brien", "Smith!")
        assert a.slug == "obrien-smith"

    def test_slug_collision_appends_number(self, db):
        svc = AgentService(db)
        a1 = svc.create("Walter", "White")
        a2 = svc.create("Walter", "White")
        assert a2.slug == "walter-white-2"

    def test_slug_collision_increments(self, db):
        svc = AgentService(db)
        svc.create("Walter", "White")
        svc.create("Walter", "White")
        a3 = svc.create("Walter", "White")
        assert a3.slug == "walter-white-3"

    def test_summary_stored(self, db):
        a = AgentService(db).create("Jesse", "Pinkman", summary='["yo"]')
        assert a.summary == '["yo"]'


class TestGetBySlug:
    def test_returns_correct_agent(self, db):
        svc = AgentService(db)
        svc.create("Gustavo", "Fring")
        a = svc.get_by_slug("gustavo-fring")
        assert a is not None
        assert a.name == "Gustavo"

    def test_missing_slug_returns_none(self, db):
        assert AgentService(db).get_by_slug("nobody-here") is None

    def test_soft_deleted_not_returned(self, db):
        svc = AgentService(db)
        a = svc.create("Mike", "Ehrmantraut")
        svc.delete(a.id)
        assert svc.get_by_slug("mike-ehrmantraut") is None


class TestGetById:
    def test_returns_correct_agent(self, db):
        svc = AgentService(db)
        a = svc.create("Hank", "Schrader")
        assert svc.get(a.id).name == "Hank"

    def test_missing_returns_none(self, db):
        assert AgentService(db).get(9999) is None


class TestUpdate:
    def test_updates_name(self, db):
        svc = AgentService(db)
        a = svc.create("Saul", "Goodman")
        updated = svc.update(a.id, {"name": "Jimmy"})
        assert updated.name == "Jimmy"


class TestDelete:
    def test_soft_delete(self, db):
        svc = AgentService(db)
        a = svc.create("Todd", "Alquist")
        svc.delete(a.id)
        assert svc.get(a.id).deleted_at is not None

    def test_hard_delete(self, db):
        svc = AgentService(db)
        a = svc.create("Lydia", "Rodarte")
        svc.delete(a.id, hard=True)
        assert svc.get(a.id) is None


class TestQuery:
    def test_filter_by_topic(self, db, topic):
        svc = AgentService(db)
        svc.create("Walter", "White", id_topic=topic.id)
        svc.create("Orphan", "Agent")
        results = svc.query(filters={"id_topic": topic.id})
        assert len(results) == 1
