# ==== Standard & Third-Party Imports ====

import os                # ← Provides a portable way of using operating system–dependent functionality.
                         #    We use os.environ to read environment variables, like API keys.

import re                # ← The “regular expression” module. Allows searching strings with patterns.
                         #    We use re.search() to pull JSON blocks out of Claude’s text.

import json              # ← JSON encoder/decoder. Converts between JSON text and Python dicts/lists.
                         #    json.loads() parses JSON text; json.dumps() produces JSON text.

import requests          # ← A popular third-party HTTP library.
                         #    We call requests.get() to fetch data from DuckDuckGo’s API.

from typing import (
    Dict,                # ← For type hinting a Python dict, e.g. Dict[str, Any]
    List,                # ← For hinting Python lists, e.g. List[WebResult]
    Any,                 # ← A catch-all type when contents can be anything
    Optional,            # ← Indicates a value may be None
    Literal              # ← Restricts a value to an exact literal, e.g. Literal["claude"]
)

from dataclasses import (
    dataclass,           # ← Decorator to auto-generate init, repr, eq, etc. for simple classes
    asdict               # ← Converts a dataclass instance into a plain dict
)

# Claude’s SDK for interacting with Anthropic’s API
import anthropic        # ← Provides the `Anthropic` client class for sending/receiving messages

# OpenAI SDK imported but unused here—could be used if you add GPT-based extraction later
import openai           # ← Provides the `openai` client for OpenAI’s API


# ==== Constants ====

# Base URL for DuckDuckGo’s Instant Answer API (returns structured JSON instead of raw HTML)
DUCKDUCKGO_ENDPOINT = "https://api.duckduckgo.com"

# Your Claude API Key, stored in an environment variable for security (not hard-coded)
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")

# A type alias restricting LLM providers to the literal string "claude"
LLMProvider = Literal["claude"]


# ==== Request & Response Data Models ====

@dataclass
class DDGRequest:
    """
    Defines the parameters for a DuckDuckGo search.
    The @dataclass decorator auto-creates:
      - __init__(self, q, format, no_html, skip_disambig)
      - __repr__, __eq__, etc.
    """

    q: str                   # ← The search query text
    format: str = "json"     # ← We want JSON results
    no_html: int = 1         # ← Instructs the API to strip HTML tags
    skip_disambig: int = 1   # ← Skips ambiguous “See also” boxes

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts this dataclass into a standard Python dict,
        e.g. {"q": "...", "format": "json", "no_html": 1, ...}
        Useful for passing as the `params` arg to requests.get().
        """
        return asdict(self)


@dataclass
class WebResult:
    """
    Represents a single web search result in a clean, structured form:
      - title: the heading of the result
      - url: link to the source
      - description: brief summary
    """

    title: str
    url: str
    description: str


# ==== DuckDuckGo MCP Client ====

class MCPClient:
    """
    Wraps DuckDuckGo API calls.
    Users call .search(query) to get a list of WebResult objects.
    """

    def __init__(self, endpoint: str = DUCKDUCKGO_ENDPOINT):
        # Save the base URL; allows override for testing or future endpoints
        self.endpoint = endpoint

    def search(self, query: str, count: int = 10) -> List[WebResult]:
        """
        Sends an HTTP GET to DuckDuckGo with our query.
        - query: the search term
        - count: max results (unused here since we only use Abstract)
        Returns up to one WebResult (DuckDuckGo’s Abstract).
        """

        # Build the request payload using our dataclass
        request_model = DDGRequest(q=query)

        try:
            # Perform the actual HTTP request
            response = requests.get(
                self.endpoint,
                params=request_model.to_dict(),  # → converts to {"q": query, ...}
                timeout=5                        # → fails after 5s if no response
            )
            # If status code != 200, throws HTTPError
            response.raise_for_status()

            # Parse JSON text into Python dict
            data = response.json()

            results: List[WebResult] = []

            # If DDG returns an “Abstract” summary, wrap it in our WebResult
            if data.get("Abstract"):
                results.append(WebResult(
                    title=data.get("Heading", ""),
                    url=data.get("AbstractURL", ""),
                    description=data.get("Abstract", "")
                ))

            return results

        except Exception as e:
            # Print error to stdout; in production you’d log this.
            print(f"[MCPClient.search] Error in DuckDuckGo search: {e}")
            return []  # On error, return empty list


# ==== Claude ↔ MCP Integration Bridge ====

class ClaudeMCPBridge:
    """
    Bridges the gap between:
    - Claude LLM (for extracting user intent)
    - MCPClient (for performing the web search)
    """

    def __init__(self, llm_provider: LLMProvider = "claude"):
        # Initialize the DuckDuckGo client
        self.mcp_client = MCPClient()

        # Store which LLM we’re using (currently only “claude”)
        self.llm_provider = llm_provider

        # Initialize the Anthropic SDK client if using Claude
        if llm_provider == "claude":
            self.claude_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    def extract_website_queries_with_llm(self, user_message: str) -> List[str]:
        """
        Given a free-form user message, return a list of
        specific search queries, e.g. ["mars planet", "nasa"].
        Delegates to _extract_with_claude() when using Claude.
        """
        if self.llm_provider == "claude":
            return self._extract_with_claude(user_message)
        else:
            # For other providers (not implemented), return an error placeholder
            return ["error"]

    def _extract_with_claude(self, user_message: str) -> List[str]:
        """
        Sends the user message to Claude with a system prompt instructing
        it to output exactly JSON like:
          { "queries": ["something", "..."] }
        """

        try:
            # 1) Build the Claude API call
            response = self.claude_client.messages.create(
                model="claude-3-sonnet-20240229",  # ← Specific Claude model version
                max_tokens=800,
                temperature=0.0,                   # ← Deterministic output
                system=(
                    "You are a helpful assistant that IDENTIFIES WEB SEARCH "
                    "QUERIES in the user message. Extract any specific "
                    "topics or websites the user wants info about. "
                    "OUTPUT EXACTLY one JSON object with a 'queries' field, "
                    "e.g., {\"queries\": [\"topic1\", \"topic2\"]}. "
                    "If none found, return {\"queries\": []}."
                ),
                messages=[{"role": "user", "content": user_message}]
            )

            # 2) Claude’s response.content is a list of message chunks;
            #    we want the first chunk’s text.
            content = response.content[0].text

            # 3) Try to find JSON inside triple-backticks:
            json_block = re.search(r'```(?:json)?\s*({.*?})\s*```', content, re.DOTALL)

            if json_block:
                # Extract the inner JSON string
                json_str = json_block.group(1)
                result = json.loads(json_str)
            else:
                # Fallback: maybe Claude returned raw JSON without backticks
                result = json.loads(content)

            # 4) Ensure we return a list of strings (fallback to empty list)
            return result.get("queries", [])

        except Exception as e:
            print(f"[ClaudeMCPBridge._extract_with_claude] Error: {e}")
            return []


# ==== Tool Call Handler (Used by your Flask /tool_call endpoint) ====

def handle_claude_tool_call(tool_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Called when Claude emits a tool_use with parameters like {"query": "..."}.
    We:
      1) Extract the 'query'
      2) Perform a DuckDuckGo search
      3) Return results in JSON-serializable form
    """

    # 1) Read the query parameter
    query = tool_params.get("query", "")
    if not query:
        # If missing or empty, return an error object
        return {"error": "no query provided"}

    # 2) Build the bridge & call the MCP client
    bridge = ClaudeMCPBridge()
    web_results = bridge.mcp_client.search(query)

    # 3) Convert each WebResult dataclass into a plain dict
    results_as_dicts = [asdict(item) for item in web_results]

    # 4) Return as a JSON-ready dict
    return {"results": results_as_dicts}
