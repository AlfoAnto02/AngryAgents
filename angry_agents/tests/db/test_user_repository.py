from __future__ import annotations

import pytest
from sqlite3 import IntegrityError

from angry_agents.src.db.repositories import user_repository as repo


def _make(
    db,
    username="walter",
    password="hashed-pw",
    name="Walter",
    surname="White",
    email="walter@example.com",
    role="common",
    slug="walter-white",
):
    return repo.create(
        db,
        {
            "username": username,
            "password": password,
            "name": name,
            "surname": surname,
            "email": email,
            "role": role,
            "slug": slug,
        },
    )


class TestCreate:
    def test_returns_user_with_id(self, db):
        u = _make(db)
        assert u.id is not None
        assert u.username == "walter"

    def test_all_fields_stored(self, db):
        u = _make(db)
        assert u.name == "Walter"
        assert u.surname == "White"
        assert u.email == "walter@example.com"
        assert u.role == "common"
        assert u.slug == "walter-white"
        assert u.password == "hashed-pw"

    def test_role_defaults_to_common(self, db):
        u = repo.create(
            db,
            {
                "username": "jesse",
                "password": "pw",
                "name": "Jesse",
                "surname": "Pinkman",
                "email": "jesse@example.com",
                "slug": "jesse-pinkman",
            },
        )
        assert u.role == "common"

    def test_timestamps_set(self, db):
        u = _make(db)
        assert u.created_at is not None
        assert u.updated_at is not None
        assert u.deleted_at is None

    def test_duplicate_username_raises(self, db):
        _make(db)
        with pytest.raises(IntegrityError):
            _make(db, email="other@example.com", slug="other-slug")

    def test_duplicate_email_raises(self, db):
        _make(db)
        with pytest.raises(IntegrityError):
            _make(db, username="other", slug="other-slug2")

    def test_duplicate_slug_raises(self, db):
        _make(db)
        with pytest.raises(IntegrityError):
            _make(db, username="other2", email="other2@example.com")


class TestGet:
    def test_returns_correct_user(self, db):
        u = _make(db)
        fetched = repo.get(db, u.id)
        assert fetched.id == u.id
        assert fetched.username == "walter"

    def test_missing_returns_none(self, db):
        assert repo.get(db, 9999) is None

    def test_get_includes_soft_deleted(self, db):
        u = _make(db)
        repo.delete(db, u.id)
        assert repo.get(db, u.id) is not None


class TestGetBySlug:
    def test_returns_correct_user(self, db):
        _make(db)
        u = repo.get_by_slug(db, "walter-white")
        assert u is not None
        assert u.username == "walter"

    def test_missing_returns_none(self, db):
        assert repo.get_by_slug(db, "nobody") is None

    def test_soft_deleted_not_returned(self, db):
        u = _make(db)
        repo.delete(db, u.id)
        assert repo.get_by_slug(db, "walter-white") is None


class TestGetByEmail:
    def test_returns_correct_user(self, db):
        _make(db)
        u = repo.get_by_email(db, "walter@example.com")
        assert u is not None
        assert u.slug == "walter-white"

    def test_missing_returns_none(self, db):
        assert repo.get_by_email(db, "ghost@example.com") is None

    def test_soft_deleted_not_returned(self, db):
        u = _make(db)
        repo.delete(db, u.id)
        assert repo.get_by_email(db, "walter@example.com") is None


class TestGetByUsername:
    def test_returns_correct_user(self, db):
        _make(db)
        u = repo.get_by_username(db, "walter")
        assert u is not None
        assert u.email == "walter@example.com"

    def test_missing_returns_none(self, db):
        assert repo.get_by_username(db, "nobody") is None

    def test_soft_deleted_not_returned(self, db):
        u = _make(db)
        repo.delete(db, u.id)
        assert repo.get_by_username(db, "walter") is None


class TestUpdate:
    def test_updates_name(self, db):
        u = _make(db)
        updated = repo.update(db, u.id, {"name": "Heisenberg"})
        assert updated.name == "Heisenberg"

    def test_updates_email(self, db):
        u = _make(db)
        updated = repo.update(db, u.id, {"email": "heis@example.com"})
        assert updated.email == "heis@example.com"

    def test_updates_role(self, db):
        u = _make(db)
        updated = repo.update(db, u.id, {"role": "admin"})
        assert updated.role == "admin"

    def test_updates_password(self, db):
        u = _make(db)
        updated = repo.update(db, u.id, {"password": "new-hash"})
        assert updated.password == "new-hash"

    def test_empty_patch_is_noop(self, db):
        u = _make(db)
        updated = repo.update(db, u.id, {})
        assert updated.name == "Walter"


class TestDelete:
    def test_soft_delete_sets_deleted_at(self, db):
        u = _make(db)
        repo.delete(db, u.id)
        assert repo.get(db, u.id).deleted_at is not None

    def test_soft_deleted_excluded_from_query(self, db):
        u = _make(db)
        repo.delete(db, u.id)
        assert all(r.id != u.id for r in repo.query(db))

    def test_hard_delete_removes_row(self, db):
        u = _make(db)
        repo.delete(db, u.id, hard=True)
        assert repo.get(db, u.id) is None


class TestQuery:
    def test_returns_all_active_users(self, db):
        _make(db)
        assert len(repo.query(db)) == 1

    def test_filter_by_role(self, db):
        _make(db, role="common")
        _make(
            db,
            username="boss",
            email="boss@example.com",
            slug="boss-slug",
            role="admin",
        )
        results = repo.query(db, filters={"role": "admin"})
        assert len(results) == 1
        assert results[0].username == "boss"

    def test_limit_and_offset(self, db):
        for i in range(4):
            _make(
                db,
                username=f"user{i}",
                email=f"user{i}@example.com",
                slug=f"user-{i}",
            )
        assert len(repo.query(db, limit=2)) == 2
        assert len(repo.query(db, offset=2)) == 2

    def test_soft_deleted_excluded(self, db):
        u = _make(db)
        repo.delete(db, u.id)
        assert repo.query(db) == []
