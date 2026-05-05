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
    @ *Persona identification*: the judges should be able to identify which of the persona defined has sent the messagges in chat;
    @