# Maze agent on AgentCore Runtime (example)

The same maze agent as [`../02_lambda_converse`](../02_lambda_converse), hosted on **Amazon Bedrock AgentCore Runtime** instead of AWS Lambda.

**Status:** reference example, not deployed. The deployed agent is `../02_lambda_converse` on Lambda ([ADR 0001](../../../docs/adr/0001-lambda-and-bedrock-converse.md)). AgentCore becomes the host when agents need long runs, sessions, memory or a gateway.

## The key idea: same agent, different wrapper

```
app/maze/02_lambda_converse/handler.py        ← the agent: tool, loop, limits (unchanged)
   ├── lambda_handler()          ← Lambda wrapper
   └── used by
app/maze/04_agentcore_runtime/main.py      ← AgentCore wrapper: imports run_agent, nothing else new
```

The tool (`read_web_page` with its exact allowlist), the Converse loop, the 25-step cap and the token limits all live in `../02_lambda_converse/handler.py`. This folder adds **about 20 lines**: an AgentCore app with one entry point. Keeping the agent logic separate from the hosting wrapper is what makes moving between Lambda and AgentCore cheap.

## The code, step by step (`main.py`)

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp, RequestContext
from handler import log, run_agent
```
- `bedrock_agentcore` is AWS's SDK for AgentCore. `BedrockAgentCoreApp` is a small web app that speaks AgentCore Runtime's contract.
- `run_agent` and `log` come straight from the Lambda version.

```python
app = BedrockAgentCoreApp()
bedrock = boto3.client("bedrock-runtime", region_name=...)
```
- The app, and a Bedrock client created once and reused for every request in the session. There's no API key: requests are signed with the runtime's IAM role.

```python
@app.entrypoint
def invoke(payload, context: RequestContext):
    result = run_agent(bedrock, os.environ["MODEL_ID"])
    log("finished", session=context.session_id, ...)
    return result
```
- `@app.entrypoint` registers the function AgentCore calls for each request to **`POST /invocations`**.
- `payload` is the JSON the caller sent. It's **ignored on purpose**: the task is fixed, so callers can't inject a different prompt.
- `context.session_id` identifies the **session**. Each session runs in its own isolated environment on Runtime, and it's logged here so you can trace a run.
- The return value is sent back to the caller as JSON.

```python
if __name__ == "__main__":
    app.run()
```
- Serves the app on **port 8080**, with **`GET /ping`** (health check) and **`POST /invocations`** (the agent). It's the same on your laptop and on Runtime.

## Lambda vs AgentCore for this agent

| | Lambda (`../02_lambda_converse`) | AgentCore Runtime (this folder) |
|---|---|---|
| Entry point | `lambda_handler(event, context)` | `@app.entrypoint invoke(payload, context)` |
| Interface | Lambda invoke | HTTP: `POST /invocations`, `GET /ping` |
| Maximum run | 15 minutes | Long sessions (hours) |
| Sessions | None | Built in, isolated per session |
| Memory, Gateway, Identity, Policy | Build yourself | AgentCore services, ready to attach |
| Dependencies | `boto3` (in the runtime) | `bedrock-agentcore` + `boto3`, packaged |
| Moving parts | Function, role, log group | Runtime, endpoint, role, code package |
| Right for the maze? | **Yes**, simplest | Works, but more than it needs |

## Run it locally (no AWS needed for the health check)

```powershell
cd C:\agentic-claims-platform
uv sync
$env:PYTHONPATH = "app\maze\02_lambda_converse"
uv run python app\maze\04_agentcore_runtime\main.py
# In another terminal:
curl http://127.0.0.1:8080/ping     # {"status":"Healthy",...}
```

Calling `POST /invocations` locally runs the agent for real, so it needs AWS credentials and `MODEL_ID` set, and it costs a few cents in Bedrock tokens.

## Deploying (later)

1. **Package:** `main.py`, `../02_lambda_converse/handler.py` and the packages in `requirements.txt`, built for **Linux arm64, Python 3.12**.
2. **Deploy:** either the **AgentCore CLI** (as the course does in 3.4), or **Terraform**: the AWS provider has `aws_bedrockagentcore_agent_runtime` and `aws_bedrockagentcore_agent_runtime_endpoint`, plus resources for Gateway, Memory and Policy. Terraform keeps it consistent with the rest of this repo.
3. **IAM:** the runtime's role may invoke only the one Bedrock model and write its own logs.
4. **Invoke:** with boto3, `bedrock-agentcore` client → `invoke_agent_runtime(agentRuntimeArn=..., runtimeSessionId=..., payload=...)`. Use a new session ID (for example a UUID) per run.

**Cost:** Runtime bills only while a session is working, so idle cost is about $0. The course notes that the AgentCore CLI's first deploy also creates a **KMS key at about $1 a month**; delete it when you tear down, or account for it (ADR 0003).
