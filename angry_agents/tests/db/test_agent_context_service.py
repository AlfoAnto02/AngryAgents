from __future__ import annotations

import pytest

from angry_agents.src.db.services import AgentContextService


class TestCreate:
    def test_returns_context_with_id(self, db, agent):
        ctx = AgentContextService(db).create(agent.id)
        assert ctx.id_context is not None
        assert ctx.id_agent == agent.id

    def test_signature_phrases_optional(self, db, agent):
        ctx = AgentContextService(db).create(agent.id)
        assert ctx.signature_phrases is None

    def test_signature_phrases_stored(self, db, agent):
        phrases = '["yo", "science"]'
        ctx = AgentContextService(db).create(agent.id, signature_phrases=phrases)
        assert ctx.signature_phrases == phrases

    def test_timestamps_set(self, db, agent):
        ctx = AgentContextService(db).create(agent.id)
        assert ctx.created_at is not None
        assert ctx.deleted_at is None


class TestGet:
    def test_returns_correct_context(self, db, agent):
        ctx = AgentContextService(db).create(agent.id)
        fetched = AgentContextService(db).get(ctx.id_context)
        assert fetched.id_context == ctx.id_context

    def test_missing_returns_none(self, db):
        assert AgentContextService(db).get(9999) is None


class TestUpdate:
    def test_updates_signature_phrases(self, db, agent):
        ctx = AgentContextService(db).create(agent.id, signature_phrases='["old"]')
        updated = AgentContextService(db).update(ctx.id_context, {"signature_phrases": '["new"]'})
        assert updated.signature_phrases == '["new"]'

    def test_empty_patch_is_noop(self, db, agent):
        ctx = AgentContextService(db).create(agent.id, signature_phrases='["stay"]')
        updated = AgentContextService(db).update(ctx.id_context, {})
        assert updated.signature_phrases == '["stay"]'


class TestDelete:
    def test_soft_delete_sets_deleted_at(self, db, agent):
        ctx = AgentContextService(db).create(agent.id)
        AgentContextService(db).delete(ctx.id_context)
        from angry_agents.src.db.repositories import agent_context_repository as r
        assert r.get(db, ctx.id_context).deleted_at is not None

    def test_hard_delete_removes_row(self, db, agent):
        ctx = AgentContextService(db).create(agent.id)
        AgentContextService(db).delete(ctx.id_context, hard=True)
        assert AgentContextService(db).get(ctx.id_context) is None


class TestQuery:
    def test_filter_by_id_agent(self, db, agent, topic):
        from angry_agents.src.db.repositories import agents_repository as ar
        other = ar.create(db, {"name": "Jesse", "surname": "Pinkman", "slug": "jesse-pinkman"})
        AgentContextService(db).create(agent.id)
        AgentContextService(db).create(other.id)
        results = AgentContextService(db).query(filters={"id_agent": agent.id})
        assert len(results) == 1
        assert results[0].id_agent == agent.id

    def test_limit_and_offset(self, db, agent):
        svc = AgentContextService(db)
        for _ in range(4):
            svc.create(agent.id)
        assert len(svc.query(limit=2)) == 2
        assert len(svc.query(offset=2)) == 2

    def test_soft_deleted_excluded(self, db, agent):
        ctx = AgentContextService(db).create(agent.id)
        AgentContextService(db).delete(ctx.id_context)
        assert AgentContextService(db).query() == []
