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

## Phase Two (judge): Collaborative Judge Evaluation

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

## Measuring Quality: Metrics and Statistical Framework

Quality isn't a single number. We measure multiple dimensions of simulation success, and each measurement carries statistical uncertainty that we must quantify.

### Persona Identification Accuracy

We count how many messages judges correctly match to their source persona and calculate a success rate. With eight personas, random guessing gives **12.5% accuracy** (totally random, our baseline). The question is whether we observe significantly better performance.

Suppose twenty judges each evaluate thirty messages (600 total attempts). If we see 210 correct identifications, that's 35% accuracy. But this is a point estimate from our sample, not the true underlying rate. We need confidence intervals to show the uncertainty.

Using a **binomial exact test**, we get a **95% confidence interval**. For 210/600 successes, the interval might be 31% to 39%. This means we're 95% confident the true accuracy lies in that range. Narrow intervals indicate precise estimates; wide intervals indicate more uncertainty.

The statistical test asks: could we observe 210 successes if the true rate were just 12.5%? We compute a p-value measuring how unlikely this would be under random guessing. If p < 0.05, we reject chance performance and conclude agents produce distinguishable outputs. But the confidence interval is often more informative than the **p-value** alone—it shows the range of plausible values, not just whether we beat baseline.

The **confusion matrix** reveals structural patterns. This 8×8 table shows which personas judges confuse with which. If Persona A often gets mistaken for Persona C but rarely for Persona F, that tells us where the simulation struggles. We can test whether confusion patterns differ from random errors using chi-square tests. Systematic confusion between specific pairs suggests they're genuinely similar in simulation output, whether due to source material overlap or extraction failures.

### Individual Fidelity Scores

Judges rate each persona's fidelity on a 1-5 Likert scale. With twenty judges and eight personas, we collect 160 ratings. For each persona, we have twenty ratings to summarize.

We use the **median** as our primary statistic, not the mean. Medians resist outliers, one extreme rating doesn't distort the summary. If fifteen judges give 4, three give 5, and two give 1, the median is 4, reflecting the majority view. The mean would be pulled toward the outlier 1s.

The **interquartile range (IQR)** measures disagreement. It captures the spread of the middle 50% of ratings. If the 25th percentile is 3 and the 75th is 5, the IQR is 2. Narrow IQR means judges agree; wide IQR means substantial disagreement.

We also compute **variance** and **standard deviation**. High variance indicates judges have fundamentally different assessments. Low variance indicates convergence. These measures reveal whether fidelity is objectively measurable or inherently subjective for each persona.

We can check whether judge specialization works by comparing agreement within and across types. Style judges should agree more with each other on style metrics than with ideology judges. If we don't see this pattern, specialization isn't working.

### Group Fidelity Metrics

Group fidelity combines automated metrics with judge assessments.

**Turn distribution via Gini coefficient.** The Gini coefficient measures inequality in distributions. For conversation turns, Gini = 0 means perfect equality (all agents speak equally), Gini = 1 means total inequality (one agent dominates). We compute Gini for our simulation and compare it to real group conversations if available.

Suppose simulated Gini is 0.35, while real conversations range from 0.28 to 0.42 with mean 0.33 and standard deviation 0.05. Is our simulation within expected bounds? We use bootstrap methods: repeatedly sample from real conversation data, compute Gini for each sample, build a distribution of plausible values. If simulated Gini falls in the 95% bootstrap interval, we have evidence the simulation matches real patterns.

**Sentiment divergence between agents.** We embed each agent's messages using sentence transformers and compute pairwise cosine distances, creating an 8×8 matrix. We compare this to a similar matrix from real conversations using **Spearman's rank correlation**. Spearman is appropriate because we care about rank ordering of distances, not absolute values. If agents who should oppose each other ideologically show high sentiment distance in both real and simulated data, Spearman correlation will be high. We report the coefficient with confidence intervals, using bootstrap to estimate uncertainty.

Judge assessments of group fidelity use ordinal scales. We collect twenty ratings and compute medians and IQRs. We track which specific features judges comment on and whether comments converge or diverge.

### Phase Two Deliberation Metrics

Deliberation produces additional metrics we analyze statistically.

**Variance reduction across rounds.** We track variance in ratings or identification choices at each round. Round 0 is Phase One (pre-deliberation), Rounds 1-3 are deliberation. We plot variance evolution and test whether reduction is significant using F-tests comparing variances between rounds.

**Convergence rate.** What fraction of high-disagreement cases showed variance reduction? We report this as a proportion with binomial confidence intervals. If 11 of 15 cases converged, that's 73% with a confidence interval roughly 48% to 90%. The wide interval reflects our small sample—we can't precisely estimate convergence rates with only 15 cases.

**Confidence calibration.** For each judge and case, we track confidence ratings alongside judgments. After deliberation, we compare confidence changes to accuracy changes. We compute correlations between the deltas. Positive correlation means judges appropriately increase confidence when improving accuracy. Negative correlation is a red flag—judges becoming more confident while getting worse.

We can also build calibration curves. Group judgments by confidence level (1-5) and compute actual accuracy within each group. Well-calibrated judges show accuracy increasing with confidence—level 5 judgments should be more accurate than level 1. Overconfident judges show flat or inverted patterns.

### Bootstrap Methods for Small Samples

Many analyses involve small samples where normal approximations might fail. With only eight personas or twenty judges, standard formulas can be unreliable. Bootstrap resampling provides a non-parametric approach to estimate confidence intervals and test hypotheses.

Bootstrap works by repeatedly resampling observed data with replacement. To estimate uncertainty around median individual fidelity:
1. Start with twenty observed ratings
2. Draw 20 ratings randomly with replacement (some appear multiple times, others not at all)
3. Compute the median of this bootstrap sample
4. Repeat 10,000 times
5. The distribution of 10,000 bootstrap medians approximates the sampling distribution
6. The 2.5th and 97.5th percentiles give a 95% confidence interval

Bootstrap works without knowing the underlying distribution and doesn't require large samples for validity (though very small samples like n=5 still give wide intervals). We can use bootstrap for correlation coefficients, variance comparisons, or any statistic where traditional formulas don't fit our sample size.
