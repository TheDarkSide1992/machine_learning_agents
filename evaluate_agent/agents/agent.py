from autogen import UserProxyAgent, AssistantAgent, GroupChatManager, GroupChat
from flaml.autogen import ConversableAgent

from evaluate_agent.config import LLM_CONFIG as CONFIG
from evaluate_agent.tools import make_get_request
from evaluate_agent.agents.agent_prompts import JUDGE_PROMPT, internal_critique_prompt, ARTICLE_PROMPT


def create_article_agent() -> ConversableAgent:
    article_agent = ConversableAgent(
        name="article_agent",
        llm_config=CONFIG,
        system_message=ARTICLE_PROMPT,
    )
    return article_agent


def create_internal_critic_agent() -> AssistantAgent:
    return AssistantAgent(
        name="internal_critic",
        llm_config=CONFIG,
        system_message=internal_critique_prompt,
    )

def create_judge_agent() -> AssistantAgent:
    return AssistantAgent(
        name="judge_agent",
        llm_config=CONFIG,
        system_message=JUDGE_PROMPT,
    )

def make_groupchat(user_proxy, internal_critic, article_agent) -> GroupChatManager:
    group = GroupChat(
        agents=[user_proxy, internal_critic, article_agent],
        messages=[],
        max_round=20,
        speaker_selection_method="auto",
    )
    return GroupChatManager(groupchat=group, llm_config=CONFIG)

def create_user_proxy(name:str = "user_proxy") -> UserProxyAgent:
    user_proxy = UserProxyAgent(
        name=f"{name}",
        human_input_mode="NEVER",
        is_termination_msg=lambda m: (m.get("content") or "").rstrip().endswith("TERMINATE"),
    )

    return user_proxy

def start_agent():

    user_proxy = create_user_proxy(name="user_proxy")

    #TODO setup other agents
