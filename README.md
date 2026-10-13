# Claude Mission Control 🚀

**Version 1.0.0** · Local, real-time subagent monitoring for Claude Code.

> **Status:** First public version. Built for Windows and designed to fit Claude Desktop's Browser pane; the server itself also runs on macOS/Linux with Python.

A local, read-only Claude Code monitoring dashboard with an agent fleet view, session activity feed, task progress, and token reporting. **No Anthropic API key, npm, telemetry, or third-party Python packages needed.**

### What you can see

- **Agent fleet:** recorded subagents, model names, lifecycle status, task descriptions and recent actions.
- **Resource telemetry:** transcript-reported input/output/cache tokens and tool calls.
- **Task progress:** only when Claude explicitly creates/completes tasks; never a guessed completion percentage.
- **Agent inspector:** click an agent to inspect observed activity and token breakdown.
- **Demo mode:** clearly-labelled sample data for trying the interface.

**Privacy:** This is a passive **local observer**, not a cloud service. It does not modify your Claude sessions or access hidden reasoning.


## Quick start (Windows)

1. Install Python 3.9+ if necessary (`py -3 --version` in PowerShell).
2. Download the v1.0.0 source ZIP from the GitHub repository, extract it, and double-click **`START-WINDOWS.bat`**. Leave the terminal running.
3. In Claude Desktop's **Code** tab, press **Ctrl+Shift+B** to open the Browser pane (or click the globe/Browser icon).
4. Navigate that pane to **`http://localhost:47821`**, or ask Claude in that code session: **"Open http://localhost:47821 in your Browser pane."** You can also open the URL in Chrome/Edge.
5. Pick your local project/session from the session dropdown. The dashboard refreshes automatically about every 2.5 seconds.

To try the interface before a session starts, click **Demo mode**. Demo content is *explicitly fictional* and not live agent data.

## Optional: agent start/stop and task progress events

This is not required to monitor transcripts. Without hooks, an agent that changed its transcript recently is labelled **Recent**, NOT **Running**, because an active file does not guarantee the agent is running.

To enable more reliable lifecycle signals, **close Claude Desktop first** and run:

```powershell
py -3 install_hooks.py
```

**Warning:** This changes your global Claude Code hooks configuration. Review `install_hooks.py` before running it. The hooks invoke a local Python process on matching events.

This makes a timestamped backup of `~/.claude/settings.json`, then **merges** in extra hook entries, preserving any existing hooks. On new agent start/stop, Claude records an event. For progress percentages, Claude must actually use its TaskCreate / TaskCompleted tools or persisted tasks; the dashboard never fabricates completion percentages.

The hook script only records event names, session IDs, agent IDs/types, task IDs and short task titles. **It does not copy chat prompts, command bodies, tool inputs or outputs.** The original transcript files are read, never modified.

Hooks are optional and may not run on older Claude Code / Desktop versions. Tasks/events produced before installation cannot be reconstructed perfectly. Settings modifications are explicit and opt-in.

## What is real / what is not

| Signal | Source | Notes |
|---|---|---|
| Agent hierarchy and description | `~/.claude/projects/.../<session>/subagents/agent-*.meta.json` | Parent ID available in newer transcript formats |
| Model, tool activity | Local JSONL subagent transcripts | Model per agent; tool names only (not secrets) |
| Tokens | JSONL model usage | Deduplicated by `message.id`; includes cache reads/writes; **not billing cost** |
| Agent Running/Done | Optional lifecycle hooks | Without hooks show `Recent` / `Unknown`. Stale hook signals possible after an app crash. |
| Progress % | Claude task files or optional task hooks | Only shown if there are tracked tasks; **not a prediction of remaining work** |
| Future plans | Not reliably available | Private reasoning is never accessible. A recorded task list is the closest supported proxy. |
| All task types | Only Claude Code local sessions | Cloud sessions, some special desktop tasks, remote WSL and unsupported formats may not appear. |

The reader parses up to the **most recent 35 MB** of any individual transcript. If a transcript exceeds that size, totals may be **partial**, and the dashboard marks them accordingly. Most recently active sessions are scanned first.

## Privacy & safety

- HTTP listener is **bound to 127.0.0.1 only**; not accessible from other devices by default.
- Does not upload any data. No CDN, analytics, API key or telemetry. Zero dependencies beyond Python 3.9+.
- Read-only session scanner. The *optional* installer changes Claude settings by adding hooks with an explicit backup; the optional hook logger writes its own metadata file under `.claude`.
- Does not reveal prompt text, bash command bodies or model hidden reasoning.
- Keep the local dashboard private if your transcripts contain sensitive metadata; the observed tool filenames and task names can still be private.

## Terminal use

```powershell
py -3 server.py --port 47821
```

For WSL, set `CLAUDE_HOME` to a mapped folder (`/mnt/c/Users/.../.claude`), then start the server in WSL. For custom ports, pass `--port` and change the Browser URL to match.

Stop with **Ctrl+C** in the server terminal.

## Troubleshooting

- No projects found: verify that `%USERPROFILE%\.claude\projects` has your session transcripts. This dashboard does not use the Claude Desktop UI's private internal task API.
- No tokens / agent status: the agent may not yet have written a transcript, may run in the cloud, or your Claude format may differ. Model and token counts require `message.usage` in the JSONL.
- Browser pane not visible: select Claude Code's **Code tab**, then **Ctrl+Shift+B**. Not the Chat tab.
- A hook reports Running forever: the session may have crashed before its stop event; the badge is a hook-based best-effort status, not proof of a live process.

Built as a separate web app running **inside the Claude Browser pane**. It does **not replace or restyle** Claude's native Background Tasks popup.

## What this does NOT do

- It cannot force Claude Desktop to display the Browser pane automatically. Open it once and keep it beside your work.
- The Python server does not spend model tokens to refresh. Your actual agents still spend their normal tokens.
- The optional hook installer **records metadata**; it does **not** launch the server or browser automatically.
- A public GitHub repository contains the **application source only**, never your local Claude transcripts, credentials or hook logs.

## Contributing and planned updates

This repository starts at **v1.0.0**. Future versions will focus on richer agent timelines, improved progress reporting, and broader Claude Desktop compatibility. Bug reports and feature requests are welcome via GitHub Issues.

See [CHANGELOG.md](CHANGELOG.md) for version history.

## License

No open-source license has been selected yet. Public availability on GitHub does not itself grant permission to reuse, modify or redistribute this code.
