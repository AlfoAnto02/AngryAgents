# Experimentation pipeline
This document defines the experimental methodology that will be used to evaluate the system.
The goal is to analyze and discuss the problems that have to be adressed in each stage.

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

## In depth analysis: Group Chat Simulation
Eight agents are instantiated, each conditioned on one persona profile. 
The simulation needs to run long enough to show persona characteristics, especially subtle behavioral patterns, but not so long that context windows fill up and agents drift... a reasonable target needs to be defined.
So, we think that an important part of this stage is how to keep the constext window reasonable by using and testing different types of techniques (e.g history truncation).

As the conversation progresses, the agent must balance two competing pressures: maintaining coherence with the persona profile and maintaining coherence with the recent conversation history. In long conversations, the second pressure tends to dominate. The agent begins to "follow the flow" of the conversation rather than maintain its distinctive character traits. This is particularly problematic if other agents are converging toward consensus or a common tone our agent might start imitating them rather than preserving its unique style.

This creates a tension in experimental design. If the conversation is too short (say, 15-20 turns), we might not see deep behavioral patterns emerge. Superficial differences like vocabulary and tone appear immediately, but more complex patterns—how a character handles prolonged disagreement, reacts to being repeatedly ignored, or evolves (or doesn't evolve) during a debate require time to manifest. If the conversation is too long (say, 150+ turns), agents may have already "forgotten" who they're supposed to be, making it impossible to distinguish whether a behavior reflects the original persona or simply conversational inertia. We have to find a compromise.

## Phase One (judge): Independent Judge Evaluation
Twenty judge-agents receive the conversation transcript and persona descriptions.
These judges aren't identical, they specialize into three types (or others that we will define): style-focused, ideology-focused, and general. 
This reflects that persona fidelity isn't unique, but it is a bundle of different qualities requiring different attention.

Each judge completes four tasks. First, persona identification: given anonymized messages, guess which persona wrote each one.
Second, individual fidelity scoring: rate each persona on a scale for how faithful the agent's messages were to the profile. This is subjective, requiring multiple judges.
Third, group fidelity assessment: does the conversation show realistic social dynamics? Do agents fall into recognizable roles? Do agreement patterns make sense given the personas?
Fourth, behavioral fidelity: setting aside specific personas, does the conversation read as human-produced, or does it show LLM artifacts like excessive politeness or unnatural consensus-seeking?.

All twenty judges work independently during this phase. They don't see what other judges said. This independence is important because it lets us measure genuine agreement between judges rather than just copying each other's answers. The output from the first phase of the judge stage is twenty separate evaluation datasets, one from each judge, containing their identification guesses, fidelity ratings, and assessments.

## Phase Two: Collaborative Judge Evaluation

Phase One produces independent judgments with unavoidable variance. Some variance reflects genuine ambiguity in the material—cases where reasonable evaluators could legitimately disagree. Other variance reflects individual judge limitations—mistakes, misreadings, or blind spots that a single judge working alone might not catch. Phase Two attempts to reduce error variance through structured deliberation while preserving the signal from genuine ambiguity.

The system first identifies cases with high disagreement from Phase One. These include messages where judges were split in identifying the persona, where fidelity ratings varied widely, or where interpretations of group dynamics conflicted. Only these cases move to deliberation, since they signal either meaningful ambiguity or possible evaluation errors.

For each selected case, judges participate in a structured debate. Judges who gave high fidelity ratings explain the evidence supporting their view, while those who gave low ratings point out inconsistencies or failures. Other judges can add observations, cite specific messages, or highlight factors that may have influenced the evaluation. The process follows a clear protocol, focusing on evidence and reasoning rather than opinion.

Deliberation serves several purposes. Practically, it can improve accuracy by allowing judges to catch mistakes or notice patterns others missed. For example, one judge might identify a subtle ideological consistency, while another might explain stylistic features that initially seemed off-persona. In this way, the process combines perspectives that were previously isolated.

More fundamentally, deliberation tests whether consensus is achievable. If judges remain divided even after discussion, this suggests that some aspects of persona evaluation are inherently subjective. By contrast, cases where judges converge indicate areas that can be evaluated more reliably. This helps define the limits of the evaluation system.

The process typically unfolds over three to five rounds. After each round, judges can revise their ratings. The system tracks how ratings change and measures variance at each stage. A decrease in variance suggests convergence and effective deliberation. Stable variance indicates persistent disagreement, while increasing variance signals confusion and potential issues with the process.

The final result is a set of consensus scores. These may be simple aggregates, such as median ratings after the final round, or weighted combinations that give more importance to judges who showed consistency, provided strong justifications, or anticipated convergence. The key goal is to compare these Phase Two results with Phase One ratings to determine whether deliberation improved evaluation quality or introduced new biases.

A crucial component is tracking judge confidence alongside ratings. Judges report how confident they are in their evaluations. Ideally, deliberation should increase confidence in cases where agreement is reached, while preserving uncertainty in ambiguous cases. If confidence rises while accuracy declines, this indicates overconfidence and a flawed process. However, if confidence increases only where convergence occurs and remains low where disagreement persists, the system is functioning as intended.

## Failure Modes and Mitigations

| Problem | Mitigation and Approach |
|--------|------------------------|
| Judge unfamiliarity | Validate judges before evaluation using known persona samples. Flag low-performing judges and analyze their results separately to assess impact. |
| Overfitting to source material | Test agents on topics not present in the original corpus. Evaluate whether persona consistency holds in new contexts. |
| Ethical risks | Prefer fictional or historical personas. Clearly label all outputs as AI-generated and avoid publishing raw transcripts that could be misused. Document safeguards when real individuals are included. |
| Time constraints | Use staged implementation. Start with a minimal system, validate core methods first, and add complexity only if time allows. |
| Low statistical power | Pre-register analyses, distinguish primary vs exploratory results, and report confidence intervals. Interpret findings conservatively. |
| Budget limits | Estimate costs in advance, run small pilots, and optimize model usage. Set a fixed budget and design within it. |
| Poor persona extraction | Manually review extracted personas for coherence and distinctiveness. Ensure alignment with source material before proceeding. |
| Information leakage | Control access to data during evaluation and deliberation. Track what each judge sees and prevent exposure to hidden information. |

The goal is not to eliminate all risks but to manage them so results remain reliable and interpretable.