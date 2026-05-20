from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from sqlite3 import IntegrityError

from angry_agents.src.db.repositories import refresh_token_repository as repo, user_repository as user_repo


def _future(days: int = 7) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )


def _past(days: int = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )


def _hash(plain: str) -> str:
    return hashlib.sha256(plain.encode()).hexdigest()


@pytest.fixture
def user(db):
    return user_repo.create(
        db,
        {
            "username": "walter",
            "password": "hashed",
            "name": "Walter",
            "surname": "White",
            "email": "w@x.com",
            "slug": "walter-white",
        },
    )


@pytest.fixture
def token(db, user):
    return repo.create(db, user.id, _hash("plain-token"), _future())


class TestCreate:
    def test_returns_token_with_id(self, db, user):
        t = repo.create(db, user.id, _hash("tok1"), _future())
        assert t.id is not None

    def test_stores_user_id(self, db, user):
        t = repo.create(db, user.id, _hash("tok2"), _future())
        assert t.user_id == user.id

    def test_stores_token_hash(self, db, user):
        h = _hash("tok3")
        t = repo.create(db, user.id, h, _future())
        assert t.token_hash == h

    def test_stores_expires_at(self, db, user):
        exp = _future(14)
        t = repo.create(db, user.id, _hash("tok4"), exp)
        assert t.expires_at == exp

    def test_revoked_at_is_none(self, db, user):
        t = repo.create(db, user.id, _hash("tok5"), _future())
        assert t.revoked_at is None

    def test_created_at_set(self, db, user):
        t = repo.create(db, user.id, _hash("tok6"), _future())
        assert t.created_at is not None

    def test_duplicate_hash_raises(self, db, user):
        h = _hash("dup-token")
        repo.create(db, user.id, h, _future())
        with pytest.raises(IntegrityError):
            repo.create(db, user.id, h, _future())


class TestGetByHash:
    def test_returns_correct_token(self, db, token):
        found = repo.get_by_hash(db, token.token_hash)
        assert found is not None
        assert found.id == token.id

    def test_unknown_hash_returns_none(self, db):
        assert repo.get_by_hash(db, _hash("does-not-exist")) is None


class TestRevoke:
    def test_sets_revoked_at(self, db, token):
        repo.revoke(db, token.token_hash)
        found = repo.get_by_hash(db, token.token_hash)
        assert found.revoked_at is not None

    def test_idempotent_on_already_revoked(self, db, token):
        repo.revoke(db, token.token_hash)
        repo.revoke(db, token.token_hash)  # must not raise
        found = repo.get_by_hash(db, token.token_hash)
        assert found.revoked_at is not None

    def test_unknown_hash_is_noop(self, db):
        repo.revoke(db, _hash("nonexistent"))  # must not raise

    def test_only_target_token_revoked(self, db, user):
        t1 = repo.create(db, user.id, _hash("t1"), _future())
        t2 = repo.create(db, user.id, _hash("t2"), _future())
        repo.revoke(db, t1.token_hash)
        assert repo.get_by_hash(db, t2.token_hash).revoked_at is None


class TestRevokeAllForUser:
    def test_revokes_all_active_tokens_for_user(self, db, user):
        t1 = repo.create(db, user.id, _hash("r1"), _future())
        t2 = repo.create(db, user.id, _hash("r2"), _future())
        repo.revoke_all_for_user(db, user.id)
        assert repo.get_by_hash(db, t1.token_hash).revoked_at is not None
        assert repo.get_by_hash(db, t2.token_hash).revoked_at is not None

    def test_does_not_affect_other_users(self, db, user):
        other = user_repo.create(
            db,
            {
                "username": "jesse",
                "password": "pw",
                "name": "Jesse",
                "surname": "Pinkman",
                "email": "j@x.com",
                "slug": "jesse-pinkman",
            },
        )
        t_other = repo.create(db, other.id, _hash("other-tok"), _future())
        repo.revoke_all_for_user(db, user.id)
        assert repo.get_by_hash(db, t_other.token_hash).revoked_at is None

    def test_skips_already_revoked_tokens(self, db, user):
        t = repo.create(db, user.id, _hash("already"), _future())
        repo.revoke(db, t.token_hash)
        repo.revoke_all_for_user(db, user.id)  # must not raise
        assert repo.get_by_hash(db, t.token_hash).revoked_at is not None
