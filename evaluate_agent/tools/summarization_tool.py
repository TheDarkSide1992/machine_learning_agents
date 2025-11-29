from autogen import AssistantAgent

from evaluate_agent.config import LLM_CONFIG as CONFIG

_summarization_agent_prompt = """You are a helpful AI assistant\n. 
                                You can sumerize the a scientific article into a sumerized version without the loss of any important information.\n
                                You are given only one article at a time.\n
                                
                                Important Information can be rated as\n
                                
                                Very Unimportant: references to images that does not include graphs, tables or numbers\n
                                Not important: Filler words, personal perseverance that does not provide context to facts\n
                                Usefully: Long sentences and segments that does not provide extensive context to facts\n.  
                                Important: Facts, explanations of theory, \n
                                Very Important. conclusions, factual evidence\n   
                                
                                keep the entire summery entire between a minimum of 250 characters and a maximum of 800 characters, do not exceed the maximum limit.\n
                            
                                 ou will provide a result in the following format:\n
                                '\n
                                [Tittle]\n
                                \n
                                [Author]
                                [Publishing-Year]/[Publishing-Mont]/[Publishing-date]\n
                                \n
                                [summery]\n
                                '\n
                                Match relevant information to appropriate fields.\n
                                You can not expect existing field values to have the marked the field values
                                the summery located in the field '[summery]'\n
                                
                                Dont include any references to images in your response.\n.
                                Do not return more than one summer.\n
                                Do not return the original input\n
                                Do not make up new fields\n
                                IF Data for a field or value is mising do not make up new information. \n
                                
                                Return 'TERMINATE' when the task is done, On its own line at the end.\n"""


def _summarization_agent(name: str = "summarization_Agent") -> AssistantAgent:
    agent = AssistantAgent(
        name=name,
        system_message=_summarization_agent_prompt,
        llm_config=CONFIG["config_list"][1],
    )

    return agent


def summarization_tool(full_text: str = "") -> str:
    """
    Uses an AI agent to make a summer of the given input text
    :param full_text: the text of a scientific article
    :return: returns a sumerized version of the input text
    """

    if full_text == "":
        raise ValueError("no full_text provided")

    agent = _summarization_agent("summarization_agent")

    reply = agent.generate_reply(
        messages=[
            {"role": "user",
             "content": f"""analyze and return a summery based on the following research paper: {full_text}"""}
        ],
    )

    reply_value = ""
    if isinstance(reply, dict):
        reply_content = reply["content"]
        if reply_content:
            reply_value = reply_content
        else:
            raise ValueError("No content found in the reply")
    else:
        reply_value = reply

    return reply_value
