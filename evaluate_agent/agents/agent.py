import json
from statistics import mean
from typing import Dict

from autogen import UserProxyAgent, AssistantAgent, GroupChatManager, GroupChat
from flaml.autogen import ConversableAgent

from evaluate_agent.config import LLM_CONFIG as CONFIG
from evaluate_agent.tools import make_get_request
from evaluate_agent.agents.agent_prompts import JUDGE_PROMPT, internal_critique_prompt, ARTICLE_PROMPT


def create_article_agent() -> ConversableAgent:
    return ConversableAgent(
        name="article_agent",
        llm_config=CONFIG,
        system_message=ARTICLE_PROMPT,
    )


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
    return UserProxyAgent(
        name=f"{name}",
        human_input_mode="NEVER",
        is_termination_msg=lambda m: (m.get("content") or "").rstrip().endswith("TERMINATE"),
    )


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


    init_message = (
        "USER_REQUEST:\n"
        f"{user_request}\n\n"
        "Workflow for agents:\n"
        "- article_agent: read USER_REQUEST and propose an answer as 'DRAFT: ...'.\n"
        "- internal_critic: when you see a DRAFT, respond with 'OK:' or 'CRITIQUE:'.\n"
        "- article_agent: if you get CRITIQUE, revise and send a new 'DRAFT:'.\n"
        "- When internal_critic is satisfied, article_agent sends "
        "'FINAL_ANSWER: ...' and also includes 'TERMINATE' in the same message.\n\n"
        "The human will only see the FINAL_ANSWER.\n"
    )

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
        "You are evaluating a research-paper-finding answer.\n\n"
        "User prompt:\n"
        f"\"\"\"{user_prompt}\"\"\"\n\n"
        "Final answer from the agent (after internal critic and GroupChat):\n"
        f"\"\"\"{final_answer}\"\"\""
    )

def llm_judge_score(user_prompt: str, final_answer: str) -> Dict:
    print("final answer:", final_answer)
    judge_agent = create_judge_agent()
    judge_prompt = build_judge_prompt(user_prompt, final_answer)
    raw = judge_agent.generate_reply(messages=[{"role": "user", "content": judge_prompt}])
    content = raw.get("content", "{}")
    print("Judge raw response:", raw['content'])
    try:
        return json.loads(content)
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

def start_agent():
    print("Enter a query. Press Enter on an empty line to exit.")
    user_topic = ""
    user_inbeforeorafter = ""
    user_year = ""
    user_citation_count = ""
    user_prompt = ""

    while True:
        user_prompt = input("Prompt> ").strip()
        if not user_prompt:
            print("Exiting.")
            break

        result = evaluate_prompt(user_prompt)
