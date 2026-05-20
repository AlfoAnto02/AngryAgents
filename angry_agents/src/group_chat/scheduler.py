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

    def next(self) -> PersonaAgent:
        if self.strategy == "round_robin":
            agent = self.agents[self._index % len(self.agents)]
            self._index += 1
            return agent
        weights = [a.dominance_weight for a in self.agents]
        return random.choices(self.agents, weights=weights, k=1)[0]

    def mark_spoke(self, agent: PersonaAgent) -> None:
        pass
