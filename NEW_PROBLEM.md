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
- The judging  has different phases: in the first one, each judge analyze and score individually the chat on the criterias previously indicated. Then, the judges compare their evaluations and try to improve the general accuracy of the system; they finally produce unique score based on their discussion.

## What type of personas ? 

Like said previously, one important point is to define the type of persona that we're gonna use. We thought of focusing
on two main types:
- **Fiction persona**: these are created from movies or TV series scripts. While the task could be considered trivial, the problem 
id to extract a good personality from relatively scarse resources (the character selected can have very few lines).
- **Real world personas**: in this case, the persona is built from podcast transcripts, by which many information on the person can be retrieved, as well as his style of conversation. In this case, the challenge relies on the fact that persona hideology and beahviour can be more difficult to extract. 

Another interestic aspect to analyze is to evaluate the agents behaviour when they have different background: for example, how well do one agent from a politician field and one from a sport field interact with each other. To evaluate so, we decided to run different situations tests:
+ **Same topic**: the eight agents are built upon personas that came from sape area of interest (politics, sport, TV shows, ...).
+ **Different topic**: the personas of reference for the eight agents come from different background.

## How do evaluation on judges work ? 

Another problem is to evaluate judges evaluation. While for the *persona identification* problem we can use ground truth data, for the fidelity, we don't have data to state if judging is good or not. To address this problem, we tought to implement an **External omniscent agent**, which have full context of personas involved in the chat, chat messages and jusges evalutation, and based on all information is able to evaluate the quality of judging process, indicating also the areas of improvement for the evaluation process. 


## Out-of-scope topics
- The aim of the project is **not** to train a model: the working pipeline uses calls to model's API to make agents work.