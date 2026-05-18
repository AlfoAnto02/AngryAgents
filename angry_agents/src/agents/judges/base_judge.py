from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AgentScore:
    author: str   # anonymised DIGEST from Chat_messages
    score: int    # 1–5


@dataclass
class PersonaMatch:
    persona_name: str
    scores: list[AgentScore]  # one score per agent in the chat

    @property
    def predicted(self) -> str:
        """Agent DIGEST most likely acting as this persona."""
        return max(self.scores, key=lambda x: x.score).author


@dataclass
class PersonaIdentificationResult:
    matches: list[PersonaMatch]  # one per persona profile


class BaseJudge(ABC):
    """
    Base for all 20 judges.

    Each judge evaluates a full Group_chat across four dimensions.
    The judge's focus (style, ideology, general, behavioral) narrows
    the lens for every evaluation.

    Phase 1 — independent:   all four evaluate() methods
    Phase 2 — collaborative: judges see each other's outputs and revise
    """

    name: str   # e.g. "style", "ideology", "general"
    focus: str  # injected into the prompt to narrow the judge's lens

    @abstractmethod
    def persona_identification(self, chat: dict, personas: list[dict]) -> PersonaIdentificationResult:
        """
        For each persona profile, score every agent in the chat 1–5 on how
        likely they are acting as that persona (through the judge's focus lens).
        Returns the argmax per persona across all agents.

        chat    — full Group_chat dict (keys: 'chat', 'messages').
        personas — list of profile dicts from data/personas/.
        """

    @abstractmethod
    def individual_fidelity(self, _chat: dict) -> None:
        """Evaluate how faithfully each agent's messages match its persona."""

    @abstractmethod
    def group_fidelity(self, _chat: dict) -> None:
        """Evaluate how well the agents behave as a coherent group."""

    @abstractmethod
    def behavioural_fidelity(self, _chat: dict) -> None:
        """Evaluate how human-like each agent's behaviour is in the chat."""
