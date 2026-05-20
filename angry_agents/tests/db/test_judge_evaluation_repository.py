from __future__ import annotations

import pytest

from angry_agents.src.db.repositories import judge_evaluation_repository as repo


class TestCreate:
    def test_returns_evaluation(self, db, judge, chat):
        ev = repo.create(db, {"id_judge": judge.id, "id_chat": chat.id, "score": [3.5]})
        assert ev.id_judge == judge.id
        assert ev.id_chat == chat.id
        assert ev.score == [3.5]

    def test_score_optional(self, db, judge, chat):
        ev = repo.create(db, {"id_judge": judge.id, "id_chat": chat.id})
        assert ev.score is None

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
        repo.create(db, {"id_judge": judge.id, "id_chat": chat.id, "score": [4.0]})
        ev = repo.get(db, judge.id, chat.id)
        assert ev.score == [4.0]

    def test_missing_returns_none(self, db):
        assert repo.get(db, 9999, 9999) is None


class TestUpdate:
    def test_updates_score(self, db, judge, chat):
        repo.create(db, {"id_judge": judge.id, "id_chat": chat.id, "score": [2.0]})
        updated = repo.update(db, judge.id, chat.id, {"score": [5.0]})
        assert updated.score == [5.0]

    def test_empty_patch_is_noop(self, db, judge, chat):
        repo.create(db, {"id_judge": judge.id, "id_chat": chat.id, "score": [3.0]})
        updated = repo.update(db, judge.id, chat.id, {})
        assert updated.score == [3.0]


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
