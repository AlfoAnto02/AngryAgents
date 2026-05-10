# Problem definition

The project's objective is to create a chat appplication in which a user can chat with agents that represent real-world personas.
The application permits the user to write direct messagges to agents or to chat in group with them. The agents' behaviour is supervised and evaluated by 
AI judges. 

In detail:
- Personas should be extracted from material present on the web. The target personas can be fictional characters from books, movies, TV series;
real world persona, like politicians, influencers; philosophers and intelectuals from the past. 
- The application permits two different type of conversation:
    + *DM messages*: the user can write direct messagges to one agent that represent one of the available personas.
    + *Group chat*: the user can chat in group with some persona-agents (for example, 8 agents). Different chat topics can be choosen. 
- Use then **20 judges** to evaluate the chat based on different criterias:
    
    + *Persona identification*: the judges should be able to identify which of the persona defined has sent the messagges in chat;
    
    + *Individual fidelity*: each agent in the chat is evaluated by the fidelity of the messagges sent, based on the persona
    that it represents;

    + *Group fidelity*: the agents are evaluated based on how they behave on a group situation;

    + *Behavioural fidelity*: the agent is evaluated based on the ability of behave like an human in the chat.

The judges don't evaluate same aspects of the personas: some evaluate style, other ideology, ... While others pursue a general analysis. This has been thought to be able to evaluate different aspects with different focus.
 The judging  has different phases: 
1. Each judge give its own evaluation on the aspects previously indicated.
2. In the next phase, the evaluation of each judge are given as context to the others and the judge agents collaborate to produce final commmon evaluation.

## What type of personas ? 

Like said previously, one important point is to define the type of persona that we're gonna use. We thought of focusing
on two main types:
- **Fiction persona**: these are created from books, movies or TV series. While the task could be considered trivial, the problem is to extract a good personality from relatively scarse resources (the character selected can have very few lines).
- **Real world personas**: in this case, the persona is built from podcast transcripts, by which many information on the person can be retrieved, as well as his style of conversation. In this case, the challenge relies on the fact that persona hideology and beahviour can be more difficult to extract. 

Related to the group chat case, an interesting aspect is represented by how the agent behave with different topics:
- **Same topic**: the personas in the group are from same field of interest (politics, sport, entertainment).
- **Different topic**: the personas choosen are from different fields. In this case, is of relevant interest to analyze how group dinamic evolve.

## How do evaluation on judges work ? 

Another problem is to evaluate judges evaluation. While for the *persona identification* problem we can use ground truth data, for the fidelity, we don't have data to state if judging is good or not. To address this problem, we tought to implement an **External omniscent agent**, which have full context of personas involved in the chat, chat messages and jusges evalutation, and based on all information is able to evaluate the quality of judging process, indicating also the areas of improvement for the evaluation process. 

## User experience

One user can authenticate as:
- **Common user**: the user can use the application, chat with agents and manage its conversations. 
- **Admin user**: the user can admin the available personas and also see judges evaluation on past chats between users and AI-personas. 


## Out-of-scope topics
- The aim of the project is **not** to train a model: the working pipeline uses calls to model's API to make agents work.