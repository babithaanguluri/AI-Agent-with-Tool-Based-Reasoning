#!/usr/bin/env python3
import os
import sys
import ast
import json
import math
import argparse
import operator
import urllib.request
import urllib.parse
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from typing import Dict, List, Any, Tuple, Optional
# Reconfigure stdout/stderr to utf-8 to prevent encoding errors on Windows terminal console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Try importing requests for API calls, fallback to urllib if necessary

try:
    import requests
except ImportError:
    requests = None

# Try importing python-dotenv to read .env files
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Try importing rich for beautiful console logging
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.syntax import Syntax
    from rich.live import Live
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None


# =====================================================================
# 1. Implementation of Tools
# =====================================================================

def get_weather(city: str) -> str:
    """
    Returns current weather conditions for a given city.
    Calls the wttr.in JSON API with fallback mock weather.
    """
    city_clean = city.strip()
    try:
        # wttr.in format=j1 returns full JSON weather data
        encoded_city = urllib.parse.quote(city_clean)
        url = f"https://wttr.in/{encoded_city}?format=j1"
        
        # Add User-Agent header to pretend to be curl
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'curl/7.79.1'}
        )
        
        # Load from wttr.in with 8 second timeout
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode('utf-8'))
            current = data.get('current_condition', [{}])[0]
            temp_c = current.get('temp_C', 'N/A')
            temp_f = current.get('temp_F', 'N/A')
            weather_desc = current.get('weatherDesc', [{}])[0].get('value', 'N/A')
            humidity = current.get('humidity', 'N/A')
            wind_speed = current.get('windspeedKmph', 'N/A')
            
            return (f"Weather in {city_clean}: {weather_desc}, "
                    f"Temperature: {temp_c}°C ({temp_f}°F), "
                    f"Humidity: {humidity}%, "
                    f"Wind Speed: {wind_speed} km/h")
    except Exception as e:
        # Fallback dictionary of popular cities for offline testing or API failure
        mock_weather = {
            "new york": "Sunny, Temperature: 22°C (71.6°F), Humidity: 45%, Wind Speed: 12 km/h",
            "new york city": "Sunny, Temperature: 22°C (71.6°F), Humidity: 45%, Wind Speed: 12 km/h",
            "nyc": "Sunny, Temperature: 22°C (71.6°F), Humidity: 45%, Wind Speed: 12 km/h",
            "tokyo": "Rainy, Temperature: 18°C (64.4°F), Humidity: 80%, Wind Speed: 15 km/h",
            "london": "Cloudy, Temperature: 14°C (57.2°F), Humidity: 75%, Wind Speed: 18 km/h",
            "paris": "Partly Cloudy, Temperature: 17°C (62.6°F), Humidity: 58%, Wind Speed: 10 km/h",
            "berlin": "Clear, Temperature: 16°C (60.8°F), Humidity: 50%, Wind Speed: 9 km/h"
        }
        
        query = city_clean.lower()
        if query in mock_weather:
            return f"{mock_weather[query]} (Mocked fallback due to connection error/limit: {str(e)})"
        
        return (f"Weather in {city_clean}: Partly Cloudy, Temperature: 20°C (68°F), "
                f"Humidity: 50%, Wind Speed: 10 km/h (Fallback due to error: {str(e)})")


# Safe AST Mathematical Evaluator definitions
ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: lambda x: x
}

ALLOWED_FUNCTIONS = {
    'factorial': math.factorial,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'sqrt': math.sqrt,
    'log': math.log,
    'exp': math.exp,
    'abs': abs,
    'round': round
}

def safe_ast_eval(node):
    """Recursively evaluates AST nodes containing only safe mathematical operations."""
    if isinstance(node, ast.Expression):
        return safe_ast_eval(node.body)
    elif isinstance(node, ast.Num):  # Python < 3.8
        return node.n
    elif isinstance(node, ast.Constant):  # Python >= 3.8
        return node.value
    elif isinstance(node, ast.BinOp):
        left = safe_ast_eval(node.left)
        right = safe_ast_eval(node.right)
        op_type = type(node.op)
        if op_type in ALLOWED_OPERATORS:
            # Prevent division by zero
            if op_type == ast.Div and right == 0:
                raise ZeroDivisionError("Division by zero is not allowed.")
            # Prevent overly large exponents to avoid CPU hang / OverflowError
            if op_type == ast.Pow and right > 1000:
                raise ValueError("Exponent too large (max 1000).")
            return ALLOWED_OPERATORS[op_type](left, right)
        raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
    elif isinstance(node, ast.UnaryOp):
        operand = safe_ast_eval(node.operand)
        op_type = type(node.op)
        if op_type in ALLOWED_OPERATORS:
            return ALLOWED_OPERATORS[op_type](operand)
        raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in ALLOWED_FUNCTIONS:
            args = [safe_ast_eval(arg) for arg in node.args]
            # Prevent factorial overflow
            if node.func.id == 'factorial' and args[0] > 100:
                raise ValueError("Factorial argument too large (max 100).")
            return ALLOWED_FUNCTIONS[node.func.id](*args)
        raise ValueError(f"Unsupported function call: {node.func.id if isinstance(node.func, ast.Name) else 'unknown'}")
    raise ValueError(f"Unsupported mathematical expression element: {type(node).__name__}")

def calculate(expression: str) -> str:
    """
    Evaluates a mathematical expression safely using AST parsing.
    Supports +, -, *, /, **, factorial(), sin(), cos(), tan(), sqrt(), log(), exp(), abs().
    """
    # Clean expression and common input variations
    expr = expression.strip().lstrip('=').strip()
    
    # Handle simple textual factorials like "5!"
    if expr.endswith('!'):
        val = expr[:-1].strip()
        if val.isdigit():
            expr = f"factorial({val})"

    try:
        tree = ast.parse(expr, mode='eval')
        result = safe_ast_eval(tree)
        return str(result)
    except Exception as e:
        return f"Error evaluating expression '{expression}': {str(e)}. (Syntax format: 'factorial(5)' or '2**8')"


def search_wikipedia(query: str) -> str:
    """
    Searches Wikipedia for a query and returns snippets of top results.
    Uses the official Wikipedia OpenSearch API.
    """
    query_clean = query.strip()
    try:
        encoded_query = urllib.parse.quote(query_clean)
        # Search API to find matching articles
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded_query}&utf8=&format=json"
        
        req = urllib.request.Request(
            search_url,
            headers={'User-Agent': 'ReActAgentBot/1.0 (contact: admin@example.com)'}
        )
        
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode('utf-8'))
            search_results = data.get('query', {}).get('search', [])
            
            if not search_results:
                return f"No Wikipedia results found for '{query_clean}'."
            
            # Format top 3 results
            results_list = []
            for i, result in enumerate(search_results[:3]):
                title = result.get('title')
                snippet = result.get('snippet', '')
                # Basic HTML cleaning of Wikipedia's match tags
                clean_snippet = snippet.replace('<span class="searchmatch">', '').replace('</span>', '')
                # HTML entity decoding for quotes/ampersands
                clean_snippet = clean_snippet.replace('&quot;', '"').replace('&amp;', '&').replace('&#039;', "'")
                results_list.append(f"{i+1}. {title}: {clean_snippet}...")
            
            return "\n".join(results_list)
    except Exception as e:
        return f"Error searching Wikipedia for '{query_clean}': {str(e)}"


# =====================================================================
# 2. Tool JSON Schema Definitions
# =====================================================================

TOOL_SCHEMAS = [
    {
        "name": "get_weather",
        "description": "Get current weather conditions for a given city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The name of the city, e.g., 'New York City', 'Tokyo', 'London'."
                }
            },
            "required": ["city"]
        }
    },
    {
        "name": "calculate",
        "description": (
            "Safely evaluates a mathematical expression. "
            "Supported operations: +, -, *, /, **, factorial(x), sin(x), cos(x), tan(x), sqrt(x), log(x), exp(x)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to evaluate, e.g., 'factorial(5)' or '2**8' or '15 + 32'."
                }
            },
            "required": ["expression"]
        }
    },
    {
        "name": "search_wikipedia",
        "description": "Searches Wikipedia for a query and returns snippets of the top search results.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search term or topic to query on Wikipedia."
                }
            },
            "required": ["query"]
        }
    }
]

# Map of tool names to functions for execution
TOOL_FUNCTIONS = {
    "get_weather": get_weather,
    "calculate": calculate,
    "search_wikipedia": search_wikipedia
}

def execute_tool(name: str, arguments: Dict[str, Any]) -> str:
    """Executes a tool by name with arguments and returns a string result."""
    if name not in TOOL_FUNCTIONS:
        return f"Error: Tool '{name}' is not defined. Available tools: {list(TOOL_FUNCTIONS.keys())}"
    
    try:
        # Call the tool function with unpacked parameters
        result = TOOL_FUNCTIONS[name](**arguments)
        return str(result)
    except Exception as e:
        return f"Error executing tool '{name}': {str(e)}"


# =====================================================================
# 3. LLM API Providers & Simulation Offline Mode
# =====================================================================

def call_gemini_api(messages: List[Dict[str, Any]], api_key: str, model: str = "gemini-3.1-flash-lite") -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Calls Gemini API using raw HTTP requests to support function calling schemas."""
    if not requests:
        raise ImportError("The 'requests' package is required for Live LLM mode. Install it with: pip install requests")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    # Map roles and parts for Gemini API compatibility
    contents = []
    for msg in messages:
        role = "model" if msg["role"] == "assistant" else "user"
        parts = []
        
        if msg["role"] == "assistant" and "gemini_parts" in msg:
            # Deep copy or use directly since we don't modify it
            parts = msg["gemini_parts"]
        else:
            # Text content
            if msg.get("content"):
                parts.append({"text": msg["content"]})
                
            # Assistant's previous tool calls
            if "tool_calls" in msg:
                for tc in msg["tool_calls"]:
                    parts.append({
                        "functionCall": {
                            "name": tc["function"]["name"],
                            "args": json.loads(tc["function"]["arguments"]),
                            "id": tc.get("id")
                        }
                    })
                
        # Tool call response (observation)
        if msg["role"] == "tool":
            parts.append({
                "functionResponse": {
                    "name": msg["name"],
                    "response": {"result": msg["content"]},
                    "id": msg.get("tool_call_id")
                }
            })
            
        if parts:
            contents.append({"role": role, "parts": parts})
            
    # Gemini schema types conversion (string -> STRING, object -> OBJECT, etc.)
    def convert_schema(schema_dict: Dict[str, Any]) -> Dict[str, Any]:
        converted = {}
        for k, v in schema_dict.items():
            if k == "type" and isinstance(v, str):
                converted[k] = v.upper()
            elif k == "properties" and isinstance(v, dict):
                converted[k] = {pk: convert_schema(pv) for pk, pv in v.items()}
            else:
                converted[k] = v
        return converted

    # Format tools list
    gemini_tools = []
    if TOOL_SCHEMAS:
        function_declarations = []
        for schema in TOOL_SCHEMAS:
            fd = {
                "name": schema["name"],
                "description": schema["description"],
                "parameters": convert_schema(schema["parameters"])
            }
            function_declarations.append(fd)
        gemini_tools = [{"functionDeclarations": function_declarations}]
        
    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [
                {
                    "text": (
                        "You are an expert AI agent working in a ReAct (Reasoning + Acting) loop. "
                        "Before selecting a tool or returning a response, provide a 'Thought' explaining your reasoning. "
                        "If you need to retrieve external data, use the appropriate tool. "
                        "Once you have enough information, write your final answer."
                    )
                }
            ]
        }
    }
    if gemini_tools:
        payload["tools"] = gemini_tools
        
    response = requests.post(url, headers=headers, json=payload, timeout=20)
    if response.status_code != 200:
        raise Exception(f"Gemini API request failed ({response.status_code}): {response.text}")
        
    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise Exception(f"No response candidate returned by Gemini API. Response: {data}")
        
    parts = candidates[0].get("content", {}).get("parts", [])
    
    text = ""
    tool_calls = []
    
    for part in parts:
        if "text" in part:
            text += part["text"]
        if "functionCall" in part:
            fc = part["functionCall"]
            tool_calls.append({
                "id": fc.get("id"),
                "type": "function",
                "function": {
                    "name": fc["name"],
                    "arguments": json.dumps(fc["args"])
                }
            })
        
    return text, tool_calls, parts


def call_openai_api(messages: List[Dict[str, Any]], api_key: str, model: str = "gpt-4o-mini") -> Tuple[str, List[Dict[str, Any]]]:
    """Calls OpenAI API using the raw HTTP request."""
    if not requests:
        raise ImportError("The 'requests' package is required for Live LLM mode. Install it with: pip install requests")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    openai_tools = []
    for schema in TOOL_SCHEMAS:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema["description"],
                "parameters": schema["parameters"]
            }
        })
        
    # Inject ReAct instruction into system role if not already there
    formatted_messages = list(messages)
    if not any(m["role"] == "system" for m in formatted_messages):
        formatted_messages.insert(0, {
            "role": "system",
            "content": (
                "You are an expert AI agent working in a ReAct (Reasoning + Acting) loop. "
                "Before selecting a tool or returning a response, provide a 'Thought' explaining your reasoning. "
                "Use the available tools when external information is required. "
                "When you have finished, compile a clear final answer."
            )
        })
        
    payload = {
        "model": model,
        "messages": formatted_messages,
        "tools": openai_tools
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=20)
    if response.status_code != 200:
        raise Exception(f"OpenAI API request failed ({response.status_code}): {response.text}")
        
    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        raise Exception(f"No response choices returned by OpenAI. Response: {data}")
        
    message = choices[0].get("message", {})
    text = message.get("content") or ""
    tool_calls = message.get("tool_calls") or []
    
    # Format tool calls cleanly
    formatted_calls = []
    for tc in tool_calls:
        formatted_calls.append({
            "id": tc.get("id"),
            "type": "function",
            "function": {
                "name": tc.get("function", {}).get("name"),
                "arguments": tc.get("function", {}).get("arguments")
            }
        })
        
    return text, formatted_calls


# =====================================================================
# Deterministic Mock Simulation Model (Offline Mode)
# =====================================================================

class SimulationLLM:
    """
    Simulates the ReAct agent thoughts and tool selections offline for demonstration.
    This allows verification of the entire loop without API keys.
    """
    def __init__(self, prompt: str):
        self.prompt = prompt.strip().lower()
        self.step_idx = 0
        
    def get_response(self, messages: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
        self.step_idx += 1
        
        # Case A: Weather + Factorial Prompt (Requirement #4 Demo)
        if "weather" in self.prompt and ("factorial" in self.prompt or "5!" in self.prompt):
            if self.step_idx == 1:
                thought = "I need to answer two queries: find the weather in New York City and compute the factorial of 5. First, I will look up the current weather conditions for New York City."
                tool_calls = [{
                    "id": "sim_call_1",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": json.dumps({"city": "New York City"})
                    }
                }]
                return thought, tool_calls
                
            elif self.step_idx == 2:
                # Find the previous tool observation
                observation = "N/A"
                for msg in reversed(messages):
                    if msg["role"] == "tool" and msg["name"] == "get_weather":
                        observation = msg["content"]
                        break
                
                thought = f"I have received the weather observations: '{observation}'. Now I need to compute the second part of the query, which is 5 factorial (5!). I will call the calculate tool with 'factorial(5)'."
                tool_calls = [{
                    "id": "sim_call_2",
                    "type": "function",
                    "function": {
                        "name": "calculate",
                        "arguments": json.dumps({"expression": "factorial(5)"})
                    }
                }]
                return thought, tool_calls
                
            else:
                weather_obs = "Sunny, 22°C (71.6°F)"
                calc_obs = "120"
                for msg in messages:
                    if msg["role"] == "tool":
                        if msg["name"] == "get_weather":
                            weather_obs = msg["content"]
                        elif msg["name"] == "calculate":
                            calc_obs = msg["content"]
                            
                thought = "I have successfully retrieved the weather in New York City and calculated 5 factorial. I will now synthesize these observations into a final response."
                final_text = (
                    f"Here is the result of your request:\n"
                    f"1. {weather_obs}\n"
                    f"2. 5 factorial (5!) is equal to {calc_obs}.\n\n"
                    f"Both parts of the request have been successfully completed."
                )
                return f"Thought: {thought}\n\n{final_text}", []
                
        # Case B: Wikipedia + Math query
        elif "wikipedia" in self.prompt or "ada lovelace" in self.prompt:
            if self.step_idx == 1:
                thought = "The user is asking about Ada Lovelace and a division calculation. I will search Wikipedia for Ada Lovelace first to gather biographical details."
                tool_calls = [{
                    "id": "sim_call_wiki",
                    "type": "function",
                    "function": {
                        "name": "search_wikipedia",
                        "arguments": json.dumps({"query": "Ada Lovelace"})
                    }
                }]
                return thought, tool_calls
            elif self.step_idx == 2:
                thought = "I have retrieved the summary of Ada Lovelace. Now, I will calculate the mathematical expression 12 divided by 3."
                tool_calls = [{
                    "id": "sim_call_calc",
                    "type": "function",
                    "function": {
                        "name": "calculate",
                        "arguments": json.dumps({"expression": "12 / 3"})
                    }
                }]
                return thought, tool_calls
            else:
                wiki_obs = "Ada Lovelace info"
                calc_obs = "4.0"
                for msg in messages:
                    if msg["role"] == "tool":
                        if msg["name"] == "search_wikipedia":
                            wiki_obs = msg["content"]
                        elif msg["name"] == "calculate":
                            calc_obs = msg["content"]
                
                thought = "I have completed both the biography search and the division calculation. I will now combine these results for the final answer."
                final_text = (
                    f"Based on the tools:\n"
                    f"1. Ada Lovelace Biography: {wiki_obs}\n"
                    f"2. Calculation: 12 divided by 3 is {calc_obs}.\n\n"
                    f"Both steps have been completed."
                )
                return f"Thought: {thought}\n\n{final_text}", []
                
        # Default Fallback for other queries
        else:
            if self.step_idx == 1:
                thought = "This is a generic query simulation. I will perform a search on the topic."
                tool_calls = [{
                    "id": "sim_call_default",
                    "type": "function",
                    "function": {
                        "name": "search_wikipedia",
                        "arguments": json.dumps({"query": self.prompt})
                    }
                }]
                return thought, tool_calls
            else:
                thought = "I have searched Wikipedia. I will compile the final simulation response."
                return f"Thought: {thought}\n\nSimulation response: The query '{self.prompt}' was processed in offline simulation mode. To execute arbitrary queries with a live LLM, configure an API key (GEMINI_API_KEY or OPENAI_API_KEY) in a .env file.", []


# =====================================================================
# 4. ReAct Agent Loop
# =====================================================================

def log_trace_step(step: int, max_steps: int, thought: str, action_name: Optional[str] = None, action_args: Optional[Dict[str, Any]] = None, observation: Optional[str] = None):
    """Prints a premium visual representation of the agent step to the console."""
    if HAS_RICH:
        # Construct rich panels
        step_header = Text(f"--- Step {step}/{max_steps} ---", style="bold magenta")
        console.print(step_header)
        
        # Thought
        thought_text = Text(thought, style="yellow")
        console.print(Panel(thought_text, title="Thought", border_style="yellow"))
        
        # Action (if any)
        if action_name:
            action_text = Text(f"Call Tool: {action_name}\nArguments: {json.dumps(action_args, indent=2)}", style="cyan")
            console.print(Panel(action_text, title="Action", border_style="cyan"))
            
        # Observation (if any)
        if observation:
            obs_text = Text(observation, style="green")
            console.print(Panel(obs_text, title="Observation", border_style="green"))
            
        console.print()
    else:
        # Standard fallback printing
        print(f"\n--- Step {step}/{max_steps} ---")
        print(f"Thought: {thought}")
        if action_name:
            print(f"Action: Call tool '{action_name}' with args {action_args}")
        if observation:
            print(f"Observation: {observation}")


def run_agent(task: str, max_steps: int = 10, api_key: str = None, provider: str = "gemini", model: Optional[str] = None) -> str:
    """
    Core ReAct loop execution. Alternates between LLM and tools.
    Prevents infinite execution via max_steps.
    """
    messages = [
        {"role": "user", "content": task}
    ]
    
    # Initialize the LLM client or simulation client
    is_simulation = not bool(api_key)
    sim_client = SimulationLLM(task) if is_simulation else None
    
    if HAS_RICH:
        if is_simulation:
            console.print(Panel(
                Text("API Key not set. Running in Offline Simulation Mode.\n"
                     "Configured for: 'What's the weather in New York City, and what is 5 factorial?'", style="bold yellow"),
                title=" System Notice"
            ))
        else:
            console.print(Panel(
                Text(f"Initializing ReAct Loop using Provider: {provider.upper()}\nPrompt: '{task}'", style="bold green"),
                title=" Starting Agent"
            ))
    else:
        if is_simulation:
            print("[INFO] API Key not set. Running in Offline Simulation Mode.")
        else:
            print(f"[INFO] Starting ReAct Loop using Provider: {provider.upper()}")
 
    # Loop iterations
    for step in range(1, max_steps + 1):
        # 1. Retrieve thought and actions from LLM/Simulation
        try:
            if is_simulation:
                raw_text, tool_calls = sim_client.get_response(messages)
                gemini_parts = None
            else:
                if provider == "gemini":
                    model_to_use = model or "gemini-3.1-flash-lite"
                    raw_text, tool_calls, gemini_parts = call_gemini_api(messages, api_key, model=model_to_use)
                elif provider == "openai":
                    model_to_use = model or "gpt-4o-mini"
                    raw_text, tool_calls = call_openai_api(messages, api_key, model=model_to_use)
                    gemini_parts = None
                else:
                    raise ValueError(f"Unknown provider: {provider}")
        except Exception as e:
            error_msg = f"LLM API Error during ReAct step: {str(e)}"
            if HAS_RICH:
                console.print(Panel(Text(error_msg, style="bold red"), title="❌ Error"))
            else:
                print(f"Error: {error_msg}")
            return f"Agent run failed due to LLM error: {str(e)}"

        # Clean the response thought and compile assistant message content
        thought = raw_text
        # Extract Thought if it has a prefix (often Gemini prefixing text output)
        if "thought:" in thought.lower():
            # Extract content after Thought: but before tool call if any
            parts_thought = thought.lower().split("thought:")
            if len(parts_thought) > 1:
                thought = raw_text[len(parts_thought[0]) + 8:].strip()
                
        # 2. Append assistant turn to messages history
        assistant_msg = {"role": "assistant", "content": raw_text}
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        if gemini_parts is not None:
            assistant_msg["gemini_parts"] = gemini_parts
        messages.append(assistant_msg)

        # 3. Decision Point: Does the LLM want to use tools or reply directly?
        if not tool_calls:
            # Reached a final answer!
            # Format and display
            if HAS_RICH:
                console.print(Panel(
                    Text(f"Agent reached final answer:\n\n{raw_text}", style="bold bright_green"),
                    title="Final Answer",
                    border_style="bright_green"
                ))
            else:
                print("\nAgent provides final answer.")
                print(raw_text)
            return raw_text

        # 4. Handle tool execution (there can be multiple, but we process them sequentially)
        # We only support executing the first tool call in standard ReAct sequential tracing
        tool_call = tool_calls[0]
        tool_name = tool_call["function"]["name"]
        
        try:
            tool_args = json.loads(tool_call["function"]["arguments"])
        except Exception as e:
            tool_args = {}
            console.print(f"[Warning] Failed parsing tool arguments: {e}") if HAS_RICH else print(f"Warning: Argument parse failure: {e}")

        # Execute tool
        observation = execute_tool(tool_name, tool_args)


        # Log observation trace
        log_trace_step(
            step=step,
            max_steps=max_steps,
            thought=thought,
            action_name=tool_name,
            action_args=tool_args,
            observation=observation
        )

        # 5. Append tool output (observation) back to conversation history
        messages.append({
            "role": "tool",
            "name": tool_name,
            "tool_call_id": tool_call["id"],
            "content": observation
        })

    # If the loop finishes without returning, max steps limit was hit!
    limit_msg = "Max steps reached without completing the task."
    if HAS_RICH:
        console.print(Panel(Text(limit_msg, style="bold red"), title="⚠️ Execution Stopped"))
    else:
        print(f"\nExecution Stopped: {limit_msg}")
    return limit_msg


# =====================================================================
# Main CLI Entry Point
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="ReAct AI Agent with Tool Calling")
    parser.add_argument(
        "--prompt", 
        type=str, 
        default="What's the weather in New York City, and what is 5 factorial?",
        help="The problem/prompt for the AI Agent to solve."
    )
    parser.add_argument(
        "--max-steps", 
        type=int, 
        default=10,
        help="Maximum steps before terminating the loop."
    )
    parser.add_argument(
        "--provider", 
        type=str, 
        choices=["gemini", "openai"],
        default="gemini",
        help="LLM provider to use (default: gemini)."
    )
    parser.add_argument(
        "--model", 
        type=str, 
        default=None,
        help="Specific model to run (defaults: gemini-1.5-flash or gpt-4o-mini)."
    )
    parser.add_argument(
        "--api-key", 
        type=str, 
        default=None,
        help="API Key for the provider (overrides environment variables)."
    )
    
    args = parser.parse_args()

    # Determine API key to use
    api_key = args.api_key
    provider = args.provider.lower()
    
    if not api_key:
        if provider == "gemini":
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        elif provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")

    # Run the ReAct agent
    run_agent(
        task=args.prompt,
        max_steps=args.max_steps,
        api_key=api_key,
        provider=provider,
        model=args.model
    )


if __name__ == "__main__":
    main()
