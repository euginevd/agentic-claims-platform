# Maze agent on Lambda + Bedrock Converse (deployed)

The deployed version of the maze agent: Claude on Amazon Bedrock, called with the **Converse API** and a hand-written loop, hosted on **AWS Lambda**. Deployed by Terraform (`infra/terraform/modules/lambda-agent`). For how it compares with the other two versions, see [../README.md](../README.md).

## The code (`handler.py`)

| Part | What it does |
|---|---|
| Constants | The allowlisted host, 25-step cap, 3,000-character pages, 512-token replies, 10-second fetch timeout |
| `TOOL_CONFIG` | The tool described to the model in JSON: name, description and a required `url` string |
| `log()` | Writes one JSON log line, which you can query in CloudWatch Logs Insights |
| `read_web_page(url)` | Parses the URL and refuses anything but `https://maze.edwarddonner.com` (exact host, so no SSRF), then fetches and trims the page |
| `run_tool(tool_use)` | Runs the tool Claude asked for; any error goes back to Claude as text instead of crashing |
| `run_agent(client, model_id)` | **The loop:** call `converse` → add up tokens → if `stopReason` is `tool_use`, run the tools and send the results back → repeat until Claude answers or the cap is hit |
| `lambda_handler(event, context)` | Lambda's entry point. Ignores the event (fixed task), runs the agent and logs the result |

`run_agent` takes the Bedrock client as an argument, so tests pass a stub (`tests/test_maze_02_lambda_converse.py`) and `../maze_agent_core` reuses it unchanged on AgentCore.

## Run it

Deploy and test with the `terraform` workflow and `aws lambda invoke`: see [docs/DEPLOY.md](../../../docs/DEPLOY.md).
