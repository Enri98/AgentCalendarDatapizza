import sys
from .agent import create_calendar_agent

def main():
    print("--- Calendar Assistant REPL ---")
    print("Type your request or '/exit' to quit.")
    
    agent = create_calendar_agent()
    
    max_turns = 15
    for turn in range(max_turns):
        try:
            user_input = input("\nUser: ").strip()
        except EOFError:
            break
            
        if user_input.lower() == "/exit":
            print("Goodbye!")
            break
        
        if not user_input:
            continue
            
        try:
            response = agent.run(user_input)
            print(f"\nAssistant: {response}")
        except Exception as e:
            print(f"\nError: {e}")
    else:
        print("\nMax conversation turns (15) reached. Ending session.")

if __name__ == "__main__":
    main()
