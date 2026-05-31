from __future__ import annotations

import pytest

from angry_agents.src.db.repositories import judges_repository as judges_repo, group_chat_repository as chat_repo
from angry_agents.src.db.services import JudgeEvaluationService

_PI = [{"persona_name": "VADER", "predicted": "Agent A x1y2", "scores": [{"author": "Agent A x1y2", "score": 4}]}]


class TestCreate:
    def test_creates_evaluation(self, db, judge, chat):
        ev = JudgeEvaluationService(db).create(judge.id, chat.id, persona_identification=_PI)
        assert ev.id_judge == judge.id
        assert ev.id_chat == chat.id
        assert ev.persona_identification == _PI

    def test_persona_identification_optional(self, db, judge, chat):
        ev = JudgeEvaluationService(db).create(judge.id, chat.id)
        assert ev.persona_identification is None

    def test_max_20_evaluations_enforced(self, db, chat, topic):
        svc = JudgeEvaluationService(db)
        judges = [judges_repo.create(db, {"role": "style"}) for _ in range(20)]
        for j in judges:
            svc.create(j.id, chat.id)

        judge_21 = judges_repo.create(db, {"role": "general"})
        with pytest.raises(ValueError, match="20"):
            svc.create(judge_21.id, chat.id)

    def test_limit_is_per_chat_not_global(self, db, judge, chat, topic):
        svc = JudgeEvaluationService(db)
        chat2 = chat_repo.create(db, {"id_topic": topic.id})
        judges = [judges_repo.create(db, {"role": "style"}) for _ in range(20)]
        for j in judges:
            svc.create(j.id, chat.id)

        ev = svc.create(judge.id, chat2.id)
        assert ev.id_chat == chat2.id

    def test_soft_deleted_evaluations_not_counted(self, db, judge, chat, topic):
        svc = JudgeEvaluationService(db)
        judges = [judges_repo.create(db, {"role": "style"}) for _ in range(20)]
        for j in judges:
            svc.create(j.id, chat.id)

        svc.delete(judges[0].id, chat.id)

        judge_new = judges_repo.create(db, {"role": "general"})
        ev = svc.create(judge_new.id, chat.id)
        assert ev is not None


class TestGet:
    def test_returns_evaluation(self, db, judge, chat):
        svc = JudgeEvaluationService(db)
        svc.create(judge.id, chat.id, persona_identification=_PI)
        ev = svc.get(judge.id, chat.id)
        assert ev.persona_identification == _PI

    def test_missing_returns_none(self, db):
        assert JudgeEvaluationService(db).get(9999, 9999) is None


class TestUpdate:
    def test_updates_persona_identification(self, db, judge, chat):
        svc = JudgeEvaluationService(db)
        svc.create(judge.id, chat.id, persona_identification=_PI)
        updated_pi = [{"persona_name": "RICK", "predicted": "Agent C z9", "scores": [{"author": "Agent C z9", "score": 5}]}]
        updated = svc.update(judge.id, chat.id, {"persona_identification": updated_pi})
        assert updated.persona_identification == updated_pi


class TestDelete:
    def test_soft_delete(self, db, judge, chat):
        svc = JudgeEvaluationService(db)
        svc.create(judge.id, chat.id)
        svc.delete(judge.id, chat.id)
        assert svc.get(judge.id, chat.id).deleted_at is not None

    def test_hard_delete(self, db, judge, chat):
        svc = JudgeEvaluationService(db)
        svc.create(judge.id, chat.id)
        svc.delete(judge.id, chat.id, hard=True)
        assert svc.get(judge.id, chat.id) is None


class TestQuery:
    def test_filter_by_id_chat(self, db, judge, chat, topic):
        svc = JudgeEvaluationService(db)
        chat2 = chat_repo.create(db, {"id_topic": topic.id})
        judge2 = judges_repo.create(db, {"role": "general"})
        svc.create(judge.id, chat.id)
        svc.create(judge2.id, chat2.id)
        results = svc.query(filters={"id_chat": chat.id})
        assert len(results) == 1
        assert results[0].id_chat == chat.id
