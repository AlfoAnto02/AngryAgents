from .roles import JudgeRole
from .user import User, CREATE_TABLE as _USER_DDL
from .topic import Topic, CREATE_TABLE as _TOPIC_DDL
from .agents import Agent, CREATE_TABLE as _AGENTS_DDL
from .agent_context import AgentContext, CREATE_TABLE as _AGENT_CONTEXT_DDL
from .group_chat import GroupChat, CREATE_TABLE as _GROUP_CHAT_DDL
from .chat_agent import CREATE_TABLE as _CHAT_AGENT_DDL
from .chat_messages import ChatMessage, CREATE_TABLE as _CHAT_MESSAGES_DDL
from .judges import Judge, CREATE_TABLE as _JUDGES_DDL
from .judge_evaluation import JudgeEvaluation, CREATE_TABLE as _JUDGE_EVAL_DDL
from .refresh_token import RefreshToken, CREATE_TABLE as _REFRESH_TOKEN_DDL

# Ordered by FK dependency so init_db() runs cleanly.
# User must be first — Topic, Agents, Group_chat, Chat_messages all FK to it.
# Chat_agent references Group_chat and Agents, so it goes after both.
# RefreshToken references User so it goes after.
ALL_DDL = [
    _USER_DDL,
    _TOPIC_DDL,
    _AGENTS_DDL,
    _AGENT_CONTEXT_DDL,
    _GROUP_CHAT_DDL,
    _CHAT_AGENT_DDL,
    _CHAT_MESSAGES_DDL,
    _JUDGES_DDL,
    _JUDGE_EVAL_DDL,
    _REFRESH_TOKEN_DDL,
]

__all__ = [
    "ALL_DDL",
    "JudgeRole",
    "User",
    "Topic",
    "Agent",
    "AgentContext",
    "GroupChat",
    "ChatMessage",
    "Judge",
    "JudgeEvaluation",
    "RefreshToken",
]
