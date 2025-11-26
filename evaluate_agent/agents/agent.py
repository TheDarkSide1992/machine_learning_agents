from autogen import UserProxyAgent
from evaluate_agent.config import LLM_CONFIG as CONFIG
from evaluate_agent.tools import make_get_request


def create_user_proxy(name:str = "user_proxy") -> UserProxyAgent:
    # User proxy to drive the GroupChat
    user_proxy = UserProxyAgent(
        name=f"{name}",
        human_input_mode="NEVER",
        is_termination_msg=lambda m: (m.get("content") or "").rstrip().endswith("TERMINATE"),
    )

    return user_proxy

def start_agent():

    user_proxy = create_user_proxy(name="user_proxy")

    #TODO setup other agents
