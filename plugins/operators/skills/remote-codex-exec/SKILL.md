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
```

Keep secrets out of the brief.

### 2. Plain detached launch (non-GUI work)

```sh
ssh <mac> 'nohup sh -c "cat /tmp/brief.md | codex --dangerously-bypass-approvals-and-sandbox exec --skip-git-repo-check -c model_reasoning_effort=high -C <workdir> > <workdir>/codex.log 2>&1" >/dev/null 2>&1 &'
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
cat /tmp/brief.md | codex --dangerously-bypass-approvals-and-sandbox exec --skip-git-repo-check -c model_reasoning_effort=high -C <workdir> > <workdir>/codex.log 2>&1
SCRIPT
ssh <mac> 'chmod +x <workdir>/run.command && open -a Terminal <workdir>/run.command'
```

Terminal is the TCC principal. The human allows Screen Recording and
Accessibility for Terminal once (System Settings, Privacy & Security), plus any
Codex helper that prompts. After that every future run inherits the grants.

### 4. Liveness and results

```sh
ssh <mac> 'pgrep -fl "codex.*exec"; tail -n 20 <workdir>/codex.log; head -1 <workdir>/REPORT.md'
```

Poll every 20-30 s from a background task, not in a foreground loop. The log
prints `session id: <uuid>` near the top. Continue the same session for a
follow-up directive with `codex exec resume <id>` (same cwd rule as the local
codex-implement skill: run it from the original working directory).

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
