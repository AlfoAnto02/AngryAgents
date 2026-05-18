from __future__ import annotations

import pytest

from angry_agents.src.db.repositories import rels


class TestAddAgentTopic:
    def test_sets_id_topic_on_agent(self, db, agent, topic):
        rel_id = rels.add(db, src=agent.id, tgt=topic.id, rel_type="agent_topic")
        from angry_agents.src.db.repositories import agents_repository as agents_repo
        updated = agents_repo.get(db, agent.id)
        assert updated.id_topic == topic.id

    def test_returns_correct_rel_id(self, db, agent, topic):
        rel_id = rels.add(db, src=agent.id, tgt=topic.id, rel_type="agent_topic")
        assert rel_id == ("agent_topic", agent.id, topic.id)


class TestAddJudgeChat:
    def test_creates_judge_evaluation_row(self, db, judge, chat):
        rels.add(db, src=judge.id, tgt=chat.id, rel_type="judge_chat")
        from angry_agents.src.db.repositories import judge_evaluation_repository as eval_repo
        ev = eval_repo.get(db, judge.id, chat.id)
        assert ev is not None

    def test_score_stored_from_details(self, db, judge, chat):
        rels.add(db, src=judge.id, tgt=chat.id, rel_type="judge_chat", details={"score": 4.5})
        from angry_agents.src.db.repositories import judge_evaluation_repository as eval_repo
        ev = eval_repo.get(db, judge.id, chat.id)
        assert ev.score == 4.5

    def test_returns_correct_rel_id(self, db, judge, chat):
        rel_id = rels.add(db, src=judge.id, tgt=chat.id, rel_type="judge_chat")
        assert rel_id == ("judge_chat", judge.id, chat.id)


class TestAddUnknownType:
    def test_raises_value_error(self, db):
        with pytest.raises(ValueError, match="unknown rel_type"):
            rels.add(db, src=1, tgt=1, rel_type="nonexistent")


class TestRemoveAgentTopic:
    def test_sets_id_topic_to_null(self, db, agent, topic):
        rels.add(db, src=agent.id, tgt=topic.id, rel_type="agent_topic")
        rels.remove(db, ("agent_topic", agent.id, topic.id))
        from angry_agents.src.db.repositories import agents_repository as agents_repo
        updated = agents_repo.get(db, agent.id)
        assert updated.id_topic is None


class TestRemoveJudgeChat:
    def test_soft_remove_sets_deleted_at(self, db, judge, chat):
        rels.add(db, src=judge.id, tgt=chat.id, rel_type="judge_chat")
        rels.remove(db, ("judge_chat", judge.id, chat.id), hard=False)
        from angry_agents.src.db.repositories import judge_evaluation_repository as eval_repo
        ev = eval_repo.get(db, judge.id, chat.id)
        assert ev.deleted_at is not None

    def test_hard_remove_deletes_row(self, db, judge, chat):
        rels.add(db, src=judge.id, tgt=chat.id, rel_type="judge_chat")
        rels.remove(db, ("judge_chat", judge.id, chat.id), hard=True)
        from angry_agents.src.db.repositories import judge_evaluation_repository as eval_repo
        assert eval_repo.get(db, judge.id, chat.id) is None


class TestRemoveUnknownType:
    def test_raises_value_error(self, db):
        with pytest.raises(ValueError, match="unknown rel_type"):
            rels.remove(db, ("bad_type", 1, 1))


class TestListRels:
    def test_lists_agent_topic_rel(self, db, agent, topic):
        rels.add(db, src=agent.id, tgt=topic.id, rel_type="agent_topic")
        results = rels.list_rels(db, rel_type="agent_topic")
        assert any(r["src"] == agent.id and r["tgt"] == topic.id for r in results)

    def test_lists_judge_chat_rel(self, db, judge, chat):
        rels.add(db, src=judge.id, tgt=chat.id, rel_type="judge_chat")
        results = rels.list_rels(db, rel_type="judge_chat")
        assert any(r["src"] == judge.id and r["tgt"] == chat.id for r in results)

    def test_filter_by_src(self, db, agent, topic):
        rels.add(db, src=agent.id, tgt=topic.id, rel_type="agent_topic")
        results = rels.list_rels(db, src=agent.id, rel_type="agent_topic")
        assert all(r["src"] == agent.id for r in results)

    def test_filter_by_tgt(self, db, agent, topic):
        rels.add(db, src=agent.id, tgt=topic.id, rel_type="agent_topic")
        results = rels.list_rels(db, tgt=topic.id, rel_type="agent_topic")
        assert all(r["tgt"] == topic.id for r in results)

    def test_soft_removed_excluded(self, db, judge, chat):
        rels.add(db, src=judge.id, tgt=chat.id, rel_type="judge_chat")
        rels.remove(db, ("judge_chat", judge.id, chat.id), hard=False)
        results = rels.list_rels(db, rel_type="judge_chat")
        assert not any(r["src"] == judge.id for r in results)

    def test_no_filter_returns_both_types(self, db, agent, topic, judge, chat):
        rels.add(db, src=agent.id, tgt=topic.id, rel_type="agent_topic")
        rels.add(db, src=judge.id, tgt=chat.id, rel_type="judge_chat")
        results = rels.list_rels(db)
        types = {r["rel_type"] for r in results}
        assert "agent_topic" in types
        assert "judge_chat" in types
