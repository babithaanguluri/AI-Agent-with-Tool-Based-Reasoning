# 🤖 AI Agent with Tool-Based Reasoning Using the ReAct Pattern

A fully functional, command-line AI Agent in Python built around the **ReAct (Reasoning + Acting)** pattern. The agent interacts with external APIs and executes safe math parsing to solve multi-step problems. It supports direct API integration with Google Gemini and OpenAI, as well as an offline simulation mode for local verification.

---

## 💡 How It Works: The ReAct Pattern

The **ReAct (Reasoning + Acting)** pattern combines reasoning (thinking about what to do next) with acting (executing external tools to get feedback/observations). This creates a loop that allows the LLM to complete complex, multi-step tasks sequentially.

Here is a visual overview of how the agent handles a user request:

```text
                     ┌──────────────────────────────┐
                     │         User Request         │
                     │  "What is the weather in     │
                     │  Tokyo, and what is 5! ?"    │
                     └──────────────┬───────────────┘
                                    │
                                    ▼
                     ┌──────────────────────────────┐
                     │          ReAct Loop          │
                     │  (Max steps guard: 10 steps) │
                     └──────────────┬───────────────┘
                                    │
                                    ├──────────────────────────┐
                                    ▼                          │ (Loop continues until
                             ┌──────────────┐                  │  final answer is found)
                             │   Thought    │                  │
                             │  "I need to  │                  │
                             │  get weather"│                  │
                             └──────┬───────┘                  │
                                    │                          │
                                    ▼                          │
                             ┌──────────────┐                  │
                             │    Action    │                  │
                             │ get_weather  │                  │
                             │  ("Tokyo")   │                  │
                             └──────┬───────┘                  │
                                    │                          │
                                    ▼                          │
                             ┌──────────────┐                  │
                             │ Observation  │                  │
                             │ "Rainy, 18°C"│                  │
                             └──────┬───────┘                  │
                                    │                          │
                                    └──────────────────────────┘
                                    │
                                    ▼
                     ┌──────────────────────────────┐
                     │         Final Answer         │
                     │   "In Tokyo it is rainy, and │
                     │   5 factorial is 120."       │
                     └──────────────────────────────┘
```

### The ReAct Cycle Sequence:
1. **Thought**: The model generates a textual explanation outlining its current understanding of the problem and planning the next action.
2. **Action (Tool Call)**: The model determines that it needs external data and requests the execution of a registered tool with specific arguments.
3. **Observation (Tool Response)**: The python execution environment catches the request, executes the tool function, retrieves the response, and appends it back to the conversation history.
4. **Repeat**: The model reads the conversation history (including the tool's observation/result) and forms a new **Thought** to either run another tool or provide the **Final Answer**.
5. **Infinite Loop Prevention**: If the loop exceeds `max_steps` (default is 10) without finding a final response, it gracefully halts with a safety stoppage warning.

---

## 📂 Project Structure

- **[agent.py](file:///d:/AI Agent with Tool-Based Reasoning Using the ReAct Pattern/agent.py)**: The main script. Contains:
  - Tool definitions (`get_weather`, `calculate`, `search_wikipedia`) and safe math parsing modules.
  - JSON schemas declaring tool signatures to the LLM.
  - LLM integration layers for Google Gemini and OpenAI.
  - The deterministic offline simulation model.
  - The core ReAct loop (`run_agent`) and premium formatting console logs.
- **[.env.example](file:///d:/AI Agent with Tool-Based Reasoning Using the ReAct Pattern/.env.example)**: Reference environment file indicating configuration variables.
- **[.env](file:///d:/AI Agent with Tool-Based Reasoning Using the ReAct Pattern/.env)** *(to be created)*: The configuration file containing your private API credentials.

---

## 🛠️ Project Components & Logic Details

### 1. Functional Tools
The agent uses three separate tools, defined in [agent.py](file:///d:/AI Agent with Tool-Based Reasoning Using the ReAct Pattern/agent.py):
*   **Weather Retrieval ([get_weather](file:///d:/AI Agent with Tool-Based Reasoning Using the ReAct Pattern/agent.py#L59))**: 
    - Queries the public `wttr.in` JSON API using a custom curl User-Agent header and an 8-second timeout.
    - Features a **local fallback dictionary** of popular cities (e.g., Tokyo, London, Paris, New York City) to handle network connectivity timeouts, API rate limits, or offline mode.
*   **Safe Calculator ([calculate](file:///d:/AI Agent with Tool-Based Reasoning Using the ReAct Pattern/agent.py#L170))**:
    - Evaluates mathematical expressions using Python's `ast` (Abstract Syntax Tree) module through [safe_ast_eval](file:///d:/AI Agent with Tool-Based Reasoning Using the ReAct Pattern/agent.py#L133).
    - **Why it is safe**: It avoids using python's built-in `eval()`, which is vulnerable to malicious code injection. Instead, it parses the expression into syntax nodes and recursively evaluates only explicitly allowed operators (`+`, `-`, `*`, `/`, `**`, unary operators) and math functions (`factorial`, `sin`, `cos`, `tan`, `sqrt`, `log`, `exp`, `abs`, `round`).
    - **Resource Safety**: Prevents division by zero, limits exponents to `1000` (`right <= 1000`), and limits factorial arguments to `100` to prevent CPU hangs or memory exhaustion.
*   **Wikipedia Search ([search_wikipedia](file:///d:/AI Agent with Tool-Based Reasoning Using the ReAct Pattern/agent.py#L192))**:
    - Connects to the Wikipedia OpenSearch API to retrieve snippets from the top 3 articles matching a query. Clean HTML tags and decode HTML entities automatically.

### 2. JSON Schema Tool Definitions
Every tool is documented in **[TOOL_SCHEMAS](file:///d:/AI Agent with Tool-Based Reasoning Using the ReAct Pattern/agent.py#L235)** using JSON schemas that specify the tool's name, description, properties, parameter types, and required parameters. 
> [!NOTE]
> For compatibility with Gemini's strict API requirements, the parameter types are automatically converted to uppercase formats (`STRING`, `OBJECT`) prior to payload construction.

### 3. ReAct Agent Loop
The core execution engine is **[run_agent](file:///d:/AI Agent with Tool-Based Reasoning Using the ReAct Pattern/agent.py#L661)**. It alternates between calling the LLM API provider and calling the requested tools. Results are logged to the console using the `rich` library to print clear, labeled blocks representing `Thought`, `Action`, `Observation`, and `Final Answer`.

### 4. Providers & Offline Simulation Mode
- **Google Gemini & OpenAI Integrations**: The agent makes direct HTTP requests to the Gemini (`gemini-3.1-flash-lite` or customized model) and OpenAI (`gpt-4o-mini` or customized model) APIs, handling context history assembly, system prompt injection, and tool call responses.
- **Deterministic Offline Simulation ([SimulationLLM](file:///d:/AI Agent with Tool-Based Reasoning Using the ReAct Pattern/agent.py#L500))**: If no API keys are provided, the script runs in simulation mode. It intercepts known prompts (like the weather + factorial multi-tool query) and executes a predefined thought-action-observation trace. This allows verifying the entire execution logic, state management, console printing, and loop constraints completely offline without LLM charges.

---

## 🚀 Setup & Installation Guide

Follow these steps to set up and run the project:

### Step 1: Clone or Navigate to the Directory
Open your terminal (PowerShell, Command Prompt, or Bash) and navigate to the project directory:
```powershell
cd "d:\AI Agent with Tool-Based Reasoning Using the ReAct Pattern"
```

### Step 2: Set Up a Python Virtual Environment (Recommended)
Isolating dependencies inside a virtual environment prevents conflicts with global packages.

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Required Dependencies
Install the Python packages necessary for live API calls, environment variable loading, and styled console outputs:
```powershell
pip install requests python-dotenv rich
```

### Step 4: Configure API Credentials
1. Duplicate the example configuration file to create your active `.env` file:
   ```powershell
   copy .env.example .env
   ```
2. Open the newly created `.env` file and define your API key:
   - To use Gemini (default): Replace the value of `GEMINI_API_KEY` with your API key from [Google AI Studio](https://aistudio.google.com/).
   - To use OpenAI: Uncomment and define `OPENAI_API_KEY` with your API key from the [OpenAI Platform](https://platform.openai.com/).

---

## 🏃 How to Run the Agent

You can run the agent in different modes using the command-line interface.

### 1. Run in Offline Simulation Mode (No API Key Required)
If you do not have an API key configured in `.env`, the agent will run in deterministic simulation mode. Try the sample multi-tool prompt:
```powershell
python agent.py --prompt "What's the weather in New York City, and what is 5 factorial?"
```

### 2. Run with Live LLM Providers (API Key Required)
Ensure you configured your API keys in the `.env` file.

**Run with Google Gemini (Default):**
```powershell
python agent.py --prompt "Compare the weather in London and Paris, and calculate the absolute difference in Celsius" --provider gemini
```

**Run with OpenAI:**
```powershell
python agent.py --prompt "Who was Ada Lovelace on Wikipedia and what is 12 divided by 3?" --provider openai
```

### 3. Customize Execution Controls
- **Change Model**: Run with a specific model version using `--model`:
  ```powershell
  python agent.py --prompt "Calculate 3 raised to the power of 8" --provider gemini --model gemini-1.5-flash
  ```
- **Verify Safety Loop Halt**: Restrict the agent's maximum steps to force a termination halt before the final response is generated. Setting `--max-steps 1` will halt the multi-tool prompt after the weather tool is executed:
  ```powershell
  python agent.py --prompt "What's the weather in New York City, and what is 5 factorial?" --max-steps 1
  ```

---

## 📊 Sample Execution Traces

### Live Multi-Tool Execution Trace (`New York City` + `5!`)
When executed with Gemini, the terminal displays the following reasoning structure:

```text
┌───────────────────────────── 🚀 Starting Agent ─────────────────────────────┐
│ Initializing ReAct Loop using Provider: GEMINI                              │
│ Prompt: 'What's the weather in New York City, and what is 5 factorial?'     │
└─────────────────────────────────────────────────────────────────────────────┘
--- Step 1/10 ---
┌────────────────────────────────── Thought ──────────────────────────────────┐
│ I need to retrieve the current weather in New York City and evaluate the    │
│ factorial of 5. I will start by checking the weather in New York City.      │
└─────────────────────────────────────────────────────────────────────────────┘
┌────────────────────────────────── Action ───────────────────────────────────┐
│ Call Tool: get_weather                                                      │
│ Arguments: {                                                                │
│   "city": "New York City"                                                   │
│ }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────── Observation ────────────────────────────────┐
│ Weather in New York City: Clear , Temperature: 26°C (79°F), Humidity: 35%,  │
│ Wind Speed: 11 km/h                                                         │
└─────────────────────────────────────────────────────────────────────────────┘

--- Step 2/10 ---
┌────────────────────────────────── Thought ──────────────────────────────────┐
│ Now that I have the weather data, I will evaluate the mathematical expression│
│ 5 factorial using the calculate tool.                                       │
└─────────────────────────────────────────────────────────────────────────────┘
┌────────────────────────────────── Action ───────────────────────────────────┐
│ Call Tool: calculate                                                        │
│ Arguments: {                                                                │
│   "expression": "factorial(5)"                                              │
│ }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────── Observation ────────────────────────────────┐
│ 120                                                                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────── Final Answer ────────────────────────────────┐
│ Agent reached final answer:                                                 │
│                                                                             │
│ The current weather in New York City is clear with a temperature of 26°C    │
│ (79°F), 35% humidity, and a wind speed of 11 km/h. Additionally, 5          │
│ factorial (5!) is 120.                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Safety Stop Execution Trace (`--max-steps 1`)
If execution steps are exceeded, the agent halts:
```text
┌───────────────────────────── 🚀 Starting Agent ─────────────────────────────┐
│ Initializing ReAct Loop using Provider: GEMINI                              │
│ Prompt: 'What's the weather in New York City, and what is 5 factorial?'     │
└─────────────────────────────────────────────────────────────────────────────┘
--- Step 1/1 ---
┌────────────────────────────────── Thought ──────────────────────────────────┐
│ I will retrieve the current weather in New York City first.                 │
└─────────────────────────────────────────────────────────────────────────────┘
┌────────────────────────────────── Action ───────────────────────────────────┐
│ Call Tool: get_weather                                                      │
│ Arguments: {                                                                │
│   "city": "New York City"                                                   │
│ }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────── Observation ────────────────────────────────┐
│ Weather in New York City: Clear , Temperature: 26°C (79°F), Humidity: 35%,  │
│ Wind Speed: 11 km/h                                                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────── ⚠️ Execution Stopped ─────────────────────────────┐
│ Max steps reached without completing the task.                              │
└─────────────────────────────────────────────────────────────────────────────┘
```
