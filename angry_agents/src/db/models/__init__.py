from .roles import JudgeRole
from .topic import Topic, CREATE_TABLE as _TOPIC_DDL
from .agents import Agent, CREATE_TABLE as _AGENTS_DDL
from .agent_context import AgentContext, CREATE_TABLE as _AGENT_CONTEXT_DDL
from .group_chat import GroupChat, CREATE_TABLE as _GROUP_CHAT_DDL
from .chat_messages import ChatMessage, CREATE_TABLE as _CHAT_MESSAGES_DDL
from .judges import Judge, CREATE_TABLE as _JUDGES_DDL
from .judge_evaluation import JudgeEvaluation, CREATE_TABLE as _JUDGE_EVAL_DDL

# Ordered by FK dependency so init_db() runs cleanly.
ALL_DDL = [
    _TOPIC_DDL,
    _AGENTS_DDL,
    _AGENT_CONTEXT_DDL,
    _GROUP_CHAT_DDL,
    _CHAT_MESSAGES_DDL,
    _JUDGES_DDL,
    _JUDGE_EVAL_DDL,
]

__all__ = [
    "ALL_DDL",
    "JudgeRole",
    "Topic",
    "Agent",
    "AgentContext",
    "GroupChat",
    "ChatMessage",
    "Judge",
    "JudgeEvaluation",
]
