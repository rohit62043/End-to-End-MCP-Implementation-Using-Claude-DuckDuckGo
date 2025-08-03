import os  # For accessing environment variables like API keys and server URLs
import json  # For encoding and decoding JSON data
import requests  # For making HTTP requests to Claude API and MCP server
import time  # For implementing retry logic with exponential backoff
from typing import Dict, List, Any, Optional  # Type hinting support

# Load Claude API key from environment variable
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")

# Claude API endpoint URL
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

# URL of the local or deployed MCP server
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:5001")

# ClaudeClient class for interacting with Claude API and handling tool calls
class ClaudeClient:
    def __init__(self, api_key: str = CLAUDE_API_KEY, model: str = "claude-3-opus-20240229"):
        self.api_key = api_key  # Store API key
        self.model = model  # Store model name

        # Prepare HTTP headers required by Claude API
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        #Define tool schema for claude's tool call
        self.tools=[{
            "name":"fetch_web_content",
            "description":"Retrieves info from website based on users queries",
            "input_schema":{
                "type":"object",
                "properties":{
                    "query":{
                        "type":"string",
                        "description":"the search query or website to look up information about"
                    }
                },
                "required":["query"]
            }
        }]
        
        self._check_mcp_server(self)
    
    def _check_mcp_server():
        try:
            response=requests.get(f"{MCP_SERVER_URL}/health",timeout=2)
            if response.status_code==200:
                return True
        except:
            pass
        
        return False
    
    def send_message(self,message:str,conversation_history:Optional[List[Dict[str,Any]]]=None)->Dict[str,Any]:
        if not self.api_key:
            raise ValueError("Api key of claude is needed")
        if conversation_history is None:
            conversation_history=[]
        
        payload={
            "model":self.model,
            "max_tokens":4096,
            "messages":conversation_history+[{"role":"user","content":message}],
            "tools":self.tools
        }
        
        print("Sending request to claude")
        
        try:
            response=requests.post(
                CLAUDE_API_URL,
                header=self.headers,
                json=payload
            )
           
            if response.status_code!=200:
               print(response.json)
               print("Error")
            
            response.raise_for_status()
            
            result=response.json()
            print(f"Claude response:{result}")
            
            has_tool_call=False
            tool_call={}
            
            if "content" in result:
                for content_block in result.get("content",[]):
                    if content_block.get("type")=="tool_use":
                        has_tool_call=True
                        print("Tool call detected")
                        
                        tool_call["name"]=content_block.get("name","")
                        tool_call["parameters"]={}
                        tool_call["parameters"]["query"]=content_block.get("input",{}).get("query",{})
                        
                        print(f"Tool call details: {tool_call}")
                        
                        tool_response=self._handle_tool_call(tool_call)
                        print(f"tool response:{tool_response}")
                        
                        
                        conversation_history.append({"role":"user","content":message})
                        conversation_history.append({"role":"assistant","content":[
                            {"type":"text","text":result.get("content",[{}])[0].get("text","")+"\n\nThe tool call was successful and here is the information from the tool call: " +
                             tool_response["results"][0]["description"]}
                        ]})
                        
                        return self.send_message("Please summarize the information from the tool call and don't send any more tool calls", conversation_history)
                
            if not has_tool_call:
                print("No Tool Calls")
            
            return result    
        
        except Exception as e:
            print(e)
        

        