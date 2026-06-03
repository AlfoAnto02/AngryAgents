# Final Week Plan

## Goal of the last week

During this final week, our main objective is to turn the current prototype into a polished, fully working system and to prepare a clear, hand-crafted presentation that tells the story of how the project evolved, what problems we faced, and how we solved them.  
The work should focus on both technical completion and communication quality, with the presentation being as important as the implementation itself.

## Main technical goals

### 1. Full MCP integration
The top priority is to implement MCP end-to-end so that an AI can interact with the application exactly like a user and access all available features.  
This means the model should not be limited to isolated actions, but should be able to navigate the app, trigger actions, read outputs, and behave like a real participant in the system.

### 2. UI completion and polish
We should finish the user interface and make it consistent and usable across the whole app.  
The requested changes include:
- switching to a white background version,
- increasing the font size,
- making every button functional,
- improving overall visual clarity and accessibility.

### 3. Chat improvements
The chat experience needs to be fixed and refined.  
The main tasks are:
- adding a pause button for the group chat,
- fixing the bug that currently prevents scrolling upward in the chat history,
- making the interaction smoother and more stable during long conversations.

### 4. Metric cleanup
We need to fix and validate all the metrics related to individual fidelity and group fidelity.  
These metrics should be reliable, readable, and consistent with the final evaluation story, because they are one of the clearest ways to demonstrate the quality of the system.

## Optional but important goals

### 5. Prefiltering experiments
The professor asked us to test how changing the prefiltering phase affects the final evaluation.  
A good experiment would be to vary the number of candidate sets shown to the judges and compare how the metrics change.  
This can help us understand the trade-off between retrieval quality, judge workload, and final accuracy.

### 6. Group chat awareness
Another requested improvement is to make the agents aware of the people they are interacting with inside the group chat.  
This should make the interaction more realistic and improve coherence in the conversation dynamics.

### 7. Deliberation phase
If time allows, we should implement deliberation and study how it changes the final accuracy.  
This would be a valuable extension because it can show whether a second reasoning pass helps the judges resolve difficult cases and improve the final output.

## Presentation goals

The presentation must be built carefully by hand, not as a rushed summary.  
It should be short, around 10 slides total, so that each team member can present about 2 slides.  
The structure should focus on storytelling: start from the initial problem, explain how we approached it from the beginning, describe the main obstacles, and show the experiments we tried before reaching the current solution.

### What the presentation should contain
- The initial problem and why it was challenging.
- The first design choices and how the project started.
- The main technical issues we encountered.
- The experiments and iterations we ran.
- The final architecture and what improved over time.
- The remaining open questions and future work.

### What the presentation should avoid
- Too much text on each slide.
- A long and flat technical explanation with no narrative.
- A presentation that looks auto-generated or too dense.
- Jumping directly to the solution without explaining the path that led there.

### Suggested storytelling angle
A strong narrative could be:
1. We started with a difficult multi-agent evaluation problem.
2. We identified bottlenecks in chat quality, retrieval, metrics, and usability.
3. We tested different solutions and refined the pipeline step by step.
4. We improved the system through experimentation and debugging.
5. We ended with a more robust architecture and a clearer evaluation framework.

This kind of structure should make the presentation more convincing and easier to follow.

## Suggested work strategy

### Priority order
1. Finish MCP integration.
2. Fix the UI and chat bugs.
3. Validate and clean up the metrics.
4. Run optional experiments if time remains.
5. Build the final presentation only after the technical story is stable.

### Practical approach
- Divide the week into small technical milestones.
- Keep a shared checklist of unfinished items.
- Freeze the core implementation early enough to focus on slides.
- Collect screenshots, metrics, and short notes while coding, so the presentation can be built from real evidence instead of memory.
- Use the presentation to explain decisions, not just results.

## Final week outcome

By the end of the week, the project should be in a state where:
- the AI can truly interact with the app through MCP,
- the UI is complete and polished,
- the chat behaves correctly,
- the fidelity metrics are trustworthy,
- the optional experiments are at least partially explored,
- the presentation tells a clear and professional story of the entire project journey.
