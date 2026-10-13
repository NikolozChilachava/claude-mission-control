#!/usr/bin/env python3
"""Non-blocking, safe metadata-only hook receiver for Claude Code.

Does NOT record tool inputs, message texts, prompt contents or tool output.
"""
import json
import os
import sys
import time
from pathlib import Path

try:
    body = sys.stdin.read(250_000)
    event = json.loads(body)
    if isinstance(event,dict):
        safe = {'at':time.time(), 'event':str(event.get('hook_event_name') or '')[:60]}
        for k in ('session_id','agent_id','agent_type','task_id','task_subject'):
            if isinstance(event.get(k), (str,int)):
                safe[k] = str(event[k])[:160]
        if safe['event'] in ('SubagentStart','SubagentStop','SessionStart','SessionEnd','TaskCreated','TaskCompleted'):
            dest=Path(os.environ.get('CLAUDE_HOME', str(Path.home()/'.claude'))).expanduser()/'mission-control-events.jsonl'
            dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('a',encoding='utf-8') as file:
                file.write(json.dumps(safe,ensure_ascii=False)+'\n')
except Exception:
    pass  # The observer must NEVER block or break Claude.
sys.exit(0)
