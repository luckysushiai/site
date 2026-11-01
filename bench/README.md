# Code-review bench (M3)

This directory is the skill-ranker task set for the job `code-review-testing-debugging`. It sits next to `site/`, not inside it, so a Cloudflare Pages upload of `site/` does not deploy it. Nothing here calls a model, creates an account, or spends money.

The ten tasks are original fixtures written for this repo. They are not copied from SkillsBench or another benchmark.

## Tasks

| Task | Kind | What the verifier checks |
|---|---|---|
| `py-review-off-by-one` | review a diff | `answer.json` file, line, and category |
| `js-review-swapped-arguments` | review a diff | `answer.json` file, line, and category |
| `py-failing-tests-remainder` | write failing tests | tests fail on the buggy module and pass on two corrected ones |
| `js-failing-tests-normalize` | write failing tests | same, for a tag normalizer |
| `py-fix-form-encoding` | fix a bug | hidden form-decoding checks, plus the visible tests |
| `js-fix-coupon-rounding` | fix a bug | hidden half-up price checks, plus the visible tests |
| `py-coverage-access` | coverage threshold | at least 90% line and 80% branch, implementation unchanged |
| `py-mutation-grades` | mutation threshold | tests pass on the original and kill at least 8 of 10 mutants |
| `py-tdd-semver` | TDD from a spec | visible examples plus hidden precedence and rejection cases |
| `js-tdd-retry-delay` | TDD from a spec | visible delays plus hidden half-up rounding and rejections |

Each task is a small offline Python or JavaScript fixture. The agent workspace is `environment/` with the Dockerfile left out. `oracle/`, `wrong/`, and `verifier/` are not copied into that workspace. Hidden checks carry the marker `HIDDEN_VERIFIER_ONLY` and `scripts/check_hidden.py` fails if that marker shows up in `instruction.md` or `environment/`.

`bench tasks check` (BenchFlow 0.6.9) accepts this layout with no account and no sandbox. Do not mount the task directory into a model agent. BenchFlow builds the image from `environment/` and only then mounts `verifier/` for the test script. The local runner does the same split.

## Harness

[BenchFlow](https://github.com/benchflow-ai/benchflow) 0.6.9 is the SkillsBench harness ([skillsbench](https://github.com/benchflow-ai/skillsbench), Apache-2.0). `pip install benchflow` and `bench tasks check` run with no account and no API key. The local sandbox is Docker ([sandboxes](https://www.benchflow.ai/docs/benchflow/sandboxes)). Modal, Daytona, and AgentCore need accounts and keys, so they are not used.

The tasks use the Harbor-style split that BenchFlow reads: `instruction.md`, `task.toml`, `environment/Dockerfile`, `oracle/solve.sh`, and `verifier/test.sh`. `scripts/run_trial.py` (local runner `local-harbor-style` 0.1.0) is the no-Docker path: it copies the fixture, applies `oracle`, `nop`, or `wrong`, runs `verifier/test.sh`, and requires exit 0 together with reward `1`. When `docker info` succeeds, `scripts/check_all.sh` also runs `bench eval run --agent oracle --sandbox docker --usage-tracking off` on the real tasks, then the same command on a copy whose `oracle/solve.sh` is a no-op. BenchFlow has no nop agent. The oracle run must score 10/10 and the no-op copy must score 0/10.

M4 should use that same BenchFlow command and Docker sandbox. No model call is part of M3.

## Model for M4

Planned model: `gemini-3.1-flash-lite` on the Gemini Developer API free tier (Google AI Studio).

Why this one:

- The official pricing page lists standard input and output for `gemini-3.1-flash-lite` as free of charge. Fetched 2026-11-01 from [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing). `gemini-2.5-flash` and `gemini-2.5-flash-lite` are also marked free of charge there.
- A third-party writeup says Gemini 2.5 Flash, Flash-Lite, and Pro API access is limited to developers who have used those models before, and that new projects should use current Gemini 3 models ([scriptbyai](https://www.scriptbyai.com/gemini-api-free-tier-limits/), 2026-10-29). That restriction is not on the official pricing page. A new free-tier project should not plan on a 2.5 id. `gemini-3.1-flash-lite` is a current id that the pricing page lists as free of charge and that both third-party writeups below name with a daily cap.
- Do not enable Grounding with Google Search or Maps. The pricing page's RPD figures for those tools are tool caps, not the generateContent cap.
- Unpaid API input and output may be used to improve Google products, and human reviewers may read, annotate, and process them. That is acceptable here because the tasks are public fixtures with no personal data. Say so wherever a score is published. [Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms), effective 2026-03-23, section "Unpaid Services".

Official request caps, from [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) (updated 2026-10-28):

- Limits are RPM, input TPM, and RPD. Exceeding any one of them returns an error.
- Limits apply per project, not per API key. RPD resets at midnight Pacific.
- The page prints no numeric free-tier RPM or RPD. It says to view the live numbers in AI Studio, and that specified limits are not guaranteed.
- This milestone does not create an AI Studio project, so the live quota was not read. M4 reads that live quota before applying any cut.

Third-party RPM/RPD numbers below are unverified. They are not Google's published table. The two writeups do not even agree with each other.

- [imisofts](https://imisofts.com/blog/gemini-api-free-tier-limits/), 2026-10-21, says the author read one free project in AI Studio that day. For Gemini 3.5 Flash-Lite and Gemini 3.1 Flash-Lite the page says 15 RPM, 250,000 TPM, and 500 RPD. For Gemini 2.5 Flash-Lite it says 10 RPM and 20 RPD. For Gemini 3.8, 3.6, 3, and 2.5 Flash it says 5 RPM and 20 RPD.
- [scriptbyai](https://www.scriptbyai.com/gemini-api-free-tier-limits/), 2026-10-19, says its table comes from the AI Studio free-tier comparison. It lists Gemini 3.1 Flash-Lite at 10 RPM, 250,000 TPM, and 500 RPD, and Gemini 3.5 Flash-Lite at the same 10 RPM and 500 RPD. It lists Gemini 3.8 Flash and 3.6 Flash at 5 RPM and 20 RPD. It also says Gemini 2.5 API access is limited to developers who used it before.
- A Google AI Developers Forum thread says a free-tier Flash quota was cut from 250 RPD to 20 RPD: [forum thread](https://discuss.ai.google.dev/t/do-they-really-think-we-wouldnt-notice-a-92-free-tier-quota/111262). That post does not name `gemini-3.1-flash-lite`.

## Call count and proposed cuts

The scored pilot is every one of the 20 skills, not only the eight skills whose job is code review. Three arms, ten tasks, three tries:

```text
20 skills x 3 arms x 10 tasks x 3 tries = 1800 generateContent calls
```

These cuts are a plan only. They are not applied. The dry run's `recorded_cuts` is empty, and all ten tasks stay in the tree. M4 reads the live AI Studio quota for `gemini-3.1-flash-lite` and only then writes a cut into the run record. The two scenarios below are bounds from the third-party numbers, not official caps.

If that live cap is 20 RPD (the third-party figure for Gemini Flash, and imisofts' figure for Gemini 2.5 Flash-Lite, not the figure either page gives this model), 1800 calls take 90 days. That binds.

1. Cut tasks per skill first, from 10 to 1. Calls become `20 x 3 x 1 x 3 = 180` (9 days at 20 RPD).
2. Then cut tries per task, from 3 to 2. Calls become `20 x 3 x 1 x 2 = 120` (6 days at 20 RPD).
3. Do not cut skills. The skill count stays 20.

If that live cap is 500 RPD (the third-party figure both writeups give `gemini-3.1-flash-lite`), 1800 calls take 3.6 days. At the scriptbyai 10 RPM figure the same 1800 calls need at least 180 minutes of spacing, and at the imisofts 15 RPM figure at least 120 minutes, before generation time. No cut is required for a multi-day run. If AI Studio shows 500 RPD or more, record no cuts. If it shows 20 RPD, record the two cuts above.

## Three arms

| Arm | What the agent receives |
|---|---|
| `no_skill` | the task instruction and the fixture only |
| `skill` | the same, plus that skill's real `SKILL.md` |
| `placebo` | the same, plus the length-matched placebo for that skill |

The dry run is oracle and nop only. Both are `no_skill`, `skill_id` is null, and `model.called` is false. It does not start the scored pilot.

## Placebo

`scripts/placebo.py` builds the placebo arm. `generate_placebo(source, skill_id)` is a pure function:

- Token count uses `scripts/tokens.py`: a token is one word (`\w+`) or one punctuation mark. This is not a provider tokenizer. Counting tokens with the Gemini API would be a model call.
- The output has the same token count as `source`.
- The seed is SHA-256 of `skill_id` plus the source, so the same inputs always produce the same text.
- Every output token is drawn from a fixed word list of unrelated nouns. The list is disjoint from a denylist of review, test, and debugging words, and the output does not copy alphabetic tokens from the source.

`python3 scripts/test_placebo.py` checks length, determinism, and the denylist. M4 should pass each skill's real text through this function. Do not vendor those skills into this directory.

## Run record

`runs/schema.json` is the M4 record. One record has the run id, job, model name and version, whether a model was called, harness name and version, and `recorded_cuts`. Each trial has the run id, task, arm (`no_skill`, `skill`, or `placebo`), skill id, model name and version, harness name and version, try number, verifier result, start and finish timestamps, usage (null when the API did not return token counts), recorded cuts, and the agent (`oracle`, `nop`, `wrong`, or `model`).

`runs/validate.py` checks a record against that schema with no extra packages. `--expect-dry-run` also requires every task to have an oracle pass and a nop fail, with no model name, no usage, and no cuts.

The dry run that produced `runs/dry-run-2026-11-01/run.json` executed the oracle and nop agents. Regenerate it with `python3 scripts/dry_run.py`.

## Reproduce

From the repo root:

```bash
bash bench/scripts/check_all.sh
```

That runs the placebo tests, the hidden-marker check, the layout check (and `bench tasks check` when BenchFlow is installed), oracle / nop / wrong for every task, and the dry-run validator. Oracle must pass. Nop and the plausible wrong answer must fail. When `docker info` succeeds and `bench` is on `PATH`, it also runs the Docker oracle (must score 10/10) and the no-op `solve.sh` stand-in (must score 0/10).
