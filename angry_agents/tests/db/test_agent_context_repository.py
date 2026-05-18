from __future__ import annotations

from angry_agents.src.db.repositories import agent_context_repository as repo


class TestCreate:
    def test_returns_context_with_id(self, db, agent):
        ctx = repo.create(db, {"id_agent": agent.id})
        assert ctx.id_context is not None
        assert ctx.id_agent == agent.id

    def test_signature_phrases_stored(self, db, agent):
        ctx = repo.create(db, {"id_agent": agent.id, "signature_phrases": '["yo", "science"]'})
        assert ctx.signature_phrases == '["yo", "science"]'

    def test_signature_phrases_optional(self, db, agent):
        ctx = repo.create(db, {"id_agent": agent.id})
        assert ctx.signature_phrases is None

    def test_timestamps_set(self, db, agent):
        ctx = repo.create(db, {"id_agent": agent.id})
        assert ctx.created_at is not None
        assert ctx.deleted_at is None


class TestGet:
    def test_returns_correct_context(self, db, agent):
        ctx = repo.create(db, {"id_agent": agent.id})
        fetched = repo.get(db, ctx.id_context)
        assert fetched.id_context == ctx.id_context

    def test_missing_returns_none(self, db):
        assert repo.get(db, 9999) is None


class TestUpdate:
    def test_updates_signature_phrases(self, db, agent):
        ctx = repo.create(db, {"id_agent": agent.id})
        updated = repo.update(db, ctx.id_context, {"signature_phrases": '["updated"]'})
        assert updated.signature_phrases == '["updated"]'

    def test_empty_patch_is_noop(self, db, agent):
        ctx = repo.create(db, {"id_agent": agent.id, "signature_phrases": "original"})
        updated = repo.update(db, ctx.id_context, {})
        assert updated.signature_phrases == "original"


class TestDelete:
    def test_soft_delete_sets_deleted_at(self, db, agent):
        ctx = repo.create(db, {"id_agent": agent.id})
        repo.delete(db, ctx.id_context)
        assert repo.get(db, ctx.id_context).deleted_at is not None

    def test_soft_deleted_excluded_from_query(self, db, agent):
        ctx = repo.create(db, {"id_agent": agent.id})
        repo.delete(db, ctx.id_context)
        assert all(c.id_context != ctx.id_context for c in repo.query(db))

    def test_hard_delete_removes_row(self, db, agent):
        ctx = repo.create(db, {"id_agent": agent.id})
        repo.delete(db, ctx.id_context, hard=True)
        assert repo.get(db, ctx.id_context) is None


class TestQuery:
    def test_filter_by_id_agent(self, db, agent, topic):
        from angry_agents.src.db.repositories import agents_repository as agents_repo
        other = agents_repo.create(db, {"name": "Jesse", "surname": "Pinkman", "slug": "jesse-p", "id_topic": topic.id})

        ctx1 = repo.create(db, {"id_agent": agent.id})
        repo.create(db, {"id_agent": other.id})

        results = repo.query(db, filters={"id_agent": agent.id})
        assert len(results) == 1
        assert results[0].id_context == ctx1.id_context

    def test_limit_and_offset(self, db, agent):
        for _ in range(3):
            repo.create(db, {"id_agent": agent.id})
        assert len(repo.query(db, limit=2)) == 2
        assert len(repo.query(db, offset=1)) == 2
