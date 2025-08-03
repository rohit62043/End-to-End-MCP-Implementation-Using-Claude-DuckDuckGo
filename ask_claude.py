import sys  # For exiting the program on failure (sys.exit)
import os  # For accessing environment variables (like API keys)
import requests  # To ping the MCP server's /health endpoint
import argparse  # To handle command-line arguments
import json  # Optional, used if you want to print formatted results later

# Import your custom ClaudeClient class
from claude_mcp_client import ClaudeClient  # Custom module that defines ClaudeClient class

# Check whether the MCP server is running and responding
def check_mcp_server():
    mcp_url = os.environ.get("MCP_SERVER_URL", "http://localhost:5001")  # Get MCP server URL from env, fallback to localhost
    try:
        response = requests.get(f"{mcp_url}/health", timeout=2)  # Send GET request to /health endpoint
        if response.status_code == 200:  # If status code is 200 OK, server is alive
            return True
        return False  # Server is reachable but unhealthy
    except requests.exceptions.RequestException:
        return False  # Network error, server likely unreachable

# The main function that handles CLI flow
def main():
    # Set up argparse for command-line usage
    parser = argparse.ArgumentParser(
        description="Ask Claude questions with web search capability"  # Help description when --help is called
    )

    parser.add_argument(
        "query",  # Positional argument: user types their question in the terminal
        nargs="*",  # Accept 0 or more words; the question is a list of strings
        help="the question to ask claude"  # Description shown in --help
    )

    args = parser.parse_args()  # Parse command-line input (e.g., python script.py who is elon musk)

    # Ensure Claude API key is present in the environment
    if not os.environ.get("CLAUDE_API_KEY"):
        print("Error in getting claude api key")  # Notify user if key is missing
        sys.exit(1)  # Exit the program immediately

    # Determine the query text
    if args.query:
        query = " ".join(args.query)  # Join all words passed via CLI into one sentence
    else:
        query = input("Ask claude")  # If no CLI args, fall back to user input (interactive mode)

    client = ClaudeClient()  # Create an instance of ClaudeClient (uses Claude + MCP)

    print(f"Searching for {query}")  # Log what you're about to search

    try:
        answer = client.get_final_answer(query)  # 🔁 This is where Claude + MCP logic happens
        print("Answer", answer)  # Print the final textual reply from Claude
    except Exception as e:
        print(e)  # Print any error if tool call or Claude interaction fails

# Standard Python boilerplate to ensure this runs only when executed directly
if __name__ == "__main__":
    main()
