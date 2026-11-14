# Final handoff

## Scope and team assignment

The project is a local-first English ↔ Hindi typed-text and speech translation
demo. The default mock providers support workflow testing only; real inference
uses local adapters and may download model weights on first use. Model output
is not guaranteed to be accurate or fast.

The contribution mapping below follows the owner assignments in
[`IMPLEMENTATION.md`](../IMPLEMENTATION.md) and the merged Sprint 4 PR history.
It records task ownership and merged work, not individual commit authorship.

| Member | Sprint 4 assignment | Merged PRs |
|---|---|---|
| A | AMTT-31 UI states/accessibility; demo lead for AMTT-40 | #72 |
| B | AMTT-32 provider failures/timeouts; AMTT-33 logging; AMTT-36 input hardening; AMTT-38 documentation | #73, #74, #77, #79 |
| C | AMTT-35 performance/memory benchmark | #76 |
| D | AMTT-34 evaluation set; AMTT-37 Windows guide; AMTT-39 regression run | #75, #78, #80 |

## Validation snapshot

- Snapshot checked: `main` at `5ace296` (AMTT-39 PR #80 merged).
- Windows default suite: `python -m pytest` — 129 passed, 1 skipped. The skip
  is the opt-in Faster-Whisper smoke test requiring a local recording and real
  inference.
- Typed and speech UI flows were exercised in both directions with mock
  providers and synthetic WAV input. Microphone denial was simulated; physical
  microphone capture and real-model inference were not performed.
- No tracked GitHub Actions workflows were present at this snapshot; the
  validation signal is the local test run, not a hosted CI check.
- A tracked-path scan found no runtime `.env` file (the tracked
  `.env.example` is the template), model cache/weight paths, audio recordings,
  or generated log/test-output files. This is not a substitute for a credential
  scanner or independent security review.

See the [Windows setup guide](windows-setup.md), [API documentation](api.md),
[architecture](architecture.md), and [final demo script](final-demo-script.md)
for operating instructions and known limitations.

## Release gate

The `v1.0.0` tag has **not** been created. The final demo/handoff changes must
first be independently reviewed and merged to `main`; then rerun the default
suite on the resulting `main` and verify the live demo prerequisites with the
team. Create and push the release tag only if those checks pass:

```powershell
git switch main
git pull --ff-only origin main
python -m pytest
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

Keep the release pending if physical microphone use, real model setup, or
required team review is unavailable. Do not mark the Jira item Done or present
mock output as real speech.
