# Groq model setup

Groq is an alternative provider for the same extraction schema and local
validation. Official [Structured Outputs documentation](https://console.groq.com/docs/structured-outputs)
lists `openai/gpt-oss-20b` as supporting strict mode. The API call goes to Groq,
not OpenAI; the model ID prefix does not change the provider destination.
Groq also has [account rate limits](https://console.groq.com/docs/rate-limits).
No provider is guaranteed free of quota, availability, or rate-limit errors.

The Groq adapter is tested with simulated HTTP responses. On 2026-11-21,
the user supplied a successful live HTTP 200 response from the configured
Groq path for "Could you give EF-1001 the MANAGER role?". It extracted
ROLE_CHANGE / EF-1001 / MANAGER, generated the expected permission differences
using mock backend data, and asked for the four omitted details. This is one
successful live smoke test, not a comprehensive model-quality evaluation.

## Set up in macOS zsh

Create your own key at <https://console.groq.com/keys>. Never paste it in chat.
In the terminal running your port-8002 server, press Control-C to stop it.
If using a new terminal, first run:

```zsh
cd /Users/malikfamilymacbook/Documents/ChatGPT/AIAgent
source .venv/bin/activate
```

Run this one line by itself:

```zsh
read -rs GROQ_API_KEY
```

Paste only the actual Groq key into the waiting line, then press Enter. No
characters will be displayed. Once the normal shell prompt returns, run:

```zsh
export GROQ_API_KEY
export LLM_PROVIDER=groq
export GROQ_MODEL=openai/gpt-oss-20b
python -m uvicorn app.main:app --reload --port 8002
```

The app reads environment variables; it does not automatically read `.env`.
The key stays in this terminal's environment and is not persisted by these
commands. Keeping an old OPENAI_API_KEY variable does not affect Groq selection;
the adapter sends only GROQ_API_KEY to Groq's fixed HTTPS endpoint.

## Test

Open <http://127.0.0.1:8002/docs#/default/plan_agent_plan_post>. Expand
**POST /agent/plan**, click Try it out, and enter:

```json
{
  "message": "Could you give EF-1001 the MANAGER role?",
  "use_model": true
}
```

Confirm the Request URL ends in `/agent/plan`, then Execute. This transmits
the synthetic test message to Groq. A successful draft should identify
EF-1001 and MANAGER, show permission differences, and ask for missing details.
It will not submit, approve, or apply any access request.

The supplied message and structured details go to the selected provider;
employee database records and policies are not added to model input. Review
the provider's data policies before using real employee information. No tools
are supplied, and the same typed validation and deterministic permission math
run after extraction. Invalid/refused/truncated responses and HTTP failures
produce safe HTTP 503 responses. No automatic provider fallback occurs.

The local form now has an optional **Describe the request / Use AI to fill form**
section. It sends the description with `use_model: true`, fills extracted fields,
and displays missing-detail questions. Review and complete the fields, then use
the ordinary Generate access plan button. That ordinary button is deterministic;
default API `use_model: false` also makes no provider call. A configured-provider
badge indicates configuration, not a live availability guarantee.

The final eight-case live Groq run passed after prompt refinement; saved results
are in `live-smoke-results.json`. The initial run over-clarified one polite role
change; no permissions were applied. Broader arbitrary-language quality is not
established by these smoke tests.

To switch back to OpenAI deliberately, set LLM_PROVIDER=openai
and configure its separate key/model variables as documented in MODEL_SETUP.md.
