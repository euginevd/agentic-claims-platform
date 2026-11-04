# Maze agent with the Anthropic SDK (alternative)

The same maze agent as [`../02_lambda_converse`](../02_lambda_converse), written with the **Anthropic Python SDK's tool runner** rather than a hand-written loop on Bedrock's Converse API.

**Status:** reference code, not deployed. The deployed agent is `../02_lambda_converse` (see [ADR 0001](../../../docs/adr/0001-lambda-and-bedrock-converse.md)). This version needs a packaging step before Terraform can deploy it (see below).

## What it does

Claude reads a page of the maze, picks a link, reads the next page, and keeps going until it finds the final message, using one tool (`read_web_page`) for at most 25 steps.

```
Lambda (handler.py)
  └─ tool runner (Anthropic SDK) ──► Claude on Amazon Bedrock (Sydney)
        │   ▲
        ▼   │  tool calls and results
     read_web_page ──► https://maze.edwarddonner.com only
```

## The code, step by step

### 1. The client

```python
client = AnthropicBedrockMantle(aws_region=os.environ.get("AWS_REGION", "ap-southeast-2"))
```

- `AnthropicBedrockMantle` is the SDK's client for Claude on Bedrock (the Messages API endpoint). After it's created, it has the same `messages` methods as the first-party client.
- **No API key:** it signs requests with the Lambda's IAM role.
- It's created **outside** the handler, so it's reused across invocations of a warm Lambda container.

### 2. The tool

```python
@beta_tool
def read_web_page(url: str) -> str:
    """Read a page of the maze and return its text, including its links.

    Args:
        url: The full https URL of a maze page.
    """
```

- `@beta_tool` turns an ordinary function into a tool. The SDK builds the JSON schema from the **type hints** (`url: str`) and the **docstring**: the first line is the tool's description, and `Args:` describes each parameter. The model only ever sees this description, never the Python.
- **Exact allowlist:** the URL is parsed, and it must be `https` with the hostname exactly `maze.edwarddonner.com`. A plain `startswith` check (as in the course's `setup.ipynb`) would also let `https://maze.edwarddonner.com.evil.io` through, which is an SSRF gap.
- **Limits:** a 10-second fetch timeout, and pages cut to 3,000 characters, because every step resends the whole history.
- A refusal is returned as text, so the model reads it and corrects itself. If the function raises an exception, the tool runner sends the error back to the model instead of crashing.

### 3. The loop: the tool runner

```python
runner = client.beta.messages.tool_runner(
    model=os.environ["MODEL_ID"],
    max_tokens=MAX_OUTPUT_TOKENS,
    max_iterations=MAX_STEPS,
    system=SYSTEM_PROMPT,
    tools=[read_web_page],
    messages=[{"role": "user", "content": TASK}],
)
for message in runner:
    ...
```

The tool runner is the harness. Each iteration:

1. calls Claude with the conversation so far,
2. if Claude asks for a tool (`stop_reason == "tool_use"`), runs `read_web_page` with Claude's arguments,
3. appends the tool result to the conversation, and goes round again.

It stops when Claude answers without a tool call (`end_turn`) or after `max_iterations` (25) calls, the step cap. This is the same loop as `run_agent()` in the course's `setup.ipynb` and `run_agent()` in `../02_lambda_converse/handler.py`, but the SDK writes it for you.

### 4. Usage and logs

- Each iteration yields one model response. The handler adds up `usage.input_tokens` and `usage.output_tokens` across them for the total cost of the run.
- It writes one JSON log line per step and one at the end, which you can query in CloudWatch Logs Insights.
- If Claude is still asking for a tool after the last iteration, the status is `step_limit`.

### 5. Security choices

- **Fixed task:** the Lambda event is ignored, so callers can't change what the agent does (no prompt injection through the request).
- **No public endpoint:** invoked with `aws lambda invoke`, controlled by IAM.
- **Least privilege:** the role should allow invoking only this one model.

## Compared with the Converse version

| | `../02_lambda_converse` (Converse) | `03_lambda_claude_sdk` (tool runner) |
|---|---|---|
| Library | `boto3`, already in the Lambda runtime | `anthropic`, **must be bundled** |
| Loop | Written by hand | The SDK's tool runner |
| Tool schema | JSON written by hand | Generated from the function |
| Code | About 70 lines | About 40 lines |
| Maturity | GA API | Tool runner is a **beta** SDK helper |
| Best for | Small agents, no dependencies | Agents with many tools |

## Before deploying it

1. **Package the SDK.** Lambda doesn't include `anthropic`. Build the zip with its dependencies for the Lambda platform (arm64, Python 3.12):
   ```bash
   pip install -r requirements.txt -t build/ --platform manylinux2014_aarch64 --only-binary=:all: --python-version 3.12
   cp handler.py build/
   ```
   In Terraform, point the `lambda-agent` module's `source_dir` at `build/`, or build a Lambda layer in CI.
2. **Model ID.** Bedrock IDs take an `anthropic.` prefix, for example `anthropic.claude-haiku-5-5` (cheap, enough for the maze). Check in the Bedrock console that the model is available in **ap-southeast-2**; if only a cross-region inference profile is offered, check where it routes (data residency).
3. **IAM.** The Mantle client uses Bedrock's Messages API endpoint. Check the Bedrock documentation for the IAM actions and resource ARNs it needs, because they may differ from `bedrock:InvokeModel` on the Converse path. Keep the policy scoped to the one model.
4. **Pin the SDK.** `requirements.txt` pins the major version, because the tool runner is beta.

## Test it (after deployment)

```bash
aws lambda invoke --function-name acp-dev-maze-agent-sdk --cli-read-timeout 310 out.json && cat out.json
aws logs tail /aws/lambda/acp-dev-maze-agent-sdk --since 15m
```
