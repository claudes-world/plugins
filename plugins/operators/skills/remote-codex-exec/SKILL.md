---
name: remote-codex-exec
description: Steer a detached Codex CLI on a remote machine over ssh, typically a Mac with a GUI session, for computer use, screen capture, browser and GUI automation that cannot be driven over ssh. Use when asked to run remote codex, launch codex exec detached on another box, do screen or browser work on a Mac, or hand a long task to a bigger machine.
---

# Remote Codex exec

Do not drive a remote screen over ssh. ssh into the machine, start a detached
`codex exec` process with a written brief, and steer it like any other CLI
agent: launch, watch the log, read the report, resume for follow-ups.

Placeholders: `<mac>` is the ssh host alias of the remote machine, `<workdir>`
is a directory on the remote (for example `~/jobs/task-1`). Keep real
hostnames, IPs and account names out of anything you commit.

## When to use

- Any remote machine with a GUI session you cannot drive over ssh (screen
  capture, computer use, signed-in browser work).
- Any long task you want to run on a bigger box than the one you are on.

## Do not use for

- Interactive logins, or anything that needs a human tap mid-run. Put the stop
  condition in the brief instead (see step 1).

## Procedure

### 1. Write the brief as a file and copy it over

Write `brief.md` locally, then:

```sh
ssh <mac> 'mkdir -p <workdir>'
scp brief.md <mac>:/tmp/brief.md
```

The brief must end with a report contract and stop conditions:

```text
Report contract:
- Write <workdir>/REPORT.md when finished or stopped.
- Its first line is exactly `STATUS: DONE` or `STATUS: BLOCKED (<reason>)`.
- Name every deliverable by full path in REPORT.md.

Stop conditions:
- Never type passwords.
- If a login is missing, stop and write `LOGIN_REQUIRED` in REPORT.md.
- If a macOS permission is missing, stop and write `PERMISSION_REQUIRED: <which>`.
- If macOS demands the account password (for example "Privacy & Security is
  trying to modify your system settings"), stop and write
  `PASSWORD_REQUIRED: <setting>`.

Do not stop for confirmations inside this brief; stop only for credentials or
out-of-scope actions.
```

A non-interactive `codex exec` ends the session whenever the model asks for
confirmation, so the last line above matters. Keep one log per run
(`codex-run<N>-<label>.log`) instead of a single `codex.log`; steps 2-4 use
`codex-run1-<label>.log` for the first run (bump N per run).

Keep secrets out of the brief.

### 2. Plain detached launch (non-GUI work)

```sh
ssh <mac> 'nohup sh -c "cat /tmp/brief.md | codex --dangerously-bypass-approvals-and-sandbox exec --skip-git-repo-check -c model_reasoning_effort=high -C <workdir> > <workdir>/codex-run1-<label>.log 2>&1" >/dev/null 2>&1 &'
```

`--yolo` is the short alias for `--dangerously-bypass-approvals-and-sandbox`;
the long flag is what `codex exec --help` lists on codex-cli 0.154. Always pass
`-c model_reasoning_effort=high`: without it the run came out at effort low.

### 3. GUI work (screen capture, computer use, browser)

A process started from ssh has no macOS TCC permissions (Screen Recording,
Accessibility). Symptoms: ffmpeg screen capture returns an input error, and
Codex's computer-use helper fails with "native pipe startup failed". Launch
inside the Mac's login session instead.

Write `<workdir>/run.command` (zsh, same pipeline), make it executable, open it
with Terminal:

```sh
ssh <mac> 'cat > <workdir>/run.command' <<'SCRIPT'
#!/bin/zsh
cat /tmp/brief.md | codex --dangerously-bypass-approvals-and-sandbox exec --skip-git-repo-check -c model_reasoning_effort=high -C <workdir> > <workdir>/codex-run1-<label>.log 2>&1
SCRIPT
ssh <mac> 'chmod +x <workdir>/run.command && open -a Terminal <workdir>/run.command'
```

Terminal is the TCC principal, but launching from Terminal is not enough on
its own. Validated on a first GUI run: the codex still reported
`PERMISSION_REQUIRED: Screen Recording` (ffmpeg avfoundation "cannot configure
display capture", `screencapture` "could not create image from display") and
the computer-use helper failed with "Sky Computer Use native pipe startup
failed".

Before the first GUI run, the human must grant Terminal both Screen Recording
and Accessibility under System Settings, Privacy & Security, plus any
Codex/ChatGPT helper that appears in those lists. On macOS 26 the pane is
named "Screen & System Audio Recording", a separate entry from Accessibility;
grant both. If the machine is remote, do
this through a screen-sharing client. The permission prompt may or may not
appear automatically, so open the panes by hand if it does not. After that
every future run inherits the grants.

When a computer-use agent toggles a principal in that pane, macOS can demand the
account password. The agent must stop with `PASSWORD_REQUIRED: <setting>`
(never type it); expect a human tap via screen sharing, then resume.

#### Pre-flight check (about 10 seconds, run BEFORE dispatching GUI work)

```sh
ssh <mac> 'cat > /tmp/tcc-check.command <<EOF
#!/bin/zsh
screencapture -x /tmp/tcc-check.png && echo CAPTURE_OK > /tmp/tcc-check.txt || echo CAPTURE_DENIED > /tmp/tcc-check.txt
EOF
chmod +x /tmp/tcc-check.command; rm -f /tmp/tcc-check.txt; open -a Terminal /tmp/tcc-check.command; sleep 5; cat /tmp/tcc-check.txt'
```

Dispatch the GUI task only on `CAPTURE_OK`. On `CAPTURE_DENIED` (or no output),
stop and ask the human to grant the permissions above, then re-run the check.

### 4. Liveness and results

```sh
ssh <mac> 'pgrep -fl "codex.*exec"; tail -n 20 <workdir>/codex-run1-<label>.log; head -1 <workdir>/REPORT.md'
```

Poll every 20-30 s from a background task, not in a foreground loop. The log
prints `session id: <uuid>` near the top. Continue the same session for a
follow-up directive with `codex exec resume <id>` (same cwd rule as the local
codex-implement skill: run it from the original working directory).

Extract the id from the previous run's log BEFORE truncating or overwriting it,
and never run `: > codex.log` before that copy:

```sh
ssh <mac> 'grep -m1 "session id:" <workdir>/codex-run1-<label>.log'
```

An EMPTY id is dangerous: `codex exec resume` with no id silently starts a NEW
session whose only context is the directive. Check the id is non-empty before
resuming. Write the next run to a fresh log (`codex-run2-<label>.log`).

When you resume to answer a confirmation the previous run stopped on, re-state
the remaining steps in the directive; the resumed run should not be assumed to
carry the plan forward.

When `head -1 REPORT.md` shows `STATUS: DONE`, bring deliverables back:

```sh
scp <mac>:<workdir>/<deliverable> ./
```

On `LOGIN_REQUIRED` or `PERMISSION_REQUIRED: <which>`, ask the human to fix it,
then relaunch or resume.

### 5. Gotchas

- `pkill -f` inside an ssh one-liner can match its own command line. Use a
  bracket trick: `pkill -f 'chrome-cd[p]'`.
- The remote codex may run under a different account than the GUI user. Check
  with `ssh <mac> who`.
- Do not copy a browser profile when the GUI session's Chrome is already
  signed in.
- Tool outputs land in the remote workdir; fetch them with scp.
- Keep the brief free of secrets.
