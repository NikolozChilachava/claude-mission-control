'use strict';
const $ = id => document.getElementById(id);
const state = {mode:'live', sessions:[], selected:null, data:null, filter:'all', inspected:null, lastRefresh:0, lastSessionListAt:0, loading:false};
const palettes = ['#82e4bd','#829fee','#b898ee','#f3b582'];
const demo = (()=> {
  const now=Date.now(); const when=m=>new Date(now-m*60000).toISOString();
  const agents=[
    {id:'frontend-7c2',name:'Implement authentication UI',type:'Frontend engineer',parentId:'',status:'running',model:'claude-sonnet-4-6',tokens:{input:1050,output:8279,cacheRead:68290,cacheWrite:14200},toolCount:32,lastAction:'Editing · LoginForm.tsx',firstActivity:when(16),lastActivity:when(.2),actions:[{time:when(.2),label:'Editing · LoginForm.tsx',tool:'Edit'},{time:when(1.3),label:'Reading · auth.ts',tool:'Read'},{time:when(2.2),label:'Running shell command',tool:'Bash'}]},
    {id:'security-a81',name:'Review authentication & RBAC',type:'Security reviewer',parentId:'',status:'running',model:'claude-opus-5-5',tokens:{input:3060,output:15742,cacheRead:134200,cacheWrite:29400},toolCount:51,lastAction:'Searching files',firstActivity:when(21),lastActivity:when(.5),actions:[{time:when(.5),label:'Searching files',tool:'Grep'},{time:when(2),label:'Reading · permissions.ts',tool:'Read'},{time:when(3),label:'Reading · routes.ts',tool:'Read'}]},
    {id:'tests-e23',name:'Write integration tests',type:'Test engineer',parentId:'frontend-7c2',status:'recent',model:'claude-haiku-4-5',tokens:{input:452,output:3940,cacheRead:35800,cacheWrite:6400},toolCount:18,lastAction:'Running shell command',firstActivity:when(13),lastActivity:when(1.2),actions:[{time:when(1.2),label:'Running shell command',tool:'Bash'},{time:when(2.5),label:'Writing · auth.test.ts',tool:'Write'}]},
    {id:'docs-b45',name:'Document API contracts',type:'Documentation',parentId:'',status:'done',model:'claude-sonnet-4-6',tokens:{input:802,output:6122,cacheRead:54780,cacheWrite:10900},toolCount:24,lastAction:'Writing · API.md',firstActivity:when(42),lastActivity:when(12),actions:[{time:when(12),label:'Writing · API.md',tool:'Write'},{time:when(15),label:'Reading · schema.ts',tool:'Read'}]},
  ];
  for(let a of agents){a.models={[a.model]:Object.values(a.tokens).reduce((s,x)=>s+x,0)};a.partial=false;}
  const tasks=[{id:'1',name:'Map existing authentication flows',status:'completed'},{id:'2',name:'Implement protected routing',status:'completed'},{id:'3',name:'Write role-based access tests',status:'in_progress'},{id:'4',name:'Validate API authorization checks',status:'in_progress'},{id:'5',name:'Review final changes and documentation',status:'pending'}];
  const totals={input:0,output:0,cacheRead:0,cacheWrite:0};for(let a of agents)for(let k in totals)totals[k]+=a.tokens[k];
  const activity=agents.flatMap(a=>a.actions.map(x=>({...x,agentId:a.id,agentName:a.name}))).sort((a,b)=>b.time.localeCompare(a.time));
  return {session:{id:'demo',name:'agentic-lender',updated:when(0),model:'claude-opus-5-5'},agents,main:{model:'claude-opus-5-5',toolCount:10,actions:[{time:when(.7),label:'Delegating work',tool:'Agent'}]},tasks,taskProgress:{done:2,total:5,percent:40},totals,activity,hooksInstalled:true,polledAt:new Date(now).toISOString(),dataSource:'Illustrative demo data'};
})();
function escapeHTML(input){return String(input ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function short(n){n=Number(n)||0;if(n>=1e6)return (n/1e6).toFixed(n>=10e6?1:2).replace(/\.?0+$/,'')+'M';if(n>=1000)return (n/1000).toFixed(n>=10000?0:1).replace(/\.0$/,'')+'k';return String(n);}
function ago(s){let d=Date.parse(s);if(!Number.isFinite(d))return 'Unknown';const t=Math.max(0,Date.now()-d);if(t<55000)return 'just now';if(t<3600000)return Math.floor(t/60000)+' min ago';if(t<86400000)return Math.floor(t/3600000)+' hr ago';return Math.floor(t/86400000)+'d ago';}
function clock(){const date=new Date();$('clock').textContent=date.toLocaleTimeString('en-GB',{hour12:false});$('clock-tz').textContent=(Intl.DateTimeFormat().resolvedOptions().timeZone||'');}
function notice(message){const el=$('notice');el.classList.toggle('hidden',!message);el.textContent=message||'';}
function connection(){const pill=$('connect-pill');pill.className='connect-pill '+(state.mode==='demo'?'demo':state.data?'connected':'');pill.querySelector('span').textContent=state.mode==='demo'?'DEMO DATA':state.data?'LOCAL · CONNECTED':'NOT CONNECTED';$('demo').textContent=state.mode==='demo'?'↩ Back to live':'◉ Demo mode';$('scan-title').textContent=state.mode==='demo'?'SAMPLE DATA ACTIVE':'READ-ONLY MONITOR';$('scan-sub').textContent=state.mode==='demo'?'Not connected to real agents':'Scanning local Claude sessions';$('stream-label').textContent=state.mode==='demo'?'SAMPLE FEED':'LOCAL RECORDS';}
async function listSessions(){
  try{const r=await fetch('/api/sessions',{cache:'no-store'});if(!r.ok)throw Error('Server returned '+r.status);const data=await r.json();state.sessions=data.sessions||[];renderSelect();
   state.lastSessionListAt=Date.now();
   if(!data.pathExists)notice('No Claude Code transcript folder found. If your sessions run in the cloud or a different user profile, this observer cannot access them. Switch to Demo mode to preview the interface.');
   else if(!state.sessions.length)notice('No local Claude Code sessions found yet. Start a local session in Claude Desktop, or explore the demo.');
   else notice('');
   if(!state.selected||!state.sessions.some(s=>s.id===state.selected))state.selected=state.sessions[0]?.id||null;
   $('session-select').value=state.selected||'';
   return true;
  }catch(err){notice('Could not reach the local reader. Run START-WINDOWS.bat, then reload this page. '+err.message);return false;}
}
function renderSelect(){const select=$('session-select');select.replaceChildren();if(state.mode==='demo'){const o=document.createElement('option');o.textContent='agentic-lender · sample workspace';o.value='demo';select.append(o);return;}if(!state.sessions.length){let o=document.createElement('option');o.value='';o.textContent='No local sessions';select.append(o);return;}
  state.sessions.forEach(s=>{const o=document.createElement('option');o.value=s.id;o.textContent=`${s.name} · ${s.id.slice(0,8)} · ${ago(s.updated)}`;select.append(o)});
}
async function load(){
 if(state.mode==='demo'){state.data=demo;renderSelect();render();return;}
 if(!state.selected){state.data=null;render();return;}
 try{const r=await fetch('/api/session?id='+encodeURIComponent(state.selected),{cache:'no-store'});if(!r.ok)throw Error('Could not read session');state.data=await r.json();state.lastRefresh=Date.now();render();}
 catch(e){notice('Error reading session: '+e.message);state.data=null;render();}
}
function totalTokens(t){return Object.values(t||{}).reduce((s,n)=>s+(Number(n)||0),0)}
function render(){const d=state.data;connection();
 $('agent-count').textContent=d?short(d.agents.length):'0';$('agent-foot').textContent=d?'All subagents in selected session':'No subagents detected';
 const running=d?d.agents.filter(a=>['running','recent'].includes(a.status)).length:0;
 $('active-count').textContent=short(running);$('active-foot').textContent=d?(d.hooksInstalled?'Hook-reported or recently active':'Transcript activity (approximate)'):'Awaiting local activity';
 $('token-count').textContent=d?short(totalTokens(d.totals)):'0';$('token-foot').textContent=d?.agents.some(a=>a.partial)||d?.main.partial?'Partial: large transcript truncated':'Input + output + cache read/write';
 $('tool-count').textContent=d?short(d.agents.reduce((s,a)=>s+a.toolCount,0)+(d.main?.toolCount||0)):'0';
 $('agent-tag').textContent=d?d.agents.length:'0';
 $('updated-at').textContent=d?`Checked ${ago(d.polledAt)}`:'Not connected';
 renderAgents();renderFeed();renderTasks();renderDonut();renderInspector();
}
function badge(s){const values={running:['RUNNING','running'],recent:['RECENT','recent'],done:['DONE','done'],unknown:['UNKNOWN','']};let [name,cl]=values[s]||values.unknown;return `<span class="status-badge ${cl}">${name}</span>`}
function agentIcon(a,i){return ['◇','⬡','⌘','⟡','◎','✧','◈'][i%7]}
function renderAgents(){const grid=$('agent-grid');const d=state.data;grid.replaceChildren();if(!d||!d.agents.length){grid.innerHTML='<div class="empty-card"><strong>No subagents found for this session.</strong><span class="empty-advice">Claude creates these when it delegates work. Try Demo mode to explore the interface.</span></div>';return;}
 const agents=d.agents.filter(a=>state.filter==='all'||(state.filter==='running'&&['running','recent'].includes(a.status))||(state.filter==='done'&&a.status==='done'));
 if(!agents.length){grid.innerHTML='<div class="empty-card">No agents match this filter.</div>';return;}
 agents.forEach((a,i)=>{const el=document.createElement('button');el.className='agent-card status-'+a.status;el.type='button';el.setAttribute('aria-label','Inspect '+a.name);el.innerHTML=`<div class="agent-head"><div class="agent-avatar v${i%4}">${agentIcon(a,i)}</div><div class="agent-head-labels"><h4 title="${escapeHTML(a.name)}">${escapeHTML(a.name)}</h4><small>${escapeHTML(a.type)}</small></div>${badge(a.status)}</div><div class="agent-description">${escapeHTML(a.lastAction)}</div><div class="agent-mini"><div><label>MODEL</label><strong>${escapeHTML(friendlyModel(a.model))}</strong></div><div><label>TOKENS</label><strong>${short(totalTokens(a.tokens))}</strong></div><div><label>TOOLS</label><strong>${short(a.toolCount)}</strong></div></div><div class="agent-bottom"><span>◷ ${ago(a.lastActivity)}</span><b>INSPECT AGENT ↗</b></div>`;el.addEventListener('click',()=>{state.inspected=a.id;renderInspector();$('inspector').classList.add('open')});grid.appendChild(el)});
}
function friendlyModel(model){if(!model)return 'Unknown';let s=model.replace(/^claude-/,'').replace(/-(20\d\d\d\d\d\d).*$/,'').replace(/-/g,' ');return s.replace(/\b\w/g,x=>x.toUpperCase()).replace(/(\d) (\d)/g,'$1.$2')}
function renderFeed(){const el=$('feed'),d=state.data;el.replaceChildren();$('event-count').textContent=(d?.activity.length||0)+' EVENTS';if(!d?.activity.length){el.innerHTML='<div class="empty-inline">No recent tool events recorded.</div>';return;}
 d.activity.slice(0,14).forEach(a=>{const row=document.createElement('div');row.className='feed-row';let name=a.agentName||'Main session';row.innerHTML=`<div class="feed-dot">↗</div><div><div class="feed-title">${escapeHTML(a.label)}</div><div class="feed-caption">${escapeHTML(name)}</div></div><div class="feed-time" title="${escapeHTML(a.time)}">${ago(a.time)}</div>`;el.appendChild(row)});
}
function renderTasks(){const d=state.data,p=d?.taskProgress;const has=Boolean(p&&p.total);$('task-percent').textContent=has?p.percent+'%':'—';$('task-count').textContent=has?`${p.done} of ${p.total} recorded tasks completed`:'No tracked tasks';$('progress-fill').style.width=(has?p.percent:0)+'%';const list=$('task-list');list.replaceChildren();if(!has){list.innerHTML='<p>No task list detected. Claude needs to create trackable tasks before progress can be calculated. Arbitrary percentages are never guessed.</p>';return;}
 d.tasks.slice(0,8).forEach(t=>{const row=document.createElement('div');row.className='task';row.innerHTML=`<span class="task-marker ${escapeHTML(t.status)}">${t.status==='completed'?'✓':t.status==='in_progress'?'◐':'·'}</span><span class="${t.status==='completed'?'strike':''}">${escapeHTML(t.name)}</span>`;list.appendChild(row)});
}
function renderDonut(){const t=state.data?.totals||{input:0,output:0,cacheRead:0,cacheWrite:0};const all=totalTokens(t);const data=[['Input',t.input,palettes[0]],['Output',t.output,palettes[1]],['Cache read',t.cacheRead,palettes[2]],['Cache write',t.cacheWrite,palettes[3]]];const entries=[];let acc=0;for(let [name,n,color] of data){let next=acc+(all?n/all*100:0);entries.push(`${color} ${acc}% ${next}%`);acc=next;}
 $('donut').style.background=all?'conic-gradient('+entries.join(',')+')':'#253344';$('donut-total').textContent=short(all);const legend=$('legend');legend.replaceChildren();for(let [name,n,color] of data){const row=document.createElement('div');row.className='legend-row';row.innerHTML=`<span class="legend-label"><i class="legend-dot"></i>${name}</span><strong>${short(n)}</strong>`;row.querySelector(".legend-dot").style.backgroundColor=color;legend.append(row)};
}
function renderInspector(){let pane=$('inspector-content');const a=state.data?.agents.find(a=>a.id===state.inspected);if(!a){pane.innerHTML='<div class="inspector-empty">Select an agent to inspect its work.</div>';return;}
const out=Object.values(a.tokens).reduce((s,n)=>s+n,0);
const rows=[['Model',friendlyModel(a.model)],['Agent type',a.type],['Input tokens',short(a.tokens.input)],['Output tokens',short(a.tokens.output)],['Cache read',short(a.tokens.cacheRead)],['Cache write',short(a.tokens.cacheWrite)],['Tool calls',short(a.toolCount)],['Parent agent',a.parentId||'Main session'],['Last update',ago(a.lastActivity)]];
 pane.innerHTML=`<div class="inspect-body"><div class="inspect-avatar">⬡</div><h2>${escapeHTML(a.name)}</h2><p class="inspect-sub">ID ${escapeHTML(a.id)}<br>${badge(a.status)}</p><div class="inspect-section"><h4>CURRENT OBSERVED ACTIVITY</h4><div class="inspect-action">${escapeHTML(a.lastAction)}</div><p class="status-help">Based on recorded tool calls, not access to hidden reasoning. ${a.status==='recent'?'Recent changes do not confirm the agent is still running.':''}</p></div><div class="inspect-section"><h4>AGENT TELEMETRY</h4>${rows.map(([k,v])=>`<div class="inspect-row"><span>${escapeHTML(k)}</span><strong>${escapeHTML(v)}</strong></div>`).join('')}</div><div class="inspect-section"><h4>RECENT ACTIONS</h4>${a.actions.length?a.actions.slice().reverse().slice(0,12).map(x=>`<div class="inspect-feed-item"><i>⌁</i><div>${escapeHTML(x.label)}<span class="inspect-time">${ago(x.time)}</span></div></div>`).join(''):'<p class="inspect-sub">No tool actions recorded.</p>'}</div>${a.partial?'<p class="label-warning">⚠️ Only the most recent 35 MB of this large transcript was parsed. Token totals may be incomplete.</p>':''}</div>`;
}
async function tick(){if(state.mode==='demo')return;const now=Date.now();if(state.loading)return;state.loading=true;try{if(now-state.lastSessionListAt>15000)await listSessions();await load();}finally{state.loading=false;}}
$('demo').addEventListener('click',async()=>{state.mode=state.mode==='demo'?'live':'demo';if(state.mode==='live'){await listSessions();await load()}else{state.data=demo;renderSelect();notice('DEMO MODE — Everything displayed is fictional sample data, not your actual Claude sessions.');render();}});
$('refresh').addEventListener('click',async()=>{await listSessions();await load();});
$('session-select').addEventListener('change',async e=>{state.selected=e.target.value;state.inspected=null;$('inspector').classList.remove('open');if(state.mode==='demo')state.mode='live';await load();});
document.querySelectorAll('.seg').forEach(b=>b.addEventListener('click',()=>{state.filter=b.dataset.filter;document.querySelectorAll('.seg').forEach(x=>x.classList.toggle('selected',x===b));renderAgents()}));
$('close-inspector').addEventListener('click',()=>{$('inspector').classList.remove('open');state.inspected=null;});
$('rail-agents').addEventListener('click',()=>{$('agents-anchor').scrollIntoView({behavior:'smooth'})});
$('rail-activity').addEventListener('click',()=>{$('activity-anchor').scrollIntoView({behavior:'smooth'})});
setInterval(clock,1000);setInterval(tick,2500);clock();connection();(async()=>{await listSessions();await load()})();
