#!/usr/bin/env python3
"""Opt-in metadata-only hooks. Safely preserves existing settings and makes backup."""
import json
import os
import shutil
import sys
from pathlib import Path
from datetime import datetime

def main():
    settings=Path(os.environ.get('CLAUDE_HOME', str(Path.home()/'.claude'))).expanduser()/'settings.json'
    settings.parent.mkdir(parents=True,exist_ok=True)
    if settings.exists():
        try: data=json.loads(settings.read_text(encoding='utf-8-sig'))
        except (OSError,ValueError) as e: raise SystemExit(f'Cannot parse {settings}. Nothing changed: {e}')
        if not isinstance(data,dict): raise SystemExit('settings.json must contain an object. Nothing changed.')
        backup=settings.with_name('settings.json.backup-mission-control-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
        shutil.copy2(settings,backup)
        print('Backup:',backup)
    else: data={}
    hook=Path(__file__).with_name('hook_event.py').resolve()
    # Quote Python and script paths (including Program Files spaces on Windows).
    command='"'+str(Path(sys.executable).resolve())+'" "'+str(hook)+'"'
    events=['SubagentStart','SubagentStop','TaskCreated','TaskCompleted','SessionEnd']
    hooks=data.setdefault('hooks',{})
    if not isinstance(hooks,dict):raise SystemExit('Invalid hooks section; nothing changed.')
    touched=[]
    for event in events:
        items=hooks.setdefault(event,[])
        if not isinstance(items,list):raise SystemExit(f'Invalid {event} hooks; nothing changed.')
        if not any(isinstance(h,dict) and any('hook_event.py' in str(x.get('command','')) for x in h.get('hooks',[]) if isinstance(x,dict)) for h in items):
            items.append({'hooks':[{'type':'command','command':command,'timeout':5}]})
            touched.append(event)
    temp=settings.with_name(settings.name+'.missioncontrol.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(settings)
    print('Installed metadata-only hooks for:', ', '.join(touched) or '(already installed)')
    print('Restart or resume your Claude Code session to enable them.')
    print('To remove: restore the backup, or remove only the mission-control hooks from settings.json.')

if __name__=='__main__':main()
