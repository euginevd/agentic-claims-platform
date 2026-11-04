"""Maze agent on Amazon Bedrock AgentCore Runtime.

The agent itself (the tool, the loop and the limits) is reused unchanged from
app/maze/02_lambda_converse/handler.py. Only the hosting wrapper differs: an AgentCore app
instead of a Lambda handler.
"""

import os

import boto3
from bedrock_agentcore.runtime import BedrockAgentCoreApp, RequestContext
from handler import log, run_agent

app = BedrockAgentCoreApp()

# Created once per session's process and reused for every request in it.
# It signs requests with the runtime's IAM role, so there is no API key.
bedrock = boto3.client(
    "bedrock-runtime", region_name=os.environ.get("AWS_REGION", "ap-southeast-2")
)


@app.entrypoint
def invoke(payload, context: RequestContext):
    """Called for each request to /invocations. The payload is ignored: the task is fixed."""
    result = run_agent(bedrock, os.environ["MODEL_ID"])
    log(
        "finished",
        session=context.session_id,
        status=result["status"],
        steps=result["steps"],
        **result["usage"],
    )
    return result


if __name__ == "__main__":
    # Serves POST /invocations and GET /ping on port 8080, locally and on Runtime.
    app.run()
