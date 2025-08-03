# End-to-End-MCP-Implementation-Using-Claude-DuckDuckGo

# Claude + MCP Integration Project

## 🧠 What is this Project?

This project demonstrates how to connect **Anthropic's Claude API** with an external **Model Context Protocol (MCP) server**, allowing Claude to call external tools such as a web content fetcher. It features:

* 🔍 Claude calling a DuckDuckGo-powered web search tool
* ⚙️ MCP server handling Claude's tool calls
* 🖥️ A command-line interface for asking Claude questions
* 🧵 Tool result chaining and summarization using conversation history

---

## 📁 Project Structure

```
project/
│
├── claude_mcp_client.py         # Main Claude integration logic (tool calls, messaging)
├── mcp_server.py                # Flask-based MCP server handling tool calls
├── mcp_integration.py          # Bridge logic between Claude tool and DuckDuckGo
├── cli.py                       # Command-line interface to interact with Claude
├── requirements.txt             # Dependencies (Flask, requests, anthropic, etc.)
└── README.md                    # You are here
```

---

## 🔄 Code Flow Overview

### 1. User Runs CLI (`cli.py`)

* Accepts a query via CLI or input prompt
* Instantiates `ClaudeClient`
* Calls `get_final_answer()`

### 2. ClaudeClient (`claude_mcp_client.py`)

* Sends the message to Claude API using `send_message()`
* If Claude decides to use a tool (like `fetch_web_content`):

  * Extracts tool call block
  * Forwards it to the MCP server via `_handle_tool_call()`
  * Adds result to conversation history
  * Sends a follow-up message to Claude to summarize the tool response

### 3. MCP Server (`mcp_server.py`)

* Exposes `/tool_call` endpoint
* Receives tool request (e.g., for `fetch_web_content`)
* Calls `handle_claude_tool_call()` from `mcp_integration.py`

### 4. MCP Integration Layer (`mcp_integration.py`)

* Bridges Claude ↔ DuckDuckGo
* Uses `MCPClient` to call the DuckDuckGo API and return results

---

## 🧭 System Architecture Diagram

```mermaid
flowchart TD
    A[User CLI Query] -->|Text Input| B(ClaudeClient.send_message)
    B -->|Request| C[Claude API]
    C -->|Tool Call: fetch_web_content| D[MCP Server (/tool_call)]
    D -->|Search Request| E[MCP Integration Layer]
    E -->|DuckDuckGo API| F[Search Results]
    F -->|Return JSON| D
    D -->|Tool Output| B
    B -->|Summarized Follow-up| C
    C -->|Final Answer| A
```

---

## 🧪 Example Usage

```bash
$ python cli.py who is the CEO of OpenAI?
Searching for who is the CEO of OpenAI?
Answer: The CEO of OpenAI is Sam Altman.
```

---

## ⚙️ Environment Variables

| Variable         | Purpose                                     |
| ---------------- | ------------------------------------------- |
| `CLAUDE_API_KEY` | Your Claude API key                         |
| `MCP_SERVER_URL` | URL of MCP server (default: localhost:5001) |

Create a `.env` file or set them directly in your shell before running the script.

---

## 📦 Requirements

Add this to `requirements.txt`:

```
flask
requests
anthropic
python-dotenv
```

Install via:

```bash
pip install -r requirements.txt
```

---

## ✅ Features

* Claude 3.5-compatible tool calling
* Flexible JSON-based MCP server interface
* Tool chaining with auto-follow-up messages
* Robust error and retry handling

---

## 🧠 Concepts Demonstrated

* ✅ Model Context Protocol (MCP)
* ✅ Claude tool calls ("tools" parameter)
* ✅ LLM + external tool orchestration
* ✅ Claude 3 models (e.g., Opus, Sonnet)
* ✅ JSON parsing and tool routing

---

## 📌 Future Ideas

* Support more tools (e.g., code executor, Wikipedia, math solver)
* Web UI (Streamlit or FastAPI + React)
* Add memory or persistent conversation store (Redis/DB)
* Integrate with LangGraph

---

## 🤝 Credits

Built by \[Your Name], powered by Claude and DuckDuckGo APIs.

---

## 📄 License

MIT License.
