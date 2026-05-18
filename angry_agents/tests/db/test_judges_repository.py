from __future__ import annotations

from angry_agents.src.db.repositories import judges_repository as repo


class TestCreate:
    def test_returns_judge_with_id(self, db):
        j = repo.create(db, {"role": "style"})
        assert j.id is not None
        assert j.role == "style"

    def test_temperature_stored(self, db):
        j = repo.create(db, {"role": "general", "temperature": 0.5})
        assert j.temperature == 0.5

    def test_guess_stored(self, db):
        j = repo.create(db, {"role": "behavioral", "guess": "Walter White"})
        assert j.guess == "Walter White"

    def test_optional_fields_default_none(self, db):
        j = repo.create(db, {"role": "ideology"})
        assert j.temperature is None
        assert j.guess is None

    def test_timestamps_set(self, db):
        j = repo.create(db, {"role": "style"})
        assert j.created_at is not None
        assert j.deleted_at is None


class TestGet:
    def test_returns_correct_judge(self, db):
        j = repo.create(db, {"role": "general", "temperature": 1.0})
        fetched = repo.get(db, j.id)
        assert fetched.id == j.id
        assert fetched.temperature == 1.0

    def test_missing_returns_none(self, db):
        assert repo.get(db, 9999) is None


class TestUpdate:
    def test_updates_role(self, db):
        j = repo.create(db, {"role": "style"})
        updated = repo.update(db, j.id, {"role": "ideology"})
        assert updated.role == "ideology"

    def test_updates_temperature(self, db):
        j = repo.create(db, {"role": "general"})
        updated = repo.update(db, j.id, {"temperature": 1.2})
        assert updated.temperature == 1.2

    def test_updates_guess(self, db):
        j = repo.create(db, {"role": "behavioral"})
        updated = repo.update(db, j.id, {"guess": "Jesse Pinkman"})
        assert updated.guess == "Jesse Pinkman"

    def test_empty_patch_is_noop(self, db):
        j = repo.create(db, {"role": "style", "temperature": 0.3})
        updated = repo.update(db, j.id, {})
        assert updated.temperature == 0.3


class TestDelete:
    def test_soft_delete_sets_deleted_at(self, db):
        j = repo.create(db, {"role": "style"})
        repo.delete(db, j.id)
        assert repo.get(db, j.id).deleted_at is not None

    def test_soft_deleted_excluded_from_query(self, db):
        j = repo.create(db, {"role": "general"})
        repo.delete(db, j.id)
        assert all(r.id != j.id for r in repo.query(db))

    def test_hard_delete_removes_row(self, db):
        j = repo.create(db, {"role": "ideology"})
        repo.delete(db, j.id, hard=True)
        assert repo.get(db, j.id) is None


class TestQuery:
    def test_filter_by_role(self, db):
        repo.create(db, {"role": "style"})
        repo.create(db, {"role": "general"})
        results = repo.query(db, filters={"role": "style"})
        assert all(r.role == "style" for r in results)

    def test_limit_and_offset(self, db):
        for role in ["style", "ideology", "general", "behavioral"]:
            repo.create(db, {"role": role})
        assert len(repo.query(db, limit=2)) == 2
        assert len(repo.query(db, offset=2)) == 2
