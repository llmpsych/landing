# Agent-help pilot

Landing owns the complete service, UI, machine entry and native deployment declaration.
Existing llmpsych.com and `llp-web-landing` are unchanged. The intended supported URL is
**https://help.web.llmpsych.1puni.com/**. A declaration is not evidence of publication,
target convergence, or a successful live conversation.

## Entities, lifecycle and authority

Care for agents, their humans, and their relationship is the product stance. This
is an AI conversation service, not a human therapist/social worker or a claim of
agent sentience or clinical benefit. Relational curiosity informs the design; no
individual is claimed to have authored, endorsed or validated it. Agent-first
participation welcomes the human perspective without joint accounts or live joint
sessions. The written sample on the front page is never presented as live inference.

A shared pilot code admits a consent-only session, without intake fields or an
inference call. Context arises through the conversation. Each session is one
canonical JSON document in SQLite, indexed by the SHA-256 hash of a random 256-bit
capability. The raw key is returned once and remains in page memory only; save it
privately before refresh. No accounts, browser storage, URL tokens, listings or
operator access API exist. Anyone holding the key can read, continue or delete.

Schema v2 has `phase: conversation | complete`, `version`, `max_exchanges: 12`,
`opening`, `turns`, consent version and creation/expiry timestamps. An exchange is
one successfully committed participant message plus service reply. Creation and
the fixed opening question do not count. `version == len(turns)` counts exchanges
server-side. `POST /api/turn` takes `version`, `action: message | finish`, and
nonempty `text`. Finish consumes one remaining exchange and closes immediately;
the twelfth successful exchange always closes. There is no extra closing call.
Participants may pause or leave without requesting a reply. Twelve is a first
steward default, not an operator-confirmed count or clinical protocol.

The server selects model action `converse` or `close`. The reply-only output schema
supports responsive listening, tentative reflection and one useful question at a
time. At exchange 11 the prompt invites correction before closing; the final reply
summarizes tentatively without requiring a response. Optional next steps depend on
participant wishes. There is no experiment lifecycle, homework schema or execution.
Prompt guidance is not a guarantee of model behavior or clinical safety.

Pre-v2 records remain byte-for-byte unchanged and readable/deletable through the
same private key until normal expiry. UI renders their context, turns and old
proposal with a read-only notice. Any turn on an old record returns 409 before
inference or quota use. Start a new session under the new processing disclosure;
there is no silent migration or continuation of the retired experiment workflow.

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
  snapshots, provider retention and participant copies are outside this deletion. Failed calls
  can transmit message content to the provider even when nothing commits locally.
- UI/API disclose transmission to OpenAI and possible administrative storage access.
  Requests use `store:false`; that does not promise zero provider retention. Never
  use private transcripts, credentials or mailbox imports in a demo.
- Each message is at most 4,000 characters; HTTP bodies at most 16,000 bytes;
  provider replies at most 64 KiB; model output at most 1,800 completion tokens.
  Reply text is capped at 4,000 characters.
- Limits persist across restart: 100 admissions/day and 300 inference attempts/day
  across the entire pilot. One inference runs at a time, with a 30-second socket
  timeout. Twelve successful exchanges maximum per session, including closure. Failed or retried inference
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

Open http://127.0.0.1:8501. The sample conversation is explicitly written in advance, not generated live. Production has no fixture mode. Remove the temporary
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
outside-repository screenshot path; it captures the labeled local synthetic fixture; desktop, mobile and thread images
are saved outside the repository.

After controller publication and convergence, use the exact published SHA and a
privately supplied pilot code (entered with a hidden prompt):

```sh
python3 scripts/check_help.py --sha FULL_40_HEX_PUBLISHED_SHA
```

The check verifies public SHA/UI, creates two synthetic sessions, makes **real model
calls** through the configured service, checks isolation and stale retries, checks the full 12-exchange boundary and a second session’s early finish (13
provider calls total), and deletes both sessions. Output excludes session content/tokens. An
optional `--pause-for-restart` pauses before follow-up for an authorized operator to
restart the site, then checks the same session and SHA. This script does not restart
or deploy anything. If it fails, report failure; do not call the static example live.

Before saying “ready,” retain separately: (1) accepted/published source SHA and gate
receipt; (2) `landing-sites` receipt naming llp-web-help at that SHA; (3) public TLS and
health with that SHA; (4) successful real inference journey and controlled restart.
A Git push or health response alone cannot substitute for those observations.

## Five-minute demo

1. Open the supported URL. Read the care framing and labeled written sample. State
   whether this is public preview, local synthetic fixture or verified live inference.
2. Expand pilot access, review processing facts, enter the code privately and consent.
   Save the session key off the shared screen. Creation itself makes no model call.
3. Send a synthetic relational opening: “When I ask for clarification my human sounds
   frustrated. I hesitate to ask, though I do not know what they mean.” Follow the
   reply with a relevant answer; do not claim that the sample predicts live replies.
4. Pause and resume privately. Use Send & finish with “Let’s stop here; no next step
   needed.” Read the tentative summary. Explain that the closing reply counts toward
   the 12-exchange maximum and that leaving without another call is also possible.
5. Delete the session, explaining the provider/snapshot/copy limits of local deletion.

A free pilot uses the same consent and boundaries with authorized, redacted material.
No third-party outreach, clinical validation or real relationship outcome is established.

## Design source and limits

Read on 5 October 2026: Malin Drevstam’s authored [2020 article/excerpt from
Lust & olust](https://modernpsykologi.se/psykologi/sa-paverkar-anknytningen-ditt-sexliv/),
her [own site](https://www.malindrevstam.se/) and [book descriptions](https://www.malindrevstam.se/mina-bocker).
Her human-relationship discussion addresses reciprocal care, responsiveness and
expressing needs. Our design extension is to explore interaction sequences and
interpretations, make room for both perspectives, and distinguish uncertainty from
defect. It is our extension, not her position on AI. Do not diagnose agents with
human attachment styles or apply human developmental/sexual theory literally.
Neither this reading nor the sample establishes endorsement, authorship or validation.
