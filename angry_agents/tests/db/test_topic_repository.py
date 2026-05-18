from __future__ import annotations

import pytest

from angry_agents.src.db.repositories import topic_repository as repo


class TestCreate:
    def test_returns_topic_with_id(self, db):
        t = repo.create(db, {"title": "The Wire"})
        assert t.id is not None
        assert t.title == "The Wire"

    def test_description_stored(self, db):
        t = repo.create(db, {"title": "Sopranos", "description": "HBO mob drama"})
        assert t.description == "HBO mob drama"

    def test_description_optional(self, db):
        t = repo.create(db, {"title": "Fargo"})
        assert t.description is None

    def test_duplicate_title_raises(self, db):
        repo.create(db, {"title": "Dexter"})
        with pytest.raises(Exception):
            repo.create(db, {"title": "Dexter"})

    def test_timestamps_set(self, db):
        t = repo.create(db, {"title": "Ozark"})
        assert t.created_at is not None
        assert t.updated_at is not None
        assert t.deleted_at is None


class TestGet:
    def test_returns_correct_topic(self, db):
        created = repo.create(db, {"title": "Lost"})
        fetched = repo.get(db, created.id)
        assert fetched.id == created.id
        assert fetched.title == "Lost"

    def test_missing_id_returns_none(self, db):
        assert repo.get(db, 9999) is None


class TestUpdate:
    def test_updates_title(self, db):
        t = repo.create(db, {"title": "Bones"})
        updated = repo.update(db, t.id, {"title": "Bones Updated"})
        assert updated.title == "Bones Updated"

    def test_updates_description(self, db):
        t = repo.create(db, {"title": "House"})
        updated = repo.update(db, t.id, {"description": "Medical drama"})
        assert updated.description == "Medical drama"

    def test_unknown_keys_ignored(self, db):
        t = repo.create(db, {"title": "Monk"})
        updated = repo.update(db, t.id, {"nonexistent_field": "value"})
        assert updated.title == "Monk"

    def test_empty_patch_is_noop(self, db):
        t = repo.create(db, {"title": "Monk 2"})
        updated = repo.update(db, t.id, {})
        assert updated.title == "Monk 2"


class TestDelete:
    def test_soft_delete_sets_deleted_at(self, db):
        t = repo.create(db, {"title": "Heroes"})
        repo.delete(db, t.id)
        fetched = repo.get(db, t.id)
        assert fetched.deleted_at is not None

    def test_soft_deleted_excluded_from_query(self, db):
        t = repo.create(db, {"title": "FlashForward"})
        repo.delete(db, t.id)
        results = repo.query(db)
        assert all(r.id != t.id for r in results)

    def test_hard_delete_removes_row(self, db):
        t = repo.create(db, {"title": "Firefly"})
        repo.delete(db, t.id, hard=True)
        assert repo.get(db, t.id) is None


class TestQuery:
    def test_returns_all_active(self, db):
        repo.create(db, {"title": "T1"})
        repo.create(db, {"title": "T2"})
        assert len(repo.query(db)) == 2

    def test_filter_by_title(self, db):
        repo.create(db, {"title": "MatchMe"})
        repo.create(db, {"title": "SkipMe"})
        results = repo.query(db, filters={"title": "MatchMe"})
        assert len(results) == 1
        assert results[0].title == "MatchMe"

    def test_limit(self, db):
        for i in range(5):
            repo.create(db, {"title": f"Topic{i}"})
        results = repo.query(db, limit=2)
        assert len(results) == 2

    def test_offset(self, db):
        for i in range(3):
            repo.create(db, {"title": f"Offset{i}"})
        all_results = repo.query(db)
        paged = repo.query(db, offset=1)
        assert len(paged) == len(all_results) - 1
