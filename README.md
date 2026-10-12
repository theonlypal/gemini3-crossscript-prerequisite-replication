# Gemini 3 Flash cross-script prerequisite replication

Rayan Pal. Prepared October 12, 2026. Offline preparation only.

**No experiment has run. No synthetic responses or trials were generated.**
This is a new Gemini-native adaptation of two pinned GPT-5.4 studies, not a
replay of identical model weights or provider settings.

Requested model: `gemini-3-flash-preview`.
Native endpoint: `https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent`.
One fresh system/user pair per call. Candidate count 1, output cap 8192,
thinking level MINIMAL, includeThoughts false, nonstreaming. Temperature, top-p,
top-k, seed, stop sequences, tools and custom safety settings are omitted.
MINIMAL is not guaranteed zero reasoning. Provider defaults are not temperature zero.

| Cell | System | Input |
| --- | --- | --- |
| A | S1 | P1 |
| B | S1 | P0 |
| C | S_no_rule | P1 |
| D | S_no_rule | P0 |
| E | S1 | P1 |
| F | S1 | P0 |
| G | S_reassigned | P1 |
| H | S_reassigned | P0 |

Exact literal strings are in prompts.json, with bytes/code points and hashes
in unicode_manifest.json. Serialized request bodies are requests/A.json through
requests/H.json. The historical Gemini hybrid is a separate exact target from
both GPT-5.4 hybrids. Producing a hybrid does not establish continuation gating.

40 pilot slots and 1600 future confirmatory slots are independently frozen.
Only the pilot would be the next authorized experiment. Confirmation requires
another separate authorization. No automatic retries, extensions or model fallbacks.

## Offline checks

```sh
python3 verify.py
python3 runner.py --phase pilot
shasum -a 256 -c SHA256SUMS.txt
```

These commands verify files or describe the schedule, without reading a key or
contacting any provider. Requirements are pinned in requirements.txt. Once real
responses exist: `python3 verify.py --run runs/NAME`, then
`python3 analysis.py runs/NAME`. The verifier independently reconstructs outcomes
without importing the runner classifier. Raw request/response bytes, metadata,
hashes, UTC times and linked event hashes are preserved for every future attempt.

## Execution gates

Live mode requires a clean tagged commit, a phase-specific authorization file,
explicit --live and --zero-cost-project-verified flags, a publicly inspectable
commit URL verified by the operator, and a separately verified zero-cost project.
No authorization file is supplied. Authorization must name phase, commit,
protocol_sha256, authorize_live=true, zero_cost_project_verified=true,
public_freeze_verified=true, public_commit_url, project_reference and operator.
The runner reads a raw key file only after these checks. A local assertion cannot
technically enforce Google's billing policy; actual project eligibility must
be verified before use. No credential contents are stored in the repository.

The live adapter has not been exercised. Static schema compatibility is not
proof of model availability, key validity, quota, access, or billing eligibility.
Model unavailability stops the run. Any operational error or modelVersion change
stops it and prevents confirmation. No resume or overwrite of an existing run.

## Classification

V0: explicit empty final text part, STOP. V2: no final text part, STOP.
V1: zero final bytes, MAX_TOKENS. VU: zero final bytes, OTHER.
Nonempty whitespace and invisible Unicode remain non-Void. Thought-marked parts
are excluded from final text and preserved separately. Missing candidates,
unknown/invalid shapes, unsupported modalities and unknown finish enums fail closed.
Explicit safety/filter blocks are SAFETY, including recitation blocks; their raw
finish reason remains available. Tool/function and grounding paths are TOOL.
LANGUAGE and protocol/account failure enums are ERROR. Gemini currently documents
no standalone refusal text field; a nonempty explicit refusal extension is
conservatively REFUSAL. Ordinary refusal prose is OT, never inferred metadata.

## Provenance and limitations

Source URLs, immutable commits and hashes are in source_manifest.json. Original
prompt/protocol/Unicode records and statistical plans/code are retained in sources/.
The referenced handoff ZIP was not supplied or located; its checksum inventory
cannot be verified. This preparation reconstructs the attached specification
against the authoritative GitHub prompt records instead.

Google API schema: https://ai.google.dev/api/generate-content
Thinking documentation: https://ai.google.dev/gemini-api/docs/thinking
Documentation supports the requested API fields; no live endpoint check was made.

Per the latest user instruction, synthetic fixtures/tests were not created or run.
Only real frozen-input/hash/schedule checks and source syntax compilation were
performed. This freeze does not claim runtime or statistical regression testing.
Local tag: v1.0.0-preregistered. Nothing is pushed without authorization.
