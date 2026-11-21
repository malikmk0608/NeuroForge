# Optional OpenAI interpretation

For the alternative Groq provider, use [GROQ_SETUP.md](GROQ_SETUP.md).
When explicitly selecting OpenAI, set `LLM_PROVIDER=openai` before starting
the server, in addition to its OPENAI_API_KEY and OPENAI_MODEL variables.

Current implementation uses OpenAI's Responses API with strict Structured Outputs.
It is optional: forms and deterministic planning continue without a model key.
The client code and simulated HTTP tests are implemented. A live synthetic
test was attempted on 2026-11-21; OpenAI returned HTTP 429, surfaced as an
actionable HTTP 503 from the AI service. Successful live extraction remains
unverified until API account limits permit a completed response.

Official references:

- [API quickstart and key setup](https://developers.openai.com/api/docs/quickstart)
- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)
- [GPT-4.1 mini capabilities](https://developers.openai.com/api/docs/models/gpt-4.1-mini)

GPT-4.1 mini is a configurable starting example supporting structured output,
not a claim that it is the newest or best model. Model access and available
API credits depend on the account. No live calls run during automated tests.

## Configure locally

Create a key in the [OpenAI API dashboard](https://platform.openai.com/api-keys).
Keep it private. In the project's macOS zsh terminal, stop the existing server
with Control-C. Run the following steps separately, not as one pasted block.

First activate the environment from the project root:

```zsh
source .venv/bin/activate
```

Then run this single command:

```zsh
read -rs OPENAI_API_KEY
```

The terminal now waits for your key without displaying characters. Paste only
the actual API key and press Enter. Wait until the normal shell prompt returns.
Then run:

```zsh
export OPENAI_API_KEY
export OPENAI_MODEL=gpt-4.1-mini
python -m uvicorn app.main:app --reload --port 8000
```

The key is entered without echoing it and is not embedded in a command saved
in shell history. It stays in this terminal's environment; it is not persisted
by these instructions. Do not put a real key in frontend JavaScript, Git, screenshots,
chat, or a committed configuration file. `.env.example` documents the variable
names only; `.env` is ignored, and automatic `.env` loading is not implemented.

## Try explicit model interpretation

In `/docs`, use `POST /agent/plan`:

```json
{
  "message": "Could you give EF-1001 the MANAGER role?",
  "use_model": true
}
```

Expected with a working key/model: a draft plan and activity indicating
model-assisted extraction. Missing request details still produce questions.
The ordinary form uses typed inputs and does not call the model. Its optional
Use AI to fill form action explicitly calls the configured model instead.
Default API `use_model: false` remains deterministic with no provider call.

Setting `use_model: true` transmits the supplied message and structured details
to OpenAI. No employee database records, permission policies, or API key values
are included in the user input sent to the model. The key is only an Authorization
header. Requests set `store: false`; that flag is not a claim of zero provider
retention or a substitute for an organization's data policies.

## What the model can and cannot do

The schema allows only an action, employee code, target role, request metadata,
and clarification questions. No tools are supplied. It cannot return permission
changes, approvals, or apply commands through this schema. Backend lookup and
Python set comparison still determine the draft permission differences.

Local validation checks extracted codes against explicitly supplied message
codes, requires a named supported target role, validates details, checks textual
grounding, and identifies text/structured conflicts. Missing and unsupported
requests ask for clarification. Relative dates, employee names without codes,
archival, and onboarding still require clarification. This conservative approach
does not guarantee perfect intent recognition; review the draft before submission.

HTTP/provider failure, refusal, incomplete response, or invalid model output
returns HTTP 503 with a safe explanation and guidance to use the form. There is
no silent substitution of guessed output and no provider response-body logging.
Safe messages distinguish invalid credentials, denied access, insufficient quota
when explicitly identified by the provider, rate limiting, model/request rejection,
network/certificate failures, timeouts, and invalid output. Raw provider error
bodies and credentials are never returned to the caller.
The HTTP timeout is 20 seconds with one attempt; no automatic retries are made.

## Validation status

Automated tests simulate structured responses, schema mismatch, refusals,
incomplete responses, authentication errors, timeouts, missing configuration,
invented metadata, conflicts, and execution through the normal planning graph.
They do not establish live model quality. After configuring the account, test
several real sentences and review employee/action/role extraction and questions
before describing the live model integration as verified.
