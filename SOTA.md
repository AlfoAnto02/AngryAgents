# State of the Art: 
This document defines the current state of the art in multi-agent personality simulation using Large Language Models.
The goal is to analyze existing literature and discuss the research gaps and known failure modes that have to be addressed in the project.


## LLM-Based Dialogue Agents: Architecture and Known Failure Modes

Before examining persona-specific work, it is useful to frame the general architectural assumptions underlying any LLM-based agent. Wason et al. [2024] provide a synthesis of the state of practice in LLM dialogue agent design, identifying three functional components that all agents share: a **Brain** (the underlying LLM), a **Perception** layer (multimodal input processing), and an **Action** layer (text generation and tool use). From an engineering standpoint, any persona agent must instantiate all three.

On the training side, the dominant specialization technique remains **Instruction Tuning** (e.g., InstructGPT), which aligns models to follow instructions via RLHF, though at the cost of potentially overfitting to surface-level patterns and inheriting training-objective mismatches. Two failure modes flagged by Wason et al. [2024] are directly relevant to this project. First, dialogue success and response accuracy may diverge: an agent can produce fluent, topically accurate output while failing to behave as the target persona would. Second, **context management** is identified as a major unsolved challenge — a critical concern for persona agents that must maintain consistent character identity across multi-turn conversations and group interactions. Wason et al. [2024] also enumerate persistent open risks: hallucination, model bias, and societal harms. These risks are not merely theoretical; as this review shows below, they manifest empirically in persona simulation systems.


## In-Context Persona Prompting: Mechanisms and Systematic Effects

The foundational empirical question for this project is whether LLMs, when prompted to adopt a persona, actually change their behavior in measurable and systematic ways.

Using **in-context impersonation** prompts of the form *"If you were a {persona}"* (with no fine-tuning) applied to Vicuna-13B and ChatGPT (GPT-3.5-turbo), Salewski et al. [2023] test three task paradigms: a multi-armed bandit exploration/exploitation game, the MMLU reasoning benchmark, and a vision-language fine-grained classification task via CLIP-embedded descriptions.
However, Salewski et al. [2023] document a critical **bias problem**: persona prompts that specify demographic characteristics (race, gender) induce stereotyped behavioral patterns. White personas outperform Black personas on bird classification; woman personas outperform man personas on birds; man personas outperform woman personas on cars reflecting social stereotypes embedded in training data. ChatGPT shows larger bias effects than Vicuna-13B, attributed to broader fine-tuning data. 

This finding is a direct methodological warning for this project: if real-person persona prompts include demographic information, agents may respond to perturbations through the lens of demographic stereotypes rather than individual character consistency.

Critically, Salewski et al. [2023] test only **social category personas** (age, expertise, gender, race), not personas of specific real individuals extracted from text corpora. Their work establishes the mechanism; it does not validate it for the specific use case of individual-person simulation.


## Personality Expression: Psychometric Validation of LLM Persona Agents

The central evaluation challenge for this project is measuring whether an agent has truly internalized a persona.

Jiang et al. [2024] (PersonaLLM) address this challenge by applying the **Big Five Inventory (BFI)** — a validated psychometric instrument — to persona-conditioned LLMs. Their experimental design generates 320 personas per model (GPT-3.5-turbo and GPT-4), covering all 2^5 = 32 combinations of Big Five trait poles, each replicated 10 times, with a system prompt of the form: *"You are a character who is [TRAIT1, ..., TRAIT5]."* Each persona then completes the full 44-item BFI and writes an 800-word personal story under the instruction not to mention personality traits explicitly.

**On BFI self-assessment (RQ1),** GPT-4 achieves large, statistically significant effect sizes across all five traits: Extraversion d = 5.47, Agreeableness d = 4.22, Conscientiousness d = 4.39, Neuroticism d = 5.17, Openness d = 6.30 (all p < 0.001). This confirms that persona-prompted LLMs do reliably encode assigned trait profiles in their self-reported attitudes.

**On linguistic style (RQ2),** Jiang et al. [2024] apply LIWC-22 psycholinguistic analysis to 320 generated stories, computing point-biserial correlations between 81 features and binary personality assignments, then comparing the pattern against the Essays human corpus (Pennebaker & King, 1999; N = 2,467). GPT-4 shows substantially greater overlap with human personality-linguistic patterns than GPT-3.5: for Conscientiousness, 11/31 overlapping human LIWC correlations vs. only 1/31 for GPT-3.5; for Openness, 17/36 vs. 2/36. Trait-consistent patterns include: extroversion correlating with affiliation words and positive tone; neuroticism correlating with anxiety and negative-affect lexicons; openness correlating with curiosity-related vocabulary.

**On human perception accuracy (RQ4),** human raters asked to predict the assigned Big Five traits from persona-generated stories achieve majority-vote accuracies against a 0.5 binary chance baseline. Extraversion is by far the most robustly perceptible trait. Crucially, **informing raters that the author is an AI significantly reduces perceived personalness** and degrades personality prediction accuracy across all traits. This finding directly motivates the **blind evaluation protocol** in this project's experimental design: raters must not know whether they are reading AI-generated or human text.

A further methodological finding relevant to this project: GPT-4 as an automated rater shows strong self-preference, rating its own stories near maximum on all quality dimensions with near-zero variance. This self-evaluation bias means automated LLM-based fidelity assessment is not a neutral substitute for human raters.

The gap left by Jiang et al. [2024] is that all evaluated personas are **synthetic** (randomly assigned combinations of Big Five poles), not extracted from real individual text corpora. The transfer from synthetic to real-person persona grounding — the central challenge of this project — remains unaddressed.


## Behavioral Fidelity: Evaluating Real-Person Agent Authenticity

Moving from personality traits to behavioral authenticity whether an agent responds to real-world situations as the target individual would — 

Zhou et al. [2025] provide the closest existing work to the behavioral fidelity evaluation problem this project faces. Their methodology constructs agents for 35 real public figures (politicians) using profile data from Wikipedia and Twitter/X, and evaluates agent responses against the figures' actual tweets in response to real-world news events, using the **RWERD (Real-World Events Responses Dataset)**. Event attitudes are labeled Positive, Neutral, or Negative by eight annotators (majority vote), providing a ground-truth signal for comparison.

The agent construction follows a **three-step prompting workflow**: (1) generate a structured representation of the target person's beliefs, values, and personality traits from the profile; (2) deepen this representation with historical positions and past actions relevant to the event; (3) add emotional authenticity. **Retrieval-Augmented Generation (RAG)** via FAISS similarity search grounds agents in relevant event context, compensating for context window limitations.

The central finding concerns the **impact of profile completeness** on behavioral fidelity. Five experimental conditions vary what information is provided (name + public office + personal details + basic political position, and subsets thereof). Results (averaged across 5 repetitions) show:

| Profile Condition | GPT-4o Accuracy | Llama-3-70B Accuracy |
|---|---|---|
| Full profile (NPPB) | 69.0% | 82.6% |
| No basic position (NPP) | 69.4% | 82.8% |
| No personal details (NPB) | 63.4% | 81.2% |
| Name only (N) | 48.8% | 69.2% |
| Basic position only (MC) | 54.6% | 69.4% |

**Personal detail features are the most critical driver of fidelity:** removing them causes the largest accuracy drop and increases variance. This has direct implications for this project's persona extraction desig, highlighting that the granularity and type of information extracted from source text corpora (beyond surface style) is the single most influential factor for downstream behavioral fidelity.

A secondary finding is that **GPT-4o produces systematically more neutral outputs** compared to Llama-3-70B, attributed to GPT-4o's Mixture-of-Experts architecture tending toward cautious, balanced responses. After a prompt intervention instructing the model not to choose neutral unless certain, GPT-4o NPPB accuracy jumps from 69.0% to **83.4%**, bringing it in line with Llama-3-70B. This model-specific conservatism is a key methodological caveat: when measuring perturbation responses, the LLM's own bias toward neutrality may systematically suppress directional character-consistent reactions, independent of persona quality.

The limitation of the study is that behavioral fidelity is evaluated on a **single-dimension outcome** (positive/negative/neutral stance) and does not capture stylistic fidelity, multi-turn consistency, or group-level interaction dynamics.


## Multi-Agent Social Simulation and Group Dynamics

The most architecturally sophisticated work on multi-agent personality simulation is Park et al. [2023] (Generative Agents), which addresses the problem that raw LLM prompting is insufficient for long-term coherent agent behavior because it cannot manage growing memories, perform higher-order inference, or plan consistently over time.

Their architecture introduces three modules on top of a base LLM (GPT-3.5-turbo):

1. **Memory Stream:** A database of timestamped natural-language observations. Memory retrieval is scored by a weighted combination of Recency (exponential decay, γ = 0.995 per hour), Importance (LLM-rated poignancy score 1–10), and Relevance (cosine similarity of embeddings): Score = α_recency · Recency + α_importance · Importance + α_relevance · Relevance (all α = 1). This grounds each agent response in the most pertinent subset of its accumulated history.

2. **Reflection:** When accumulated importance scores exceed a threshold (150 points), agents synthesize recent memories into higher-level abstract insights ("reflection trees"), enabling longer-term coherence and personality-consistent behavior without relying solely on token-window context.

3. **Planning:** Agents generate recursive daily plans (broad strokes → hourly → 5–15 minute chunks), stored in the memory stream and updated reactively to circumstances, providing a backbone for consistent goal-directed behavior.

The system is validated in two ways. In a **controlled interview evaluation**, 100 Prolific crowdworkers rank the believability of five conditions (full architecture, three ablations removing modules in order, and a human crowdworker baseline) on five question categories. Using TrueSkill rating, the full architecture (μ = 29.89) significantly outperforms all ablations and even the human crowdworker baseline (μ = 22.95), with the fully ablated baseline (prior state of the art without any memory) scoring lowest (μ = 21.21). The effect size between full architecture and no-memory baseline is Cohen's d = 8.16 — a very large effect that validates the memory architecture's contribution. All pairwise comparisons are significant (p < 0.001) except the non-significant crowdworker vs. fully-ablated pair.

In the **end-to-end evaluation**, 25 agents with fictional seed identities are placed in a simulated village ("Smallville") and allowed to run freely for two game days. The system produces emergent social behaviors without explicit programming: information about a mayoral candidacy diffuses from 1 agent (4%) to 8 (32%), party invitations spread from 1 (4%) to 13 (52%), and social network density increases from 0.167 to 0.74. Only 1.3% of agent-awareness responses (6/453) contain hallucinated information. These **group-level dynamics metrics** — information diffusion rates, network density, coordination rates — are the most concrete existing proposals for measuring group fidelity and are directly applicable to this project's H2 hypothesis (turn-share Gini, sentiment divergence, interaction network statistics).

Park et al. [2023] also document important **failure modes** that this project must anticipate:

- **Memory retrieval failures:** agents sometimes fail to surface relevant memories, producing character-inconsistent responses.
- **Hallucinated embellishments:** agents add plausible but factually false details (e.g., fabricating future events from partial information).
- **Instruction-tuning side effects:** agents exhibit overly formal dialogue and excessive agreeableness, rarely declining requests which doesn't take account for individual personality differences.
- **Spatial norm errors:** agents violate commonsense situational constraints.

The critical gap of Park et al. [2023] for this project is that all 25 agents are **fictional** with synthetic seed memories no agent is grounded in a real person's textual corpus. The architecture is transferable, but the extraction pipeline that maps a real person's text to the memory-stream seed format must be built from scratch. Additionally, no psychometric personality framework is used, making it difficult to characterize or measure the personality space being explored.


## Evaluation Methodologies: A Cross-Paper Synthesis

Taken together, the five reviewed works converge on a set of evaluation approaches relevant to each of this project's four fidelity dimensions.

**Individual fidelity (style)** can be assessed through:
- Psychometric self-assessment: BFI administered to the agent, compared to a target profile [Jiang et al., 2024]
- LIWC-based psycholinguistic profiling: point-biserial correlations between persona-assigned traits and linguistic features in generated text [Jiang et al., 2024]
- Text complexity metrics (grade-level readability), which Salewski et al. [2023] show shift systematically with persona characteristics

**Individual fidelity (behavioral)** can be assessed through:
- Event-driven response comparison: agent stance on real events compared to ground-truth human responses [Zhou et al., 2025]
- Interview-style probing across five dimensions (self-knowledge, memory, plans, reactions, reflections), evaluated by blind raters using TrueSkill [Park et al., 2023]
- Blind multi-choice identification: raters presented anonymized snippets attempt to identify the source persona [this project's headline hypothesis; closest proxy in Jiang et al., 2024's RQ4]

**Group fidelity** can be assessed through:
- Information diffusion rate across agents [Park et al., 2023]
- Social network density evolution over interaction time [Park et al., 2023]
- Turn-share Gini coefficient and sentiment divergence across persona pairs [this project's H2]
- Coordination rate on shared tasks [Park et al., 2023]

**Perturbation response** has no direct precedent in the reviewed literature. The closest analog is:
- Zhou et al.'s [2025] event-driven evaluation, which tests stance on real-world events but restricted to a single-dimension output.
- Park et al.'s [2023] reactive plan updates and "reactions" interview question category, targeting fictional agents only.
- Salewski et al.'s [2023] bandit task as an implicit perturbation-response scenario (changing reward probabilities).

This constitutes the clearest **gap** in the existing literature: no prior work evaluates whether persona-conditioned LLM agents respond to counterfactual event injections in a direction predictable from the seed person's known positions.


## Open Problems and Research Gaps

Mapping the covered literature onto the project's specific claims reveals the following open problems:

1. **Real-person corpus extraction:** No existing work proposes a systematic, validated method for extracting a structured persona representation from a raw text corpus of a real individual. Zhou et al. [2025] use Wikipedia summaries and Twitter timelines as pre-structured sources; Jiang et al. [2024] use synthetic trait assignments. The extraction pipeline (`extract_persona.py`) in this project — whether few-shot prompted, embedding-based, or fine-tuned — has no validated baseline to compare against.

2. **Individual-level vs. group-level persona:** Park et al. [2023] demonstrate group-level emergent dynamics but with fictional agents. No work validates that real-person-grounded agents produce group dynamics that resemble the real group's dynamics, let alone proposes a metric for that comparison.

3. **Personality + behavioral + group fidelity in a unified framework:** Each reviewed paper addresses at most one or two of the four fidelity dimensions. Jiang et al. [2024] covers personality and style; Zhou et al. [2025] covers behavioral stance; Park et al. [2023] covers believability and group dynamics. The integration of all four in a single experimental pipeline, grounded in real-person corpora, is the novel contribution of this project.

4. **Perturbation response as a falsifiable hypothesis:** The finding that LLMs tend toward neutral/conservative outputs [Zhou et al., 2025] and excessive agreeableness [Park et al., 2023] suggests that perturbation response measurement will require careful prompt design to avoid systematically suppressing directional responses before persona-specific differences can be observed.

5. **Bias and default-voice leakage:** Salewski et al. [2023] document that demographic persona prompts induce stereotyped biases. The complementary failure mode is *default-voice leakage* — where all persona agents sound like the LLM's generic fine-tuned output rather than like distinct individuals. The style-scrubbed control planned in this project's experimental design directly tests for this, as acknowledged by the project specification.

6. **Blind evaluation and demand characteristics:** Jiang et al. [2024] demonstrate that informing raters of AI authorship significantly reduces perceived personalness and personality attribution accuracy. This establishes an empirical rationale for the blind rater protocol in this project's headline hypothesis — and implies that non-blind evaluations would systematically underestimate agent fidelity.


## References

Jiang, H., Zhang, X., Cao, X., Breazeal, C., Roy, D., & Kabbara, J. (2024). **PersonaLLM: Investigating the Ability of Large Language Models to Express Personality Traits.** *Proceedings of the Annual Meeting of the Association for Computational Linguistics (ACL)*. arXiv:2305.02547.

Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., & Bernstein, M. S. (2023). **Generative Agents: Interactive Simulacra of Human Behavior.** *Proceedings of the 36th Annual ACM Symposium on User Interface Software and Technology (UIST '23)*. ACM. https://doi.org/10.1145/3586183.3606763

Salewski, L., Alaniz, S., Rio-Torto, I., Schulz, E., & Akata, Z. (2023). **In-Context Impersonation Reveals Large Language Models' Strengths and Biases.** *Advances in Neural Information Processing Systems (NeurIPS 2023)*. arXiv:2305.14930.

Wason, R., Arora, P., Arora, D., Kaur, J., Singh, S. P., & Hoda, M. N. (2024). **Appraising Success of LLM-based Dialogue Agents.** *Proceedings of the 11th International Conference on Computing for Sustainable Global Development (INDIACom 2024)*. BVICAM / IEEE Xplore. 978-93-80544-51-9/24.

Zhou, J., Jiang, B., Gong, R., & Jiang, H. (2025). **Evaluating LLM-based Role-playing Agent Authenticity via Event-driven Response Simulation: A Benchmark on Real-World Events Responses.** *Proceedings of the 2nd International Symposium on AI and Cybersecurity (ISAICS 2025)*. IEEE. DOI: 10.1109/ISAICS66888.2025.11350200.
