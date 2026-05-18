from __future__ import annotations

import pytest

from angry_agents.src.db.services import JudgeService

VALID_ROLES = ["style", "ideology", "general", "behavioral"]


class TestCreate:
    @pytest.mark.parametrize("role", VALID_ROLES)
    def test_valid_roles_accepted(self, db, role):
        j = JudgeService(db).create(role=role)
        assert j.role == role

    def test_invalid_role_raises_value_error(self, db):
        with pytest.raises(ValueError):
            JudgeService(db).create(role="invalid_role")

    def test_temperature_stored(self, db):
        j = JudgeService(db).create(role="style", temperature=0.8)
        assert j.temperature == 0.8

    def test_guess_stored(self, db):
        j = JudgeService(db).create(role="general", guess="Walter White")
        assert j.guess == "Walter White"


class TestUpdate:
    def test_valid_role_update_accepted(self, db):
        svc = JudgeService(db)
        j = svc.create(role="style")
        updated = svc.update(j.id, {"role": "ideology"})
        assert updated.role == "ideology"

    def test_invalid_role_update_raises_value_error(self, db):
        svc = JudgeService(db)
        j = svc.create(role="style")
        with pytest.raises(ValueError):
            svc.update(j.id, {"role": "bad_role"})

    def test_role_unchanged_when_not_in_patch(self, db):
        svc = JudgeService(db)
        j = svc.create(role="behavioral")
        updated = svc.update(j.id, {"temperature": 1.0})
        assert updated.role == "behavioral"


class TestGet:
    def test_returns_judge(self, db):
        svc = JudgeService(db)
        j = svc.create(role="general")
        assert svc.get(j.id).id == j.id

    def test_missing_returns_none(self, db):
        assert JudgeService(db).get(9999) is None


class TestDelete:
    def test_soft_delete(self, db):
        svc = JudgeService(db)
        j = svc.create(role="style")
        svc.delete(j.id)
        assert svc.get(j.id).deleted_at is not None

    def test_hard_delete(self, db):
        svc = JudgeService(db)
        j = svc.create(role="ideology")
        svc.delete(j.id, hard=True)
        assert svc.get(j.id) is None


class TestQuery:
    def test_filter_by_role(self, db):
        svc = JudgeService(db)
        svc.create(role="style")
        svc.create(role="general")
        results = svc.query(filters={"role": "style"})
        assert len(results) == 1
        assert results[0].role == "style"
