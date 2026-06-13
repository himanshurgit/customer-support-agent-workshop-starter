# Customer Support Agent — Workshop Starter

Starter scaffold for the **Build an AI Customer Support Agent on AWS** workshop —
an AI agent powered by **Amazon Bedrock AgentCore** and **Claude** that reads your
product docs (RAG), remembers customers across sessions, creates support tickets,
and escalates to a human when needed.

This repo contains a single self-contained script, [`bootstrap.py`](bootstrap.py),
that generates the entire project — every folder, code file, IAM policy, and helper
script — so every learner starts from an identical, working baseline on **Windows,
macOS, or Linux**.

---

## Prerequisites

- **Python 3.11+**
- **AWS CLI v2**, configured with a profile that has `AdministratorAccess`
- An **AWS account with Amazon Bedrock model access** enabled for Claude Sonnet 4
  and Titan Embeddings V2 (in `us-east-1`)
- **Git** (optional — there is a no-Git download path below)
- **Windows users:** run everything in **Git Bash** (installed with
  [Git for Windows](https://git-scm.com/download/win)) from the
  [VS Code](https://code.visualstudio.com) terminal. Git Bash is real bash, so every
  command in the workshop runs unchanged.

---

## Quick start

```bash
# 1. Get this scaffold
git clone https://github.com/himanshurgit/customer-support-agent-workshop-starter.git
cd customer-support-agent-workshop-starter

# 2. Generate the full project (use python3 if that is your interpreter)
python bootstrap.py

# 3. Create a virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate        # Git Bash on Windows: same path works
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Load shared AWS environment variables (run in every new terminal)
source scripts/set-env.sh
```

Then follow the workshop modules.

### No Git? Download just the script

```bash
mkdir customer-support-agent-workshop-starter && cd customer-support-agent-workshop-starter
curl -O https://raw.githubusercontent.com/himanshurgit/customer-support-agent-workshop-starter/main/bootstrap.py
python bootstrap.py
```

---

## What `bootstrap.py` generates

```
.
├── agent.py                      # the AI agent (Strands SDK): tools + system prompt
├── requirements.txt
├── .env                          # config, filled in as you progress
├── test_memory.py                # cross-session memory test (imports agent.py)
├── docs/
│   ├── product-guide.txt         # sample product documentation (RAG source)
│   └── troubleshooting.txt
├── lambda/
│   ├── create-ticket/index.py    # tool: write a ticket to DynamoDB
│   ├── escalate/index.py         # tool: send an SNS escalation email
│   └── api-handler/index.py      # HTTP entry point that invokes the agent
├── infra/
│   ├── lambda-trust-policy.json
│   ├── lambda-permissions.json
│   ├── agentcore-trust-policy.json
│   └── agentcore-permissions.json
└── scripts/
    ├── set-env.sh                # shared env vars (sets MSYS_NO_PATHCONV=1 for Git Bash)
    ├── package_lambda.py         # cross-platform Lambda zipper
    ├── build_api_lambda.py       # bundles agent + deps for the API Lambda
    ├── test_kb.py                # verify the Knowledge Base returns results
    ├── create_memory.py          # create the AgentCore memory store
    └── test_runner.py            # end-to-end API tester (stdlib only)
```

Re-running `bootstrap.py` is safe — it **never overwrites files you have already
edited** (existing files are skipped). Generated files use Unix line endings so they
work on AWS Lambda regardless of the OS that created them.

---

## Architecture

```
Customer -> API Gateway -> Lambda -> Bedrock AgentCore Runtime
                                     |-- Claude (claude-sonnet-4-6)
                                     |-- Memory   (remembers customers across sessions)
                                     |-- Knowledge Base (RAG over your S3 docs)
                                     |-- tool: create_ticket    -> Lambda -> DynamoDB
                                     +-- tool: escalate_to_human -> Lambda -> SNS email
```

---

## Cleanup

Several resources cost money if left running — especially the OpenSearch Serverless
collection behind the Knowledge Base. The final workshop module walks through deleting
everything. Always tear down your workshop resources when you are done.
