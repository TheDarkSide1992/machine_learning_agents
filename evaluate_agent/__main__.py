from evaluate_agent.agents import start

def main(): #TODO Make it run the agents as exegesis requires
    print("Starting up.....")

    while True:
        prompt = get_user_input()
        start(prompt=prompt)


def get_user_input() -> str:
    prompt = input("Please enter your prompt: ")

    while prompt.strip() == "":
        prompt = input("Invalid input, please enter your prompt: ")

    return prompt

if __name__ == "__main__":
    main()