from __future__ import annotations

import pytest

from angry_agents.src.db.repositories import judge_evaluation_repository as repo

_PI = [{"persona_name": "VADER", "predicted": "Agent A x1y2", "scores": [{"author": "Agent A x1y2", "score": 4}]}]


class TestCreate:
    def test_returns_evaluation(self, db, judge, chat):
        ev = repo.create(db, {"id_judge": judge.id, "id_chat": chat.id, "persona_identification": _PI})
        assert ev.id_judge == judge.id
        assert ev.id_chat == chat.id
        assert ev.persona_identification == _PI

    def test_persona_identification_optional(self, db, judge, chat):
        ev = repo.create(db, {"id_judge": judge.id, "id_chat": chat.id})
        assert ev.persona_identification is None

    def test_timestamps_set(self, db, judge, chat):
        ev = repo.create(db, {"id_judge": judge.id, "id_chat": chat.id})
        assert ev.created_at is not None
        assert ev.deleted_at is None

    def test_duplicate_composite_key_raises(self, db, judge, chat):
        repo.create(db, {"id_judge": judge.id, "id_chat": chat.id})
        with pytest.raises(Exception):
            repo.create(db, {"id_judge": judge.id, "id_chat": chat.id})


class TestGet:
    def test_returns_correct_evaluation(self, db, judge, chat):
        repo.create(db, {"id_judge": judge.id, "id_chat": chat.id, "persona_identification": _PI})
        ev = repo.get(db, judge.id, chat.id)
        assert ev.persona_identification == _PI

    def test_missing_returns_none(self, db):
        assert repo.get(db, 9999, 9999) is None


class TestUpdate:
    def test_updates_persona_identification(self, db, judge, chat):
        repo.create(db, {"id_judge": judge.id, "id_chat": chat.id, "persona_identification": _PI})
        updated_pi = [{"persona_name": "HOMELANDER", "predicted": "Agent B z9", "scores": [{"author": "Agent B z9", "score": 5}]}]
        updated = repo.update(db, judge.id, chat.id, {"persona_identification": updated_pi})
        assert updated.persona_identification == updated_pi

    def test_empty_patch_is_noop(self, db, judge, chat):
        repo.create(db, {"id_judge": judge.id, "id_chat": chat.id, "persona_identification": _PI})
        updated = repo.update(db, judge.id, chat.id, {})
        assert updated.persona_identification == _PI


class TestDelete:
    def test_soft_delete_sets_deleted_at(self, db, judge, chat):
        repo.create(db, {"id_judge": judge.id, "id_chat": chat.id})
        repo.delete(db, judge.id, chat.id)
        assert repo.get(db, judge.id, chat.id).deleted_at is not None

    def test_soft_deleted_excluded_from_query(self, db, judge, chat):
        repo.create(db, {"id_judge": judge.id, "id_chat": chat.id})
        repo.delete(db, judge.id, chat.id)
        assert repo.query(db) == []

    def test_hard_delete_removes_row(self, db, judge, chat):
        repo.create(db, {"id_judge": judge.id, "id_chat": chat.id})
        repo.delete(db, judge.id, chat.id, hard=True)
        assert repo.get(db, judge.id, chat.id) is None


class TestQuery:
    def test_filter_by_id_judge(self, db, judge, chat, topic):
        from angry_agents.src.db.repositories import judges_repository as judges_repo, group_chat_repository as chat_repo
        judge2 = judges_repo.create(db, {"role": "general"})
        chat2 = chat_repo.create(db, {"id_topic": topic.id})

        repo.create(db, {"id_judge": judge.id, "id_chat": chat.id})
        repo.create(db, {"id_judge": judge2.id, "id_chat": chat2.id})

        results = repo.query(db, filters={"id_judge": judge.id})
        assert len(results) == 1
        assert results[0].id_judge == judge.id

    def test_filter_by_id_chat(self, db, judge, chat, topic):
        from angry_agents.src.db.repositories import judges_repository as judges_repo, group_chat_repository as chat_repo
        judge2 = judges_repo.create(db, {"role": "behavioral"})
        chat2 = chat_repo.create(db, {"id_topic": topic.id})

        repo.create(db, {"id_judge": judge.id, "id_chat": chat.id})
        repo.create(db, {"id_judge": judge2.id, "id_chat": chat2.id})

        results = repo.query(db, filters={"id_chat": chat.id})
        assert len(results) == 1
        assert results[0].id_chat == chat.id
