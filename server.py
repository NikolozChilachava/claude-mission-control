#!/usr/bin/env python3
"""Claude Mission Control: local, read-only Claude Code transcript observer."""
import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent
CLAUDE = Path(os.environ.get('CLAUDE_HOME', str(Path.home() / '.claude'))).expanduser()
PROJECTS = CLAUDE / 'projects'
TASKS = CLAUDE / 'tasks'
EVENTS = CLAUDE / 'mission-control-events.jsonl'
MAX_SESSION_FILES = 500
MAX_BYTES = 35 * 1024 * 1024
PORT = 47821
_CACHE = {}

def jload(s):
    try: return json.loads(s)
    except (ValueError, TypeError): return None

def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat().replace('+00:00','Z')

def safe_stat(p):
    try: return p.stat()
    except OSError: return None

def clip(s, n=120):
    if not isinstance(s, str): return ''
    return re.sub(r'[\x00-\x1f]+', ' ', s).strip()[:n]

def session_paths():
    if not PROJECTS.is_dir(): return []
    items = []
    try:
        for folder in PROJECTS.iterdir():
            if not folder.is_dir(): continue
            for f in folder.glob('*.jsonl'):
                st = safe_stat(f)
                if st: items.append((st.st_mtime, f))
    except OSError: pass
    return [p for _,p in sorted(items, reverse=True)[:MAX_SESSION_FILES]]

def peek_info(f):
    """Read bounded tail to get session title/cwd from visible records only."""
    st = safe_stat(f)
    if not st: return {}
    try:
        with f.open('rb') as fh:
            fh.seek(max(0, st.st_size - 180_000))
            lines = fh.read().decode('utf-8', 'replace').splitlines()
    except OSError: return {}
    title = ''; cwd = ''; latest_model = ''
    for line in reversed(lines):
        row = jload(line)
        if not isinstance(row, dict): continue
        cwd = cwd or row.get('cwd') or ''
        if row.get('type') == 'assistant':
            model = (row.get('message') or {}).get('model')
            if isinstance(model,str) and model not in ('<synthetic>',): latest_model = latest_model or model
        if cwd and latest_model: break
    name = Path(cwd).name if cwd else f.parent.name.strip('-').split('-')[-1]
    return dict(id=f.stem, name=clip(name, 65) or 'Project', cwd=clip(cwd, 160), updated=iso(st.st_mtime), model=latest_model, size=st.st_size)

def read_rows(p):
    st = safe_stat(p)
    if not st: return ([], False)
    key = str(p)
    cached = _CACHE.get(key)
    if cached and cached[0] == st.st_size and cached[1] == st.st_mtime_ns:
        return cached[2]
    partial = st.st_size > MAX_BYTES
    rows = []
    try:
        with p.open('rb') as fh:
            if partial:
                fh.seek(st.st_size - MAX_BYTES)
                fh.readline() # skip incomplete first line
            for line in fh:
                if len(line) > 4_000_000: continue
                obj = jload(line)
                if isinstance(obj, dict): rows.append(obj)
    except OSError:
        return ([], False)
    val = (rows, partial)
    _CACHE[key] = (st.st_size, st.st_mtime_ns, val)
    if len(_CACHE) > 150:
        for k in list(_CACHE)[:40]: _CACHE.pop(k, None)
    return val

def action_title(tool):
    name = clip(tool.get('name') or '', 55)
    inp = tool.get('input') or {}
    if not isinstance(inp,dict): inp = {}
    path = inp.get('file_path') or inp.get('path') or inp.get('file') or ''
    short_path = clip(str(path).replace('\\','/').split('/')[-1], 46)
    verbs = {'Read':'Reading', 'Edit':'Editing', 'Write':'Writing', 'Grep':'Searching files', 'Glob':'Locating files', 'Bash':'Running shell command', 'Agent':'Delegating work', 'Task':'Delegating work', 'TodoWrite':'Updating task list', 'TaskCreate':'Creating task', 'TaskUpdate':'Updating task', 'TaskList':'Checking tasks', 'WebSearch':'Searching the web', 'WebFetch':'Reading a web page'}
    head = verbs.get(name, name.replace('_',' ') if name else 'Using tool')
    # Do not display commands, tool outputs or prompt text: they can contain secrets.
    return head + (' · '+ short_path if short_path and name in ('Read','Write','Edit') else '')

def analyze(p):
    rows, partial = read_rows(p)
    msgs = {} # message.id dedupes repeated usage across blocks
    actions = []
    seen_calls = set()
    last_model = ''
    latest = safe_stat(p).st_mtime if safe_stat(p) else time.time()
    first = latest
    for i,row in enumerate(rows):
        t = row.get('timestamp')
        if isinstance(t,str):
            try:
                dt = datetime.fromisoformat(t.replace('Z','+00:00')).timestamp()
                first = min(first,dt)
                latest = max(latest,dt)
            except ValueError: pass
        if row.get('type') != 'assistant': continue
        msg = row.get('message') or {}
        if not isinstance(msg,dict): continue
        model = msg.get('model')
        if model and model not in ('<synthetic>','synthetic'): last_model = model
        usage = msg.get('usage') or {}
        mid = msg.get('id') or row.get('uuid') or f'row-{i}'
        if isinstance(usage,dict) and any(isinstance(usage.get(k),int) for k in ('input_tokens','output_tokens','cache_read_input_tokens')):
            prior = msgs.get(mid)
            definitive = msg.get('stop_reason') is not None
            entry = (definitive, (usage.get('output_tokens') or 0), usage, model)
            if prior is None or (definitive and not prior[0]) or (definitive==prior[0] and entry[1] >= prior[1]):
                msgs[mid] = entry
        contents = msg.get('content') or []
        if isinstance(contents,list):
            for block in contents:
                if isinstance(block,dict) and block.get('type')=='tool_use':
                    call_id = block.get('id')
                    if call_id and call_id in seen_calls: continue
                    if call_id: seen_calls.add(call_id)
                    actions.append({'time':t if isinstance(t,str) else iso(latest), 'label':action_title(block), 'tool':clip(block.get('name',''),30)})
    toks = {'input':0,'output':0,'cacheRead':0,'cacheWrite':0}
    by_model = {}
    for _,_,u,model in msgs.values():
        x = {'input':int(u.get('input_tokens') or 0),'output':int(u.get('output_tokens') or 0),'cacheRead':int(u.get('cache_read_input_tokens') or 0),'cacheWrite':int(u.get('cache_creation_input_tokens') or 0)}
        for k in toks: toks[k] += x[k]
        label = model or 'Unknown'
        by_model[label] = by_model.get(label,0) + sum(x.values())
    return {'model':last_model,'tokens':toks,'models':by_model,'toolCount':len(actions),'actions':actions[-15:], 'lastAction':actions[-1]['label'] if actions else 'No tool activity recorded', 'lastActivity':iso(latest),'firstActivity':iso(first), 'partial':partial}

def agent_meta(path):
    try: data = jload(path.read_text(encoding='utf-8')) if path.is_file() else None
    except (OSError, UnicodeError): data = None
    return data if isinstance(data,dict) else {}

def read_events(session_id):
    if not EVENTS.is_file(): return []
    try:
        with EVENTS.open('rb') as fh:
            st = EVENTS.stat()
            if st.st_size > 2_000_000:
                fh.seek(st.st_size - 2_000_000); fh.readline()
            arr = []
            for line in fh:
                r = jload(line)
                if isinstance(r,dict) and r.get('session_id')==session_id: arr.append(r)
            return arr[-1500:]
    except OSError: return []

def tasks_for(session_id, events):
    found = {}
    for e in events:
        typ = e.get('event')
        tid = str(e.get('task_id') or '')
        if not tid: continue
        if typ=='TaskCreated':
            found[tid] = {'id':tid,'name':clip(e.get('task_subject') or 'Task', 105),'status':'pending'}
        elif typ=='TaskCompleted':
            found.setdefault(tid,{'id':tid,'name':'Task '+tid,'status':'pending'})['status']='completed'
    if TASKS.is_dir():
        names = ('session-'+session_id[:8], 'session-'+session_id, session_id)
        for n in names:
            d = TASKS / n
            if not d.is_dir(): continue
            for f in d.glob('*.json'):
                try: obj=jload(f.read_text(encoding='utf-8'))
                except (OSError,UnicodeError): continue
                if isinstance(obj,dict):
                    tid = str(obj.get('id') or f.stem)
                    status = str(obj.get('status') or 'pending').lower()
                    found[tid] = {'id':tid, 'name':clip(obj.get('subject') or obj.get('activeForm') or 'Task',105),'status':status if status in ('completed','in_progress','pending') else 'pending'}
    return list(found.values())[:100]

def get_session(path):
    meta = peek_info(path)
    aid = meta.get('id')
    events = read_events(aid)
    statuses = {}
    for e in events:
        # Claude emits both `agent-abc` and `abc` depending on version/context.
        agent_id = str(e.get('agent_id') or '').removeprefix('agent-')
        if agent_id and e.get('event') in ('SubagentStart','SubagentStop'):
            statuses[agent_id] = e
        if e.get('event') == 'SessionEnd':
            for key in statuses:
                if statuses[key].get('event')=='SubagentStart': statuses[key]={'event':'SessionEnd'}
    root_dir = path.parent / aid / 'subagents'
    main = analyze(path)
    agents = []
    if root_dir.is_dir():
        files = sorted(root_dir.glob('agent-*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)[:90]
        seen = set()
        for f in files:
            agent_id = f.stem.removeprefix('agent-')
            seen.add(agent_id)
            md = agent_meta(f.with_suffix('.meta.json'))
            a = analyze(f)
            event = statuses.get(agent_id,{})
            event_type = event.get('event')
            minutes = max(0, (time.time()-f.stat().st_mtime)/60)
            if event_type in ('SubagentStop', 'SessionEnd'): status='done'
            elif event_type=='SubagentStart' and (time.time()-float(event.get('at', 0))) < 86400: status='running'
            elif minutes < 2: status='recent'
            else: status='unknown'
            agents.append({'id':agent_id, 'name':clip(md.get('description') or md.get('agentType') or event.get('agent_type') or 'Subagent', 100), 'type':clip(md.get('agentType') or event.get('agent_type') or 'Agent',55), 'parentId':clip(str(md.get('parentAgentId') or ''),60), 'status':status, **a})
        for agent_id,e in statuses.items():
            if agent_id not in seen and e.get('event')=='SubagentStart':
                agents.append({'id':agent_id,'name':clip(e.get('agent_type') or 'Starting agent',80),'type':clip(e.get('agent_type') or 'Agent',50),'parentId':'','status':'running','model':'','tokens':{'input':0,'output':0,'cacheRead':0,'cacheWrite':0},'models':{},'toolCount':0,'actions':[],'lastAction':'Waiting for transcript','lastActivity':iso(e.get('at') or time.time()),'firstActivity':iso(e.get('at') or time.time()),'partial':False})
    tsks = tasks_for(aid,events)
    # Never claim progress if there is no explicit task list.
    finished = sum(1 for t in tsks if t['status']=='completed')
    totals = {'input':main['tokens']['input'], 'output':main['tokens']['output'],'cacheRead':main['tokens']['cacheRead'],'cacheWrite':main['tokens']['cacheWrite']}
    for a in agents:
        for key in totals: totals[key]+=a['tokens'][key]
    activity = []
    for a in agents:
        for action in a['actions']:
            activity.append({**action,'agentId':a['id'],'agentName':a['name']})
    for action in main['actions']:
        activity.append({**action,'agentId':'main','agentName':'Main session'})
    activity.sort(key=lambda e:e.get('time') or '', reverse=True)
    return {'session':meta, 'main':main, 'agents':agents, 'tasks':tsks, 'taskProgress': {'done':finished,'total':len(tsks),'percent':round(finished/len(tsks)*100) if tsks else None}, 'totals':totals, 'activity':activity[:70], 'hooksInstalled':any(x.get('event') in ('SubagentStart','SubagentStop') for x in events), 'dataSource':'Local Claude Code transcripts (read-only)', 'polledAt':iso(time.time())}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args): pass
    def respond(self,body,status=200,content_type='application/json; charset=utf-8'):
        data = body if isinstance(body,bytes) else (json.dumps(body,ensure_ascii=False).encode('utf-8') if content_type.startswith('application/json') else body.encode('utf-8'))
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'self'")
        self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        req=urlparse(self.path)
        if req.path == '/api/sessions':
            paths=session_paths()[:60]
            self.respond({'sessions':[peek_info(f) for f in paths],'pathExists':PROJECTS.is_dir(),'time':iso(time.time())}); return
        if req.path == '/api/session':
            sid=parse_qs(req.query).get('id',[''])[0]
            # Only open IDs returned by our known session index. Do not accept file paths.
            f=next((p for p in session_paths() if p.stem==sid),None)
            if f is None: self.respond({'error':'Session not found'},404)
            else: self.respond(get_session(f))
            return
        if req.path == '/api/health': self.respond({'ok':True,'claudeHome':str(CLAUDE),'projectsExist':PROJECTS.is_dir()}); return
        files={'/':'index.html','/index.html':'index.html','/styles.css':'styles.css','/app.js':'app.js'}
        if req.path in files:
            ext = req.path.rsplit('.',1)[-1]
            typ={'css':'text/css','js':'text/javascript','html':'text/html'}.get(ext,'text/html')+'; charset=utf-8'
            self.respond((ROOT/files[req.path]).read_bytes(),content_type=typ)
        else: self.respond({'error':'Not found'},404)

def main():
    global PORT
    p=argparse.ArgumentParser(description='Read-only dashboard for local Claude Code sessions')
    p.add_argument('--port',type=int,default=PORT)
    args=p.parse_args()
    PORT=args.port
    server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
    print(f'\n  Claude Mission Control → http://localhost:{PORT}')
    print(f'  Reading: {PROJECTS}')
    print('  Local only · read-only · Ctrl+C to stop\n', flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
