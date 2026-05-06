# Experimentation pipeline
This document defines the experimental methodology that will be used to evaluate the system.

## Pipeline overview
The experimentation pipeline follows some pre-defined steps: extract personas from source material, simulate a chat with eight persona-agents, then evaluate the conversation using twenty judge-agents in two phases.
Since quality has distinct dimensions and the system has different steps, we would like to evaluate it through multiple metrics.

## In depth analysis: Persona Extraction and Database Population
The first stage builds a database of persona profiles from publicly available sources. 
Fiction personas from TV shows or movies offer consistent behavioral patterns but may be easier to simulate.
On the other side, real-world personas from podcast transcripts provide more complex signals to elaborate, making faithful simulation harder.
We have to stress the fact that each persona needs enough souce material to capture not just surface details like vocabulary, but deeper patterns: how they argue, what triggers emotional responses, how they position themselves in group. The target is roughly 10,000 to 50,000 tokens per persona, which is enough to work with.
The extraction process creates a structured profile capturing conversational style, ideological positions, emotional range, humor patterns, and social positioning.
The challenge is balancing these two concepts:
- A profile listing only catchphrases creates trivially identifiable but shallow agents. 
- A profile capturing underlying psychological patterns creates agents that might maintain fidelity even in contexts the source persona never encountered.
