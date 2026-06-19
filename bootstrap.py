#!/usr/bin/env python3
"""Scaffold the "Build an AI Customer Support Agent on AWS" workshop project.

Pure standard library — runs the same on Windows (Git Bash), macOS, and Linux.
Usage:
    python bootstrap.py        (or: python3 bootstrap.py)

Re-running is safe: existing files are left untouched so your edits survive.
"""
import os
import stat
import sys

# ---------------------------------------------------------------------------
# Every file the workshop needs, keyed by its relative path.
# The contents below match exactly what each module shows the learner.
# ---------------------------------------------------------------------------
FILES = {}

# ── requirements.txt ───────────────────────────────────────────────────────
FILES["requirements.txt"] = """\
strands-agents>=0.1.0
strands-agents-tools>=0.1.0
boto3>=1.38.0
python-dotenv>=1.0.0
"""

# ── .env (filled in as the learner progresses) ─────────────────────────────
FILES[".env"] = """\
AWS_REGION=us-east-1
TICKET_TABLE_NAME=support-tickets

# Filled in as you complete each module:
KNOWLEDGE_BASE_ID=
MEMORY_ID=
GUARDRAIL_ID=
GUARDRAIL_VERSION=DRAFT
"""

# ── docs/product-guide.txt ─────────────────────────────────────────────────
FILES["docs/product-guide.txt"] = """\
ACME SaaS Platform — Support Guide

PASSWORD RESET
To reset your password: go to Settings → Security → Reset Password.
An email will arrive within 5 minutes. Links expire after 24 hours.
If no email arrives, check your spam folder or contact support.

BILLING
We accept Visa, Mastercard, and American Express.
Invoices are generated on the 1st of each month and emailed to the billing contact.
To update payment details: Settings → Billing → Payment Methods.
Refunds are processed within 5-10 business days to the original payment method.

API RATE LIMITS
Free plan: 100 requests/minute.
Pro plan: 1,000 requests/minute.
Enterprise plan: 10,000 requests/minute + burst allowance.
Rate limit errors return HTTP 429. Use exponential backoff for retries.

INTEGRATIONS
Slack integration: Settings → Integrations → Slack → Connect.
GitHub integration: requires repo admin access to install the webhook.
Zapier: available on Pro and Enterprise plans only.

DATA EXPORT
Export all data: Settings → Data → Export. Generates a ZIP within 2 hours.
Exports include: all records, attachments, and audit logs.
Data is retained for 90 days after account cancellation.
"""

# ── docs/troubleshooting.txt ───────────────────────────────────────────────
FILES["docs/troubleshooting.txt"] = """\
ACME SaaS Platform — Troubleshooting Guide

CANNOT LOG IN
1. Check Caps Lock is off.
2. Try resetting your password (see product guide).
3. If using SSO, contact your IT admin — the issue may be with your identity provider.
4. Account may be locked after 10 failed attempts. Wait 15 minutes or contact support.

SLOW PERFORMANCE
- Clear browser cache and cookies.
- Try a different browser (Chrome and Firefox are fully supported).
- Check status.acme.com for any active incidents.
- Large data exports or bulk imports can slow the dashboard temporarily.

WEBHOOK NOT FIRING
- Verify the endpoint URL is publicly accessible (not localhost).
- Check the webhook secret matches what is configured in Settings → Integrations.
- Review the delivery log in Settings → Integrations → Webhook → Logs.
- Endpoints must respond with HTTP 200 within 10 seconds or the delivery is retried.

DATA NOT SYNCING
- Sync runs every 15 minutes on Pro, every 5 minutes on Enterprise.
- Force a manual sync: Settings → Data → Sync Now.
- If sync has been failing for more than 1 hour, contact support with your account ID.
"""

# ── lambda/create-ticket/index.py ──────────────────────────────────────────
FILES["lambda/create-ticket/index.py"] = '''\
import json, boto3, uuid
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("support-tickets")

def handler(event, context):
    body = event if isinstance(event, dict) else json.loads(event.get("body", "{}"))

    ticket_id = f"TKT-{str(uuid.uuid4())[:8].upper()}"
    item = {
        "ticketId":       ticket_id,
        "customerEmail":  body.get("customer_email", "unknown"),
        "subject":        body.get("subject", "Support Request"),
        "description":    body.get("description", ""),
        "priority":       body.get("priority", "normal"),
        "status":         "open",
        "createdAt":      datetime.now(timezone.utc).isoformat(),
    }

    table.put_item(Item=item)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "ticket_id": ticket_id,
            "message": f"Support ticket {ticket_id} created successfully.",
            "estimated_response": "4 hours for normal priority, 1 hour for high priority.",
        }),
    }
'''

# ── lambda/escalate/index.py ───────────────────────────────────────────────
FILES["lambda/escalate/index.py"] = '''\
import json, boto3, os
from datetime import datetime, timezone

sns = boto3.client("sns")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")

def handler(event, context):
    body = event if isinstance(event, dict) else json.loads(event.get("body", "{}"))

    customer_email = body.get("customer_email", "unknown")
    reason         = body.get("reason", "Customer requested human support")
    urgency        = body.get("urgency", "normal")
    summary        = body.get("conversation_summary", "No summary provided")

    message = f"""
ESCALATION ALERT - {urgency.upper()} PRIORITY
Time: {datetime.now(timezone.utc).isoformat()}

Customer: {customer_email}
Reason: {reason}

Conversation Summary:
{summary}

Please respond within {"1 hour" if urgency == "urgent" else "4 hours"}.
"""
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=f"[{urgency.upper()}] Support Escalation - {customer_email}",
        Message=message,
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Your request has been escalated to our support team.",
            "urgency": urgency,
            "response_time": "1 hour" if urgency == "urgent" else "4 hours",
        }),
    }
'''

# ── lambda/api-handler/index.py ────────────────────────────────────────────
FILES["lambda/api-handler/index.py"] = '''\
import json, os, sys

# Include the agent module — build_api_lambda.py packages agent.py alongside this file
sys.path.insert(0, "/var/task")

from agent import build_agent

def handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        message     = body.get("message", "").strip()
        customer_id = body.get("customer_id", "anonymous")

        if not message:
            return _response(400, {"error": "message is required"})

        agent = build_agent(customer_id=customer_id)
        result = agent(message)

        return _response(200, {
            "response":    str(result),
            "customer_id": customer_id,
        })

    except Exception as e:
        print(f"Error: {e}")
        return _response(500, {"error": "Internal server error"})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }
'''

# ── infra/lambda-trust-policy.json ─────────────────────────────────────────
FILES["infra/lambda-trust-policy.json"] = '''\
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "lambda.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
'''

# ── infra/lambda-permissions.json ──────────────────────────────────────────
FILES["infra/lambda-permissions.json"] = '''\
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["dynamodb:PutItem", "dynamodb:GetItem"],
      "Resource": "arn:aws:dynamodb:us-east-1:*:table/support-tickets"
    },
    {
      "Effect": "Allow",
      "Action": "sns:Publish",
      "Resource": "*"
    }
  ]
}
'''

# ── infra/agentcore-trust-policy.json ──────────────────────────────────────
FILES["infra/agentcore-trust-policy.json"] = '''\
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "bedrock.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
'''

# ── infra/agentcore-permissions.json ───────────────────────────────────────
FILES["infra/agentcore-permissions.json"] = '''\
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      "Resource": "*"
    },
    { "Effect": "Allow", "Action": ["bedrock:Retrieve"], "Resource": "*" },
    {
      "Effect": "Allow",
      "Action": ["lambda:InvokeFunction"],
      "Resource": "arn:aws:lambda:us-east-1:*:function:support-*"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "*"
    }
  ]
}
'''

# ── agent.py ───────────────────────────────────────────────────────────────
FILES["agent.py"] = '''\
import json, os, boto3
from strands import Agent, tool
from strands.models import BedrockModel
from dotenv import load_dotenv

load_dotenv()

REGION            = os.getenv("AWS_REGION", "us-east-1")
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID")
TICKET_TABLE      = os.getenv("TICKET_TABLE_NAME", "support-tickets")

GUARDRAIL_ID      = os.getenv("GUARDRAIL_ID", "")
GUARDRAIL_VERSION = os.getenv("GUARDRAIL_VERSION", "DRAFT")

lambda_client = boto3.client("lambda",                region_name=REGION)
kb_client     = boto3.client("bedrock-agent-runtime", region_name=REGION)


# -- Tool 1: Search the Knowledge Base ---------------------------------------

@tool
def search_knowledge_base(query: str) -> str:
    """Search the product documentation and support guides to answer customer questions.
    Use this tool FIRST before attempting to answer any product-related question.

    Args:
        query: The customer's question or topic to search for.
    """
    try:
        response = kb_client.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": 5}
            },
        )
        results = response.get("retrievalResults", [])
        if not results:
            return "No relevant documentation found for this query."

        chunks = []
        for r in results:
            if r.get("score", 0) > 0.3:
                chunks.append(r["content"]["text"])

        return "\\n\\n---\\n\\n".join(chunks) if chunks else "No sufficiently relevant documentation found."
    except Exception as e:
        return f"Knowledge base search failed: {str(e)}"


# -- Tool 2: Create Support Ticket -------------------------------------------

@tool
def create_ticket(
    customer_email: str,
    subject: str,
    description: str,
    priority: str = "normal",
) -> str:
    """Create a support ticket in the ticketing system when a customer requests one
    or when you cannot resolve their issue after searching the documentation.
    Priority should be 'high' for billing or login issues, 'normal' for everything else.

    Args:
        customer_email: The customer's email address.
        subject: A short, clear subject line for the ticket.
        description: A detailed description of the issue including steps already tried.
        priority: Ticket priority — 'normal' or 'high'.
    """
    try:
        response = lambda_client.invoke(
            FunctionName="support-create-ticket",
            Payload=json.dumps({
                "customer_email": customer_email,
                "subject": subject,
                "description": description,
                "priority": priority,
            }),
        )
        result = json.loads(response["Payload"].read())
        return json.loads(result.get("body", "{}")).get(
            "message", "Ticket created successfully."
        )
    except Exception as e:
        return f"Failed to create ticket: {str(e)}"


# -- Tool 3: Escalate to Human -----------------------------------------------

@tool
def escalate_to_human(
    customer_email: str,
    reason: str,
    urgency: str,
    conversation_summary: str,
) -> str:
    """Escalate the customer's issue to a human support agent via email alert.
    Use this when: (1) the customer is very frustrated, (2) the issue involves
    account security or data loss, (3) the customer explicitly asks for a human,
    or (4) you have been unable to resolve the issue after multiple attempts.

    Args:
        customer_email: The customer's email address.
        reason: Why you are escalating this conversation.
        urgency: 'urgent' for security/data issues, 'normal' for everything else.
        conversation_summary: A brief summary of the conversation and what was tried.
    """
    try:
        response = lambda_client.invoke(
            FunctionName="support-escalate",
            Payload=json.dumps({
                "customer_email": customer_email,
                "reason": reason,
                "urgency": urgency,
                "conversation_summary": conversation_summary,
            }),
        )
        result = json.loads(response["Payload"].read())
        return json.loads(result.get("body", "{}")).get(
            "message", "Escalated to support team."
        )
    except Exception as e:
        return f"Escalation failed: {str(e)}"


# -- System Prompt -----------------------------------------------------------

SYSTEM_PROMPT = """You are a helpful AI customer support agent for ACME SaaS Platform.

Your job:
1. Answer customer questions accurately using the search_knowledge_base tool.
   Always search before answering — do not guess from memory.
2. If you cannot find the answer after searching, create a support ticket using create_ticket.
3. If the customer is frustrated, has a security issue, or explicitly asks for a human,
   use escalate_to_human immediately.
4. Always be empathetic, concise, and clear. Use bullet points for step-by-step instructions.
5. If you create a ticket or escalate, tell the customer the ticket ID or expected response time.

Rules:
- Never make up product features or pricing not found in the documentation.
- Never ask for passwords or full payment card numbers.
- If unsure, create a ticket rather than guessing.
"""


# -- Build the Agent ---------------------------------------------------------

def build_agent(customer_id: str = None):
    """customer_id scopes memory per customer (use email or user id)."""
    guardrail_config = None
    if GUARDRAIL_ID:
        guardrail_config = {
            "guardrailIdentifier": GUARDRAIL_ID,
            "guardrailVersion":    GUARDRAIL_VERSION,
            "trace":               "enabled",
        }

    model = BedrockModel(
        model_id="anthropic.claude-sonnet-4-6",
        region_name=REGION,
        guardrail_config=guardrail_config,
    )

    memory = None
    if os.getenv("MEMORY_ID") and customer_id:
        try:
            from strands.memory import BedrockAgentCoreMemory
            memory = BedrockAgentCoreMemory(
                memory_id=os.getenv("MEMORY_ID"),
                session_id=customer_id,
                region_name=REGION,
            )
        except Exception as e:
            print(f"Memory disabled: {e}")

    return Agent(
        model=model,
        tools=[search_knowledge_base, create_ticket, escalate_to_human],
        system_prompt=SYSTEM_PROMPT,
        memory=memory,
    )


# -- Local interactive test --------------------------------------------------

if __name__ == "__main__":
    agent = build_agent()
    print("Agent ready. Type 'quit' to exit.\\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break
        response = agent(user_input)
        print(f"\\nAgent: {response}\\n")
'''

# ── scripts/set-env.sh ─────────────────────────────────────────────────────
FILES["scripts/set-env.sh"] = """\
#!/usr/bin/env bash
# Source this file at the start of every terminal session:
#   source scripts/set-env.sh
export MSYS_NO_PATHCONV=1     # Git Bash: stop it mangling file:// paths (no-op on macOS/Linux)
export AWS_REGION="us-east-1"
export AWS_PROFILE="workshop"
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
export DOCS_BUCKET="support-agent-docs-$AWS_ACCOUNT_ID"
export TICKET_TABLE_NAME="support-tickets"

# Uncomment and fill in as you create these resources:
# export KNOWLEDGE_BASE_ID="XXXXXXXXXX"
# export SNS_TOPIC_ARN="arn:aws:sns:us-east-1:...:support-escalations"

echo "Region : $AWS_REGION"
echo "Account: $AWS_ACCOUNT_ID"
echo "Bucket : $DOCS_BUCKET"
"""

# ── scripts/package_lambda.py ──────────────────────────────────────────────
FILES["scripts/package_lambda.py"] = '''\
#!/usr/bin/env python3
"""Zip a Lambda source folder into function.zip — cross-platform.
Usage: python scripts/package_lambda.py lambda/create-ticket"""
import os, sys, zipfile

def package(src_dir):
    out = os.path.join(src_dir, "function.zip")
    if os.path.exists(out):
        os.remove(out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(src_dir):
            for name in files:
                if name == "function.zip":
                    continue
                full = os.path.join(root, name)
                # arcname must be flat/relative so Lambda finds index.py at the root
                z.write(full, os.path.relpath(full, src_dir))
    print(f"Created {out}")

if __name__ == "__main__":
    package(sys.argv[1])
'''

# ── scripts/build_api_lambda.py ────────────────────────────────────────────
FILES["scripts/build_api_lambda.py"] = '''\
#!/usr/bin/env python3
"""Bundle the API handler + agent.py + dependencies into function.zip.
Cross-platform — no cp, no zip, no shell. Run: python scripts/build_api_lambda.py"""
import os, shutil, subprocess, sys, zipfile

ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC   = os.path.join(ROOT, "lambda", "api-handler")
BUILD = os.path.join(SRC, "build")
ZIP   = os.path.join(SRC, "function.zip")

# 1. Fresh build dir
shutil.rmtree(BUILD, ignore_errors=True)
os.makedirs(BUILD)

# 2. Copy handler + agent.py (shutil.copy works on every OS)
shutil.copy(os.path.join(SRC, "index.py"), BUILD)
shutil.copy(os.path.join(ROOT, "agent.py"), BUILD)

# 3. Install dependencies into the build dir
subprocess.check_call([
    sys.executable, "-m", "pip", "install", "--quiet",
    "strands-agents", "strands-agents-tools", "boto3", "python-dotenv",
    "--target", BUILD,
])

# 4. Zip everything at the build-dir root (flat — Lambda requirement)
if os.path.exists(ZIP):
    os.remove(ZIP)
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for base, _, files in os.walk(BUILD):
        for name in files:
            full = os.path.join(base, name)
            z.write(full, os.path.relpath(full, BUILD))
print(f"Built {ZIP}")
'''

# ── scripts/test_kb.py ─────────────────────────────────────────────────────
FILES["scripts/test_kb.py"] = '''\
import os, boto3
from dotenv import load_dotenv

load_dotenv()  # reads KNOWLEDGE_BASE_ID from .env — no shell exports needed

kb_client = boto3.client(
    "bedrock-agent-runtime",
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)

response = kb_client.retrieve(
    knowledgeBaseId=os.environ["KNOWLEDGE_BASE_ID"],
    retrievalQuery={"text": "How do I reset my password?"},
    retrievalConfiguration={
        "vectorSearchConfiguration": {"numberOfResults": 3}
    },
)

for result in response["retrievalResults"]:
    print("Score:", round(result["score"], 3))
    print("Content:", result["content"]["text"][:200])
    print("---")
'''

# ── scripts/create_memory.py ───────────────────────────────────────────────
FILES["scripts/create_memory.py"] = '''\
import boto3, os
from dotenv import load_dotenv

load_dotenv()
REGION = os.getenv("AWS_REGION", "us-east-1")

agentcore = boto3.client("bedrock-agentcore", region_name=REGION)

response = agentcore.create_memory(
    name="support-agent-memory",
    description="Long-term memory for the support agent - stores customer plan, issues, and preferences",
    memoryConfiguration={
        "extractionConfiguration": {
            "type": "SEMANTIC",
        },
        "retentionDays": 90,
    },
)

memory_id = response["memoryId"]
print(f"Memory store created: {memory_id}")
print(f"Add to .env: MEMORY_ID={memory_id}")
'''

# ── test_memory.py (project root — imports agent.py) ───────────────────────
FILES["test_memory.py"] = '''\
import os
from agent import build_agent   # lives at project root alongside this script
from dotenv import load_dotenv

load_dotenv()

CUSTOMER = "alice@example.com"

print("=== Session 1 ===")
agent1 = build_agent(customer_id=CUSTOMER)
r1 = agent1("Hi, I'm on the Enterprise plan and I'm seeing rate limit errors on the API")
print(f"Agent: {r1}")

print("\\n=== Session 2 (new agent instance, same customer) ===")
agent2 = build_agent(customer_id=CUSTOMER)
r2 = agent2("Hi, any updates on my API issue?")
print(f"Agent: {r2}")
# The agent should recall Enterprise plan and rate limit context from Session 1
'''

# ── scripts/test_runner.py ─────────────────────────────────────────────────
FILES["scripts/test_runner.py"] = '''\
#!/usr/bin/env python3
"""End-to-end tester for the support agent API. Cross-platform (stdlib only).
Usage: python scripts/test_runner.py https://XXXX.execute-api.us-east-1.amazonaws.com/prod"""
import json, sys, urllib.request

API_URL = sys.argv[1].rstrip("/")
EMAIL   = "demo@example.com"

def ask(message):
    payload = json.dumps({"message": message, "customer_id": EMAIL}).encode()
    req = urllib.request.Request(
        f"{API_URL}/chat", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=130) as r:
        body = json.loads(r.read())
    print(f"You  : {message}")
    print(f"Agent: {body.get('response', body)}\\n")

TESTS = [
    ("Knowledge Base (RAG)", "How do I reset my password?"),
    ("Knowledge Base (RAG)", "What are the API rate limits on the Pro plan?"),
    ("Ticket Creation",      "I have been unable to sync my data for 3 hours. Please create a support ticket."),
    ("Escalation",           "My account data has disappeared and I'm very worried. I need a human immediately."),
    ("Memory recall",        "Hi, what issues have I previously reported?"),
    ("Guardrail",            "How does ACME compare to HubSpot?"),
]

for label, message in TESTS:
    print(f"====== {label} ======")
    ask(message)
print("====== ALL TESTS COMPLETE ======")
'''

# ── README.md (orientation for anyone who clones the repo directly) ─────────
FILES["README.md"] = """\
# Support Agent Workshop — Starter

Scaffold for the **Build an AI Customer Support Agent on AWS** workshop
(Amazon Bedrock AgentCore + Claude).

## Quick start

```bash
python bootstrap.py        # creates the full project (use python3 if needed)
python -m venv .venv
source .venv/bin/activate  # Git Bash on Windows: same path works
pip install -r requirements.txt
source scripts/set-env.sh  # loads shared AWS env vars
```

Then follow the workshop modules. Windows users: run everything inside
**Git Bash** (installed with Git for Windows) from the VS Code terminal.

`bootstrap.py` never overwrites files you have already edited, so it is safe
to re-run.
"""


# ---------------------------------------------------------------------------
def main():
    root = os.path.dirname(os.path.abspath(__file__))
    created = 0
    skipped = 0
    for rel_path, content in FILES.items():
        full = os.path.join(root, *rel_path.split("/"))
        parent = os.path.dirname(full)
        if parent:
            os.makedirs(parent, exist_ok=True)
        # Do not clobber files the learner has already edited.
        if os.path.exists(full):
            print(f"  skip (exists): {rel_path}")
            skipped += 1
            continue
        # newline="\n" forces Unix line endings so files work on AWS Lambda
        # regardless of the OS that generated them.
        with open(full, "w", newline="\n", encoding="utf-8") as f:
            f.write(content)
        # Make shell scripts executable on macOS/Linux (harmless elsewhere).
        if rel_path.endswith(".sh"):
            os.chmod(full, os.stat(full).st_mode | stat.S_IEXEC)
        print(f"  created: {rel_path}")
        created += 1

    print(f"\nScaffold complete — {created} created, {skipped} skipped.")
    print("Next: create a venv, install requirements.txt, then source scripts/set-env.sh")


if __name__ == "__main__":
    sys.exit(main())
