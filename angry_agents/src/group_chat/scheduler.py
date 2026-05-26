from __future__ import annotations

import random
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from ..agents.personas.persona_agent import PersonaAgent


class TurnScheduler:
    strategy: Literal["round_robin", "weighted_random"]

    def __init__(self, agents: list[PersonaAgent], strategy: Literal["round_robin", "weighted_random"]):
        self.agents = agents
        self.strategy = strategy
        self._index = 0
        self._turn_count = 0
        self._last_spoke: dict[int, int] = {}  # agent.id → turn number

    def _effective_weight(self, agent: PersonaAgent) -> float:
        turns_since = self._turn_count - self._last_spoke.get(agent.agent.id, -999)
        if turns_since < agent.cooldown_turns:
            return 0.0
        return agent.dominance_weight

    def next(self) -> PersonaAgent:
        self._turn_count += 1
        if self.strategy == "round_robin":
            agent = self.agents[self._index % len(self.agents)]
            self._index += 1
            return agent
        weights = [self._effective_weight(a) for a in self.agents]
        return random.choices(self.agents, weights=weights, k=1)[0]

    def mark_spoke(self, agent: PersonaAgent) -> None:
        self._last_spoke[agent.agent.id] = self._turn_count
