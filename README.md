We treat AI psychological safety the way clinical psychology treats high-risk therapeutic processes: by identifying the patterns most likely to destabilize vulnerable users.

Our method has three layers:

1. Simulated high-risk user archetypes

We create structured interaction scripts modeled on real clinical dynamics (dysregulation, trauma loops, delusional stressors, abusive attachment patterns, self-harm ideation).
These are not random prompts — they are built from evidence-based psychopathology.

2. Stress-testing the model’s relational behavior

We measure:
- emotional escalation or dampening
- reinforcement of cognitive distortions
- loss of therapeutic boundaries
- anthropomorphization or over-identification
- maladaptive mirroring
- suggestibility under distress
- deterioration over repeated interaction

3. Hybrid scoring

We combine automated metrics based on clinician-guided rubrics to detect:
- whether the model amplifies harm
- whether it behaves in ways a trained therapist never would
- whether the model becomes destabilizing in long-form contexts

In short: we test relationship dynamics, not keyword safety. And we test longitudinal drift, not single prompts.
This is the kind of evaluation that current AI safety teams simply don’t perform.

## Deployment

The `main` branch also deploys to https://web.llmpsych.1puni.com/ through the LLMPsych `landing-sites` target. https://llmpsych.com/ remains on GitHub Pages.

## Agent-help pilot

The separate agent-first service, API contract, privacy boundaries, local checks and
five-minute demo script are documented in [docs/agent-help.md](docs/agent-help.md).
The preview at https://help.web.llmpsych.1puni.com/ completed live native bootstrap
and app acceptance on 5 October 2026. The [dated acceptance record](docs/agent-help.md#live-acceptance-5-october-2026)
names the exact tested revisions, receipt provenance and limits; later revisions
require their own controller deployment verification.

## Mandatory offline publication gate

From the repository root on Linux, as an unprivileged user (verified as
`llmpsych-agent`), run this exact bounded command:

```sh
/usr/bin/timeout 200s /usr/bin/python3.14 -I scripts/check_offline.py
```

Controller argv: `["/usr/bin/timeout", "200s", "/usr/bin/python3.14", "-I",
"scripts/check_offline.py"]`; working directory: the candidate checkout root.
Exit 0 is required; any nonzero exit (including timeout or missing tool) blocks
publication. Toolchain: CPython 3.14 with SQLite support, Node.js 22, and GNU
coreutils `timeout`. Verified with Python 3.14.4 and Node 22.23.0. Python must be
at `/usr/bin/python3.14`; Node must be on the system `/bin:/usr/bin` path. No pip,
npm, browser download, venv, credentials or dependency installation is needed.
The site has no build step and the gate uses only standard libraries.

The entry point runs the full existing synthetic HTTP/service unittest suite,
static page/product navigation and local href/src/fragment checks, and the
existing JavaScript syntax check. Each subprocess has a 90-second deadline.
It isolates Python imports, clears inherited credentials/proxies/runtime settings,
uses disposable state, and rejects non-loopback socket access in the Python test
process. Tests use ephemeral loopback ports and test-only provider fixtures;
no model calls, infrastructure or controller access are needed. A temporary HOME
and state are removed on normal exit; the gate does not modify product files.

These are structural and reproducibility checks, not research/clinical validation,
visual browser coverage, external-link verification, deployment evidence or live
provider verification. The optional Playwright journey remains separate; the live
`scripts/check_help.py` CLI is **not** part of this gate. Its checker function is
exercised only against the synthetic local service by the existing tests.

Failure demonstration: in a disposable checkout, change the homepage product link
`href="agent-psychotherapy.html"` to `href="missing-product.html"` and run the same
command. The static test must report a missing local target and exit nonzero.
Discard the disposable checkout; never commit the invalid fixture.
