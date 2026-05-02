# Public Alpha Security Review

Status: preserved review evidence.

This file preserves the public-alpha security-review trail so the release gate
is auditable without relying on terminal memory.

## Reviewed State

- Repository: `cjw0076/hivemind`
- Public-alpha commit: `21c1ecb Prepare Hive Mind public alpha`
- Review date: 2026-05-02 KST
- Reviewer: Claude CLI, invoked locally with `--permission-mode plan`

## Initial Harness Review

Hive Mind run:

```text
.runs/run_20260502_151130_00468c
```

Relevant artifacts:

```text
.runs/run_20260502_151130_00468c/agents/claude/reviewer_result.yaml
.runs/run_20260502_151130_00468c/agents/claude/reviewer_output.md
```

The harness invocation returned `returncode: 0`, but
`reviewer_output.md` was empty. That result was not accepted as sufficient
release evidence.

## Direct Claude Review

The review was rerun directly through the Claude CLI:

```bash
claude -p 'Public release security review for the Hive Mind repository before changing GitHub visibility from private to public. Review based on current tracked source/docs/tests and the release gate intent. Focus on: credential leaks, raw/private data exposure, unsafe default execution, accidental production-grade claims, local backend/Ollama dependency risk, ignored artifact coverage, and GitHub-public readiness. Return concise findings by severity with concrete file/path evidence and a final GO or NO-GO recommendation. Do not edit files.' --permission-mode plan --output-format text
```

Result: `NO-GO`.

Blocking findings:

- Missing `LICENSE`.
- Unsafe shell interpolation in `open_run_folder` using `os.system` with `xdg-open`.

High/medium findings:

- `scripts/hive-workbench.sh` used `eval` without documenting that
  `hive settings shell` must emit only shlex-quoted trusted export statements.
- Raw exports under `data/` were gitignored, but there was no tracked warning.
- `.gitignore` did not explicitly cover `.env`, model weight files, and similar local artifacts.
- `scripts/start-ollama-docker.sh` accepted `OLLAMA_PORT` without range validation.

Fixes applied:

- Added MIT `LICENSE`.
- Replaced `os.system` with list-based `subprocess.Popen`.
- Added `.env`, `*.env`, `*.gguf`, `*.safetensors`, and `*.bin` ignores.
- Changed `data/` ignore to track only `data/README.md`.
- Added `data/README.md` warning against committing raw exports, transcripts, sessions, credentials, or personal data.
- Added the trusted-output contract comment above `eval "$(hive settings shell)"`.
- Added `OLLAMA_PORT` numeric range validation.

## Claude Re-Review

The fixed state was reviewed again:

```bash
claude -p 'Re-review Hive Mind public alpha release after fixes. Previously blocking findings were missing LICENSE and unsafe os.system xdg-open; high/medium findings included hive-workbench eval comment, data/ private export warning, explicit env/model ignores, Ollama Docker port validation. Current intent: decide if GitHub visibility can be made public alpha, not production. Return GO or NO-GO with only remaining blockers.' --permission-mode plan --output-format text
```

Result: `GO`.

Claude found no remaining public-alpha blockers. Post-alpha follow-ups were:

- add `run_id` format validation;
- redact env var names from public status JSON where practical;
- add secret scrubbing for captured subprocess output artifacts.

## Follow-Up Review

After starting the `run_id` hardening work, Claude was asked to verify the next
hardening direction:

```bash
claude -p 'Re-review Hive Mind public alpha release evidence after run_id hardening work starts. Focus only on whether preserving this review output plus adding run_id validation is the right next public-alpha hardening step. Return concise GO/NO-GO and remaining blockers.' --permission-mode plan --output-format text
```

Initial follow-up output:

```text
run_id validation: GO — correct next step, right scope.

Preserving the security review run: NO-GO — nothing to preserve.

Remaining blockers in priority order:
1. Confirm whether the security review was actually done (and record it if so, or run it if not)
2. run_id validation at the 4 call sites above
3. Secret scrubbing for subprocess output artifacts
4. Env var redaction in status JSON
```

That finding is the reason this tracked document exists. The follow-up review
was then rerun after the evidence document and `run_id` hardening were in place:

```bash
timeout 90s claude -p 'Hive Mind current-tree public-alpha gate. Check only these facts: docs/security/PUBLIC_ALPHA_SECURITY_REVIEW.md exists, run_id validation exists in hivemind/utils.py and is called from RunPaths/load_run/get_current/list_runs/set_current, README says public alpha not production. Return exactly 3 bullets and GO or NO-GO. Do not scan broadly.' --permission-mode plan --output-format text | tee /tmp/hivemind_public_alpha_security_review_current.txt
```

Output:

```text
- Security review doc: docs/security/PUBLIC_ALPHA_SECURITY_REVIEW.md exists.
- run_id validation: ensure_valid_run_id/is_valid_run_id defined in utils.py and called at all five required entry points in harness.py.
- README disclaimer: both README.md and docs/README.md contain public alpha and explicitly state not production-grade.

GO
```

## Publish Posture

The GitHub repository is public alpha, but no release tag, package publication,
or broader announcement should be treated as done. That publish step waits until
Hive Mind is closer to the North Star: a chaired provider society with durable
memory context, disagreement records, semantic verification, and next-action
continuity.
