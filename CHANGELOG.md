# Changelog

All notable changes to Claude Mission Control are documented here.

## [1.0.0] - 2026-10-13

### Initial public version

- Local live dashboard for Claude Code sessions and subagents.
- Session selector, agent cards and searchable session activity.
- Per-agent model, recorded tool actions and token usage.
- Optional lifecycle and task hooks with settings backup.
- Task completion progress based only on recorded tasks.
- Demo mode and detail inspector.
- Python standard-library server; no API keys, dependencies or external telemetry.

### Known limitations

- The dashboard cannot read every Claude Desktop cloud/background task.
- Hook state may be stale after crashes, and uninstrumented tasks may show as Recent/Unknown.
- Task percentages are based on explicit task records, not completion predictions.
- Token totals are transcript-derived and may not match subscription usage.

## Future

Suggestions and improvements can be tracked using GitHub Issues. Version 1 focuses on dependable passive monitoring; future enhancements can add visualizations and integrations.
