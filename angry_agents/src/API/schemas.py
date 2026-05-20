from __future__ import annotations

from pydantic import BaseModel, Field


class UserOut(BaseModel):
    id: int | None = Field(None, description="Auto-generated primary key")
    username: str
    name: str
    surname: str
    email: str
    role: str = Field(..., description="One of: common | admin")
    slug: str = Field(..., description="URL-safe unique identifier derived from name+surname")
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = Field(None, description="Non-null means soft-deleted")


class TopicOut(BaseModel):
    id: int | None = Field(None, description="Auto-generated primary key")
    title: str = Field(..., description="Unique topic title")
    description: str | None = Field(None, description="Optional long-form description")
    created_by: int | None = Field(None, description="FK to User.ID")
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = Field(None, description="Non-null means soft-deleted")


class AgentOut(BaseModel):
    id: int | None = Field(None, description="Auto-generated primary key")
    id_topic: int | None = Field(None, description="Parent topic")
    created_by: int | None = Field(None, description="FK to User.ID")
    name: str
    surname: str
    slug: str = Field(..., description="URL-safe unique identifier derived from name+surname")
    summary: str | None = Field(None, description="JSON-encoded persona summary")
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = None


class AgentContextOut(BaseModel):
    id_context: int | None = Field(None, description="Auto-generated primary key")
    id_agent: int = Field(..., description="Parent agent")
    signature_phrases: str | None = Field(None, description="JSON-encoded list of signature phrases")
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = None


class GroupChatOut(BaseModel):
    id: int | None = Field(None, description="Auto-generated primary key")
    id_topic: int = Field(..., description="Topic this chat belongs to")
    created_by: int | None = Field(None, description="FK to User.ID")
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = None


class ChatMessageOut(BaseModel):
    id: int | None = Field(None, description="Auto-generated primary key")
    id_chat: int = Field(..., description="Parent group chat")
    message: str
    author: str | None = Field(
        None,
        description="Anonymised agent token (name+surname+HMAC). "
                    "NULL for user-posted messages.",
    )
    created_by: int | None = Field(None, description="FK to User.ID — set for user-posted messages")
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = None


class JudgeOut(BaseModel):
    id: int | None = Field(None, description="Auto-generated primary key")
    role: str = Field(..., description="One of: style | ideology | general | behavioral")
    temperature: float | None = Field(None, description="LLM sampling temperature for this judge")
    guess: str | None = Field(None, description="Judge's current persona guess")
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = None


class JudgeEvaluationOut(BaseModel):
    id_judge: int = Field(..., description="FK to Judges")
    id_chat: int = Field(..., description="FK to Group_chat")
    score: list[float] | None = Field(None, description="Fidelity scores 1–5")
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = None


class TokenOut(BaseModel):
    access_token: str = Field(..., description="Short-lived JWT — send as 'Authorization: Bearer <token>'")
    token_type: str = Field("bearer", description="Always 'bearer'")
    user: UserOut = Field(..., description="Authenticated user info")
    refresh_token: str | None = Field(None, description="Long-lived refresh token — store securely")


class AccessTokenOut(BaseModel):
    access_token: str = Field(..., description="Refreshed short-lived JWT")
    token_type: str = Field("bearer", description="Always 'bearer'")
