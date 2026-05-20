from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PersonaScore:
    persona_name: str
    score: int    # 1–5


@dataclass
class AuthorMatch:
    author: str               # anonymised DIGEST from Chat_messages
    scores: list[PersonaScore]  # one score per persona profile

    @property
    def predicted(self) -> str:
        """Persona profile most likely being acted by this author."""
        return max(self.scores, key=lambda x: x.score).persona_name


@dataclass
class PersonaIdentificationResult:
    matches: list[AuthorMatch]  # one per author present in the chat


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
        For each author in the chat, score every persona profile 1–5 on how
        likely that author is acting as that persona (through the judge's focus lens).
        Returns one AuthorMatch per author, with predicted = argmax across personas.

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
