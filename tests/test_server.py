"""Tests for the local transcript reader; no live Claude files required."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


class MissionControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.project = self.home / 'projects' / 'test-project'
        self.project.mkdir(parents=True)
        self.session_id = 's123'
        self.session_path = self.project / f'{self.session_id}.jsonl'
        self.subagents = self.project / self.session_id / 'subagents'
        self.subagents.mkdir(parents=True)
        self.agent_path = self.subagents / 'agent-a123.jsonl'
        self.events_path = self.home / 'mission-control-events.jsonl'
        self._patches = [
            patch.object(server, 'CLAUDE', self.home),
            patch.object(server, 'PROJECTS', self.home / 'projects'),
            patch.object(server, 'TASKS', self.home / 'tasks'),
            patch.object(server, 'EVENTS', self.events_path),
        ]
        for p in self._patches:
            p.start()
            self.addCleanup(p.stop)
        server._CACHE.clear()

    def write_jsonl(self, path, rows):
        path.write_text(''.join(json.dumps(r)+'\n' for r in rows), encoding='utf-8')

    def test_session_discovery(self):
        self.write_jsonl(self.session_path, [{'type':'user','cwd':'/demo/my-project'}])
        result = server.session_paths()
        self.assertEqual(len(result), 1)
        self.assertEqual(server.peek_info(result[0])['name'], 'my-project')

    def test_agent_hook_ids_status_and_totals(self):
        self.write_jsonl(self.session_path, [{'type':'user','cwd':'/demo/my-project'}])
        usage = {'input_tokens':12,'output_tokens':34,'cache_read_input_tokens':56,'cache_creation_input_tokens':78}
        assistant = {'type':'assistant','timestamp':'2026-10-13T09:00:00Z','message':{
            'id':'msg-123','model':'claude-sonnet','usage':usage,'stop_reason':'end_turn',
            'content':[{'type':'tool_use','id':'tool-1','name':'Read','input':{'file_path':'/demo/example.txt'}}]}}
        self.write_jsonl(self.agent_path, [assistant, assistant])
        (self.subagents/'agent-a123.meta.json').write_text(json.dumps({'agentType':'Explore','description':'Find tests'}),encoding='utf-8')
        self.write_jsonl(self.events_path, [
            {'event':'SubagentStart','agent_id':'agent-a123','session_id':self.session_id,'at':1710000000},
            {'event':'SubagentStop','agent_id':'agent-a123','session_id':self.session_id,'at':1710000030},
            {'event':'TaskCreated','task_id':'1','task_subject':'Review','session_id':self.session_id},
            {'event':'TaskCompleted','task_id':'1','session_id':self.session_id},
            {'event':'TaskCreated','task_id':'2','task_subject':'Test','session_id':self.session_id},
        ])
        data = server.get_session(self.session_path)
        self.assertEqual(data['agents'][0]['status'], 'done')
        self.assertEqual(data['agents'][0]['model'], 'claude-sonnet')
        self.assertEqual(data['agents'][0]['tokens']['output'], 34) # repeated message counted once
        self.assertEqual(data['agents'][0]['toolCount'], 1)
        self.assertEqual(data['taskProgress'], {'done':1,'total':2,'percent':50})

    def test_no_tasks_means_no_fabricated_progress(self):
        self.write_jsonl(self.session_path, [])
        data = server.get_session(self.session_path)
        self.assertIsNone(data['taskProgress']['percent'])

    def test_tool_action_does_not_expose_shell_command(self):
        result = server.action_title({'name':'Bash','input':{'command':'echo very_secret_password'}})
        self.assertEqual(result, 'Running shell command')
        self.assertNotIn('very_secret_password',result)


if __name__ == '__main__':
    unittest.main()
