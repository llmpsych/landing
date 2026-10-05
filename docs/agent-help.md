# Agent-help pilot

Landing owns the complete service, UI, machine entry and native deployment declaration.
Existing llmpsych.com and `llp-web-landing` are unchanged. The intended supported URL is
**https://help.web.llmpsych.1puni.com/**. A declaration is not evidence of publication,
target convergence, or a successful live conversation.

## Entities, lifecycle and authority

A participant voluntarily supplies a difficulty, minimal context and desired change.
A shared pilot admission code permits creation, but never reading another session.
Each session is one canonical JSON document in SQLite, indexed by a SHA-256 hash of
its random 256-bit capability. The raw capability is returned once, never stored
server-side. The UI holds it in page memory only; save it privately for follow-up.
There are no cookies, URL tokens, accounts, inbox integrations or session listings.
An observer can watch the consenting participant's browser or receive their session
key explicitly; there is no separate operator access API.

`discussion` (1–4 model turns) → `experiment` (one proposal) → `complete` (one review).
Only the server selects legal transitions. The model returns text and four experiment
fields: change, measure, stop_condition, review_when. It has no shell, tools, retrieval,
controller credentials or ability to execute the proposed experiment. The participant
retains responsibility for assessing a proposal within existing authority. Prompt
instructions guide language, but are not a clinical or output-safety guarantee.

Session versions provide optimistic concurrency. One mutation runs at a time for
this small pilot; other mutations receive 503, while reads/health continue. After a
lost response, GET first: an already committed version cannot be appended twice.
An interrupted provider request may incur provider cost without a committed reply;
we do not claim exactly-once billing. SQLite transactions commit complete turns and
survive restart. Quotas count attempts, including failed provider calls.

## Privacy and bounds

- `SITE_STATE` must be mode 0700, outside the source/release tree. The service database
  is mode 0600. SQLite secure deletion is enabled. No content or credentials are
  logged by the application; only explicitly allowlisted UI files can be served.
- Session access expires seven days after creation. Expired records are purged at
  startup, on session mutations, and hourly while the service runs. If the service
  is stopped, cleanup waits until restart. A successful DELETE removes the local
  record immediately. No backups are created by this application. Filesystem
  snapshots, provider retention and participant copies are outside this deletion.
- UI/API disclose transmission to OpenAI and possible administrative storage access.
  Requests use `store:false`; that does not promise zero provider retention. Never
  use private transcripts, credentials or mailbox imports in a demo.
- Each input field is at most 4,000 characters; HTTP bodies at most 16,000 bytes;
  provider replies at most 64 KiB; model output at most 1,800 completion tokens.
  Discussion text is capped at 4,000 characters and each experiment field at 1,500.
- Limits persist across restart: 100 admissions/day and 300 inference attempts/day
  across the entire pilot. One inference runs at a time, with a 30-second socket
  timeout. Six successful turns maximum per session. Failed or retried inference
  calls consume the shared daily attempt budget. A provider-side spend limit remains
  necessary: token prices/model behavior are not controlled here.
- Sixteen concurrent HTTP connections maximum, 10-second request socket timeout,
  same-origin browser mutations, JSON-only writes, no CORS, restrictive CSP,
  no third-party scripts/fonts, no HTML rendering of model text. The native proxy
  owns TLS. Proxy access logs may contain client IPs and fixed endpoint paths;
  clients must never put tokens or content in URLs.

## Runtime contract and hosting dependency

The standard-library Python server binds explicitly to loopback. The native declaration
uses `llp-web-help`, candidate port 8501, runtime `python3.12`, and
`help.web.llmpsych.1puni.com`. Port 8500 remains assigned to the static landing.
These are the only two declarations in landing. Source scope comes from
knowledge-ingestion handoff commit `0ee5b35be38b80136c85aba80815e69bf8240d09`,
`steward/sites/README.md`. Protected installed policy/port availability and controller
receipts still need confirmation; this source does not reserve a port.

Native `SITE_STATE` is `/var/lib/llmpsych-sites/llp-web-help`. The application currently
expects a private `runtime.json` there with exactly these keys:

```json
{"api_key":"DEDICATED APPLICATION KEY", "model":"AUTHORIZED MODEL ID", "pilot_code":"RANDOM SECRET OF AT LEAST 24 CHARACTERS"}
```

This is a configuration **contract**, not permission or instructions to copy secrets
into state manually. A matching source-only protected binding is retained in knowledge-ingestion
commit `f4a3ab3cca6d4424cac43914aefdca40841314b9`,
`steward/sites/model-binding/README.md` and `50-model.conf`. It uses a required
read-only OS bind for this site's runtime file, without a broker or schema change.
The final reader keeps that exact contract. The binding is **uninstalled and
runtime-unverified**; consult that owning handoff for approval, installation,
rotation and UID/mount verification. The operator must authorize the model,
provider data handling and spend limits before protected installation. No environment search, steward login, GG auth,
controller execution or generic inference broker is used. Do not commit a runtime file,
put credentials in argv, or use a real key for fixture tests. Missing configuration
serves the UI with a clear unavailable notice and rejects new sessions with 503.

The fixed HTTPS provider request is documented in the
[official OpenAI Chat Completions API reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create):
structured JSON output, bounded completion tokens and `store:false`. The operator's
selected model must support this contract. Redirects are rejected; no caller controls
the provider URL. Model refusal, timeout, malformed JSON or incomplete output returns
502 without changing session content.

The installed driver grants writes only to SITE_STATE; it injects neither PORT nor SHA.
`/healthz` captures the full SHA once from the resolved immutable release directory
at process startup. A source checkout reports `development`. Health separates
`inference_configured` from any live journey claim; it never performs paid inference.

The working custom name `help.llmpsych.com` requires an operator-approved exact-host
policy change preserving the existing suffix, domain/DNS authority, certificate and
SNI routing. A CNAME alone is insufficient. Do not change apex/www Pages, install a
new host, or provision DNS from this task. Establish the supported fallback first.

## Run and verify

For a non-live local UI (no credentials required):

```sh
help_state=$(mktemp -d)
SITE_STATE="$help_state" python3 help_service/server.py --port 8501 --origin http://127.0.0.1:8501
```

Open http://127.0.0.1:8501. The illustrative panel and “Use this synthetic intake” are
explicitly written examples. Production has no fixture mode. Remove the temporary
state directory after stopping the process.

```sh
python3 -m unittest discover -s tests -v
node --check help_service/web/app.js
git diff --check
```

The HTTP suite uses an explicitly synthetic test-only inference function. It verifies
full lifecycle, two-session isolation, stale retries, expiry/deletion, restart/resume,
persistent quotas, body bounds, origins, authority-free provider payload, bad output,
provider failure with unchanged session, missing runtime, and source/state separation.
These checks do not establish provider access, external TLS or deployment.

The optional real-browser check uses a separate local fixture process (never the
production entry point). Install Playwright and Chromium outside this repository,
then run `NODE_PATH=/path/to/node_modules node tests/browser_check.cjs`. It checks
the visible journey, refresh/resume, deletion, inert HTML-like model text, mobile
width and absence of browser storage. `HELP_SCREENSHOT` optionally names an
outside-repository screenshot path; it captures only the empty intake.

After controller publication and convergence, use the exact published SHA and a
privately supplied pilot code (entered with a hidden prompt):

```sh
python3 scripts/check_help.py --sha FULL_40_HEX_PUBLISHED_SHA
```

The check verifies public SHA/UI, creates two synthetic sessions, makes **real model
calls** through the configured service, checks isolation and stale retries, completes
a review, and deletes both sessions. Output excludes session content/tokens. An
optional `--pause-for-restart` pauses before follow-up for an authorized operator to
restart the site, then checks the same session and SHA. This script does not restart
or deploy anything. If it fails, report failure; do not call the static example live.

Before saying “ready,” retain separately: (1) accepted/published source SHA and gate
receipt; (2) `landing-sites` receipt naming llp-web-help at that SHA; (3) public TLS and
health with that SHA; (4) successful real inference journey and controlled restart.
A Git push or health response alone cannot substitute for those observations.

## Five-minute demo

1. Open the supported URL and show the four-step journey. Explain that the right-hand
   illustration is synthetic, and runtime configuration alone is not proof of inference.
2. Use the synthetic intake. Enter the privately supplied pilot code and opt in.
   Do not reveal the code or session key on a shared screen.
3. Send a concrete synthetic observation: “Another check has not changed my decision.”
   Read the generated question, then add a relevant answer (wording will vary).
4. Ask for an experiment: “Respect the agreed checks and my existing authority.”
   Point out its measure, stop condition and review time; no action has been executed.
5. Save the private key for later, resume the session, and report explicitly synthetic
   trial observations. Read the review, then delete the session. Explain that this
   demonstration does not establish benefit, diagnosis or a real behavioral outcome.

A real free pilot uses the same consent and boundaries with the participant's own
redacted material. No outreach or enrollment of a third party is authorized here.
