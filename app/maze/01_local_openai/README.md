# 01 · Local script with the OpenAI SDK

The simplest version: one Python file on your laptop, calling an **OpenAI** model with the **OpenAI Python SDK** and an **API key in `.env`**. No AWS, no Terraform, no deployment. It's the course's `setup.ipynb` maze agent turned into a script, with the stricter allowlist from the AWS versions.

For how it compares with the other versions, see [../README.md](../README.md).

## Run it

```powershell
cd C:\agentic-claims-platform
uv sync
copy app\maze\01_local_openai\.env.example app\maze\01_local_openai\.env   # then paste your key into .env
uv run python app\maze\01_local_openai\maze.py
```

- Put `OPENAI_API_KEY=sk-...` in `.env`, either in this folder or at the repo root. `.env` is git-ignored, and gitleaks and push protection block keys anyway. Never commit a key.
- `MODEL` in `.env` picks the OpenAI model (default `gpt-6-luna`, small and cheap). Check the model ID in your OpenAI account if it's rejected.
- **Same code, other providers:** set `OPENAI_BASE_URL` to any OpenAI-compatible API (for example OpenRouter, or Ollama on your machine) with that provider's key and model ID.

## The code (`maze.py`)

| Part | What it does |
|---|---|
| `DEFAULT_MODEL` | The model used unless `MODEL` is set |
| Constants | Allowlisted host, 25-step cap, 3,000-character pages, 10-second fetch timeout |
| `TOOLS` | The tool described in OpenAI's JSON format (`type: function`, name, description, parameters) |
| `read_web_page(url)` | Exact allowlist: `https` and host `maze.edwarddonner.com` only, so look-alike hosts are refused |
| `run_tool(tool_call)` | Parses the model's JSON arguments, runs the tool, returns a `role: tool` message; errors go back to the model as text |
| `run_agent(client, model)` | **The loop:** `chat.completions.create` with tools → add up tokens → if `tool_calls`, run them and append the results → if text, done → an empty reply goes round again → stop at 25 steps |
| `main()` | `load_dotenv()` reads `.env`, checks `OPENAI_API_KEY` is set, builds the client with `timeout=120, max_retries=5` (it reads the key and any `OPENAI_BASE_URL` itself), runs the agent, prints the result as JSON |

`run_agent` takes the client as an argument, so `tests/test_maze_01_local_openai.py` passes a stub and never calls the network.

## When to use it, and when not

**Use it for:**
- learning and experimenting: change the prompt, model or limits and rerun in seconds
- comparing models quickly before choosing one for production
- demos on your own machine

**Don't use it for production:**
- **The API key** sits in a file on a laptop; production uses IAM roles (no keys) or Secrets Manager.
- **Data path:** requests go to OpenAI's API (US by default), so data residency and retention follow OpenAI's terms. Regulated and government clients usually need Bedrock or Azure OpenAI in an Australian region.
- **No controls:** no CI/CD deployment, audit trail, budget cap or access control.

The usual path is to **prototype here, then run the agent in the cloud** with versions 02 to 04.
