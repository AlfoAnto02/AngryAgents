# Problem definition

The project's objective is to create a chat between different agents, which have pre-defined personas, and then 
use judge-agents to evalutate the persona-agent reply.

In detail:
- Personas should be extracted from material present on the web. Some examples are fiction personas
from Movies and TV series or real world personas by scraping podcast transcripts. The persona behaviour 
shpuld then be saved in the database.
- Create **8 agents** which have different personas chosen from the database previously built. Then make them chat
togheter in a group chat and save the messages on the database.
- Use then **20 judges** to evaluate the chat based on different criterias:
    
    + *Persona identification*: the judges should be able to identify which of the persona defined has sent the messagges in chat;
    
    + *Individual fidelity*: each agent in the chat is evaluated by the fidelity of the messagges sent, based on the persona
    that it represents;

    + *Group fidelity*: the agents are evaluated based on how they behave on a group situation;

    + *Behavioural fidelity*: the agent is evaluated based on the ability of behave like an human in the chat.

The judges don't evaluate same aspects of the personas: some evaluate style, other ideology, ... While others pursue a general
analysis. This has been thought to be able to evaluate different aspects with different focus.
- The judging phase has different phases: in the first phase, each judge analyze and score individually the chat on the criterias previously indicated. Then, the judges compare their evaluations and try to improve the general accuracy of the system; they finally produce unique score based on their discussion.


## Out-of-scope topics
- The aim of the project is **not** to create an app: the UI implemented is basic and is needed only to visualize clearly the 
chat between the agents and to understand judges evaluation;
- The aim of the project is **not** to train a model: the working pipeline uses calls to model's API to make agents work.