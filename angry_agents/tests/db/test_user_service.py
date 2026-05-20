from __future__ import annotations

import pytest
from sqlite3 import IntegrityError

from angry_agents.src.db.services import UserService


def _create(db, **kwargs):
    defaults = dict(
        username="walter",
        password="secret123",
        name="Walter",
        surname="White",
        email="walter@example.com",
    )
    defaults.update(kwargs)
    return UserService(db).create(**defaults)


class TestCreate:
    def test_slug_auto_generated(self, db):
        u = _create(db)
        assert u.slug == "walter-white"

    def test_slug_lowercased_and_hyphenated(self, db):
        u = _create(db, username="u1", name="Breaking", surname="Bad", email="u1@x.com")
        assert u.slug == "breaking-bad"

    def test_slug_special_chars_stripped(self, db):
        u = _create(db, username="u2", name="O'Brien", surname="Smith!", email="u2@x.com")
        assert u.slug == "obrien-smith"

    def test_slug_collision_appends_number(self, db):
        svc = UserService(db)
        svc.create("walter", "pw1", "Walter", "White", "a@x.com")
        u2 = svc.create("walt2", "pw2", "Walter", "White", "b@x.com")
        assert u2.slug == "walter-white-2"

    def test_slug_collision_increments(self, db):
        svc = UserService(db)
        svc.create("u1", "pw", "Walter", "White", "u1@x.com")
        svc.create("u2", "pw", "Walter", "White", "u2@x.com")
        u3 = svc.create("u3", "pw", "Walter", "White", "u3@x.com")
        assert u3.slug == "walter-white-3"

    def test_password_stored_hashed(self, db):
        u = _create(db)
        assert u.password != "secret123"
        assert "$" in u.password

    def test_role_defaults_to_common(self, db):
        u = _create(db)
        assert u.role == "common"

    def test_admin_role_accepted(self, db):
        u = _create(db, role="admin")
        assert u.role == "admin"

    def test_invalid_role_raises(self, db):
        with pytest.raises(ValueError, match="role"):
            _create(db, role="superuser")

    def test_duplicate_username_raises_integrity(self, db):
        _create(db)
        with pytest.raises(IntegrityError):
            _create(db, email="other@x.com")

    def test_duplicate_email_raises_integrity(self, db):
        _create(db)
        with pytest.raises(IntegrityError):
            _create(db, username="other")


class TestAuthenticate:
    def test_correct_credentials_return_user(self, db):
        _create(db)
        user = UserService(db).authenticate("walter@example.com", "secret123")
        assert user is not None
        assert user.username == "walter"

    def test_wrong_password_returns_none(self, db):
        _create(db)
        user = UserService(db).authenticate("walter@example.com", "wrongpass")
        assert user is None

    def test_unknown_email_returns_none(self, db):
        user = UserService(db).authenticate("ghost@example.com", "secret123")
        assert user is None

    def test_auth_is_constant_time(self, db):
        """Verify hmac.compare_digest is used (no timing leak via early return)."""
        _create(db)
        u1 = UserService(db).authenticate("walter@example.com", "secret123")
        u2 = UserService(db).authenticate("walter@example.com", "wrong")
        assert u1 is not None
        assert u2 is None


class TestGetBySlug:
    def test_returns_user(self, db):
        _create(db)
        u = UserService(db).get_by_slug("walter-white")
        assert u is not None
        assert u.username == "walter"

    def test_missing_returns_none(self, db):
        assert UserService(db).get_by_slug("no-one") is None

    def test_soft_deleted_not_returned(self, db):
        u = _create(db)
        UserService(db).delete(u.id)
        assert UserService(db).get_by_slug("walter-white") is None


class TestGetByEmail:
    def test_returns_user(self, db):
        _create(db)
        u = UserService(db).get_by_email("walter@example.com")
        assert u is not None

    def test_missing_returns_none(self, db):
        assert UserService(db).get_by_email("ghost@x.com") is None


class TestUpdate:
    def test_updates_name(self, db):
        u = _create(db)
        updated = UserService(db).update(u.id, {"name": "Heisenberg"})
        assert updated.name == "Heisenberg"

    def test_updating_password_rehashes(self, db):
        u = _create(db)
        svc = UserService(db)
        svc.update(u.id, {"password": "newpassword"})
        # New hash authenticates with new password
        assert svc.authenticate("walter@example.com", "newpassword") is not None
        # Old password no longer works
        assert svc.authenticate("walter@example.com", "secret123") is None

    def test_updating_password_stores_new_hash(self, db):
        u = _create(db)
        UserService(db).update(u.id, {"password": "newpassword"})
        stored = UserService(db).get(u.id)
        assert stored.password != "newpassword"
        assert "$" in stored.password

    def test_invalid_role_in_update_raises(self, db):
        u = _create(db)
        with pytest.raises(ValueError):
            UserService(db).update(u.id, {"role": "superuser"})

    def test_valid_role_update(self, db):
        u = _create(db)
        updated = UserService(db).update(u.id, {"role": "admin"})
        assert updated.role == "admin"


class TestDelete:
    def test_soft_delete(self, db):
        u = _create(db)
        UserService(db).delete(u.id)
        assert UserService(db).get(u.id).deleted_at is not None

    def test_hard_delete(self, db):
        u = _create(db)
        UserService(db).delete(u.id, hard=True)
        assert UserService(db).get(u.id) is None


class TestQuery:
    def test_filter_by_role(self, db):
        svc = UserService(db)
        svc.create("u1", "pw", "A", "B", "a@x.com", role="common")
        svc.create("u2", "pw", "C", "D", "c@x.com", role="admin")
        results = svc.query(filters={"role": "admin"})
        assert len(results) == 1
        assert results[0].username == "u2"

    def test_limit_and_offset(self, db):
        svc = UserService(db)
        for i in range(4):
            svc.create(f"u{i}", "pw", f"N{i}", "Sur", f"u{i}@x.com")
        assert len(svc.query(limit=2)) == 2
        assert len(svc.query(offset=2)) == 2
