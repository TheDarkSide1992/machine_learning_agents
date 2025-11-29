import json
from statistics import mean
from typing import Dict

from autogen import UserProxyAgent, AssistantAgent, GroupChatManager, GroupChat, ConversableAgent

from evaluate_agent.config import LLM_CONFIG as CONFIG
from evaluate_agent.tools import make_get_request
from evaluate_agent.agents.agent_prompts import JUDGE_PROMPT, internal_critique_prompt, ARTICLE_PROMPT

_config = CONFIG["config_list"][1]

def create_article_agent() -> ConversableAgent:
    agent =  ConversableAgent(
        name="article_agent",
        llm_config=_config,
        system_message=ARTICLE_PROMPT,

    )

    agent.register_for_llm(name="http_request_tool", description="Perform an HTTP-based search with a JSON request body.")(make_get_request)

    return agent

def create_internal_critic_agent() -> AssistantAgent:
    agent =  AssistantAgent(
        name="internal_critic",
        llm_config=_config,
        system_message=internal_critique_prompt,
    )

    return agent

def create_judge_agent() -> AssistantAgent:
    agent = AssistantAgent(
        name="judge_agent",
        llm_config=_config,
        system_message=JUDGE_PROMPT,
    )

    return agent

def make_groupchat(user_proxy, internal_critic, article_agent) -> GroupChatManager:
    group = GroupChat(
        agents=[user_proxy, article_agent, internal_critic],
        messages=[],
        max_round=20,
        speaker_selection_method="auto",
    )
    return GroupChatManager(groupchat=group, llm_config=None)

def create_user_proxy(name:str = "user_proxy") -> UserProxyAgent:
    agent = UserProxyAgent(
        name=f"{name}",
        human_input_mode="NEVER",
        is_termination_msg=lambda m: (m.get("content") or "").rstrip().endswith("TERMINATE"),
    )

    agent.register_for_execution(name="http_request_tool")(make_get_request)

    return agent


def run_with_internal_critic(user_request: str) -> Dict:
    user_proxy = create_user_proxy()
    article_agent = create_article_agent()
    internal_critic = create_internal_critic_agent()
    manager = make_groupchat(user_proxy, internal_critic, article_agent)

    """
    Run the user_request through:
    - article_agent (drafts)
    - internal_critic (OK / CRITIQUE)
    in a GroupChat, until article_agent emits FINAL_ANSWER + TERMINATE.
    Returns: final_answer + full trace of the conversation.
    """


    init_message =  f"""USER_REQUEST: '{user_request}'
                    Workflow for agents:
                    article_agent: Needs to run http_request_tool to find articles.\n
                    article_agent: If the request is ambiguous or impossible, explain clearly and do NOT "
                    "invent impossible articles.\n"
                    article_agent: read USER_REQUEST and propose an answer as 'DRAFT: ...'.\n
                    internal_critic: when you see a DRAFT, respond with 'OK:' or 'CRITIQUE:'.\n
                    article_agent: if you get CRITIQUE, revise and send a new 'DRAFT:'.\n
                    When internal_critic is satisfied, article_agent sends \n
                    TERMINATE after getting a message 'OK:'.\n
                    Return final answer as 'FINAL_ANSWER: [Answer]' include 'TERMINATE' in the same message, when done.\n
                    Include Link to the article, if it exist.\n
                    The human will only see the FINAL_ANSWER."""


    final = user_proxy.initiate_chat(
        manager,
        message=init_message,
    )

    trace = list(manager.groupchat.messages)

    # Extract the FINAL_ANSWER from article_agent
    final_answer = None
    for msg in reversed(trace):
        if msg.get("name") == "article_agent" and isinstance(msg.get("content"), str):
            content = msg["content"]
            if "FINAL_ANSWER:" in content:
                final_answer = content
                break

    return {
        "final_answer": final_answer or str(final),
        "trace": trace,
    }

def build_judge_prompt(user_prompt: str, final_answer: str) -> str:
    return (
        f"""You are evaluating a research-paper-finding answer.\n
        User prompt:\n"
        \"\"\"{user_prompt}\"\"\"\n"
        Final answer from the agent (after internal critic and GroupChat):\n
        "\"\"\"{final_answer}\"\"\""""
    )

def llm_judge_score(user_prompt: str, final_answer: str) -> Dict:
    print("final answer:", final_answer)
    judge_agent = create_judge_agent()
    judge_prompt = build_judge_prompt(user_prompt, final_answer)
    raw = judge_agent.generate_reply(messages=[{"role": "user", "content": judge_prompt}])
    #content = json.loads(str(raw['final_answer']))
    print("Judge raw response:", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback structure if judge fails to emit valid JSON
        return {
            "final_answer": final_answer,
            "rationale": "Judge JSON parse failed.",
            "completeness": 0.0,
            "quality": 0.0,
            "robustness": 0.0,
            "transparency": 0.0,
            "total": 0.0,
        }

def evaluate_prompt(prompt: str) -> Dict:
    # 1) Run through GroupChat with internal critic
    internal = run_with_internal_critic(prompt)
    final_answer = internal["final_answer"]

    # 2) External judge scores the final answer
    judge_scores = llm_judge_score(prompt, final_answer)

    return {
        "prompt": prompt,
        "final_answer": final_answer,
        "judge_scores": judge_scores,
    }

def start_agent(prompt:str=""):
    if prompt.strip() == "":
        raise ValueError("Invalid prompt.")

    result = evaluate_prompt(prompt=prompt)
