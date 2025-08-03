# ==== Standard and Local Imports ====

import os                   # ← For reading environment variables, like PORT
import json                 # ← For encoding/decoding JSON (not used directly here, but useful)
from flask import (
    Flask,                  # ← Flask app factory
    request,                # ← Represents the incoming HTTP request
    jsonify                 # ← Converts Python dicts to proper JSON HTTP responses
)

# Importing from our custom MCP integration module
from mcp_integration import (
    handle_claude_tool_call # ← Function that performs the search and returns results
)

# ==== Port Configuration ====

PORT = int(os.environ.get("PORT", 5001))
# Tries to get the PORT from the environment (useful for deployment platforms like Heroku).
# If not set, defaults to port 5001.
# `int(...)` is necessary because os.environ returns strings.

# ==== Initialize Flask App ====

app = Flask(__name__)
# Creates the main Flask application.
# `__name__` is a special Python variable that is set to the name of the module.
# Flask uses this to know where to find resources like templates and static files.


# ==== Health Check Endpoint ====

@app.route("/health", methods=["GET"])
def health_check():
    # A simple health check route to verify that the server is alive.
    # Often used in deployments, uptime monitoring, load balancers, etc.
    return jsonify({"status": "ok"})
    # Returns a JSON response: { "status": "ok" }

# ==== Root Endpoint ====

@app.route("/", methods=["GET"])
def root():
    # A simple welcome/info page showing what the MCP server is.
    return jsonify({
        "name": "MCP server",
        "status": "running",
        "endpoints": [
            {"path": "/health", "methods": ["GET"], "description": "health"},
            {"path": "/tool_call", "methods": ["POST"], "description": "Handle the tool call"}
        ]
    })
    # Gives metadata about the server: its name, status, and available endpoints.

# ==== Tool Call Endpoint ====

@app.route("/tool_call", methods=["POST"])
def tool_call():
    # This route handles POST requests from Claude when it issues a tool call.
    
    if not request.json:
        # If the request body is missing or not valid JSON
        return jsonify({"error": "invalid request"}), 400
        # Returns an error with HTTP status code 400 (Bad Request)

    tool_name = request.json.get("name")
    # Reads the `name` field from the tool call JSON payload.
    # This tells us what tool Claude is trying to use (e.g., "fetch_web_content").

    parameters = request.json.get("parameters", {})
    # Reads the `parameters` field — this will contain inputs like `query: "mars"`.

    if tool_name != "fetch_web_content":
        # We only support one tool in this MCP server — anything else is rejected.
        return jsonify({"error": "unknown tool name"}), 400
        # Return 400 Bad Request for unsupported tool names.

    result = handle_claude_tool_call(parameters)
    # Calls our handler function with the parameters to fetch web content.
    # This function calls DuckDuckGo and formats results.

    return jsonify(result)
    # Converts the Python dict returned from handle_claude_tool_call into a JSON response.

# ==== Run App ====

if __name__ == "__main__":
    # This check ensures the code runs only if the file is executed directly (not imported).
    
    app.run(host="0.0.0.0", port=PORT)
    # Runs the Flask app on all network interfaces (0.0.0.0) at the specified port.
    # Useful for Docker, cloud servers, and local dev.
