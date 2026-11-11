import json
import contextlib
import os
import shutil
import subprocess
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import pc_mesh as mesh
import update_control as control
from install import hooks


class UpdateState(unittest.TestCase):
    @unittest.skipIf(os.name=='nt','native controlling Unix terminal')
    def test_phone_width_survives_piped_prompt_output(self):
        import pty, fcntl, termios, struct, sys
        master,slave=pty.openpty()
        fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',24,32,0,0))
        def control_terminal():
            os.setsid(); fcntl.ioctl(0,termios.TIOCSCTTY,0)
        try:
            result=subprocess.run([sys.executable,'-c','import pc_mesh; print(pc_mesh.terminal_width())'],stdin=slave,capture_output=True,text=True,
                                  cwd=Path(mesh.__file__).parent,preexec_fn=control_terminal,timeout=5)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout.strip(),'32')
        finally:
            os.close(master);os.close(slave)
    def test_zero_after_installation_cannot_be_undone_by_old_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            hub = mesh.Hub({'members':[{'id':'test','name':'Test'}]}, directory)
            now = time.time()
            def report(count, checked):
                hub.report('test', {'updates':{'status':'OK','count':count,'packages':['p'] if count else [],'checked_at':checked}})
            report(1, now-10)
            report(0, now)
            report(1, now-10)
            self.assertEqual(hub.nodes['test']['updates']['count'], 0)
            self.assertEqual(hub.sequence, 2)
            self.assertEqual(hub.nodes['test']['last_good_updates']['count'], 0)
            text, _ = mesh.prompt_output(directory)
            mesh.save_json(Path(directory)/'fleet.json',hub.snapshot())
            text, _ = mesh.prompt_output(directory)
            self.assertNotIn('1 ausstehende Updates',text)
            self.assertIn('Test: 0',text)

    def test_scan_failure_preserves_last_verified_count_as_cached(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory)
            mesh.save_json(state/'local.json', {'updates':{'status':'OK','count':7,'packages':['pkg-a'],'checked_at':123.0}})
            with patch.object(mesh.platform,'system',return_value='NetBSD'), patch.object(mesh,'scan_pkgin',side_effect=TimeoutError('collector timeout')):
                result=mesh.collect_updates(state,Path('.'))
            self.assertEqual(result['status'],'CACHED')
            self.assertEqual(result['count'],7)
            self.assertEqual(result['checked_at'],123.0)
            self.assertIn('collector timeout',result['error'])
            self.assertIn('scan_error_at',result)

    @unittest.skipIf(os.name=='nt','Linux machine-service handover helpers')
    def test_linux_machine_handover_removes_only_managed_cron_blocks(self):
        import enable_machine_updates as machine_enable
        original='MAILTO=owner@example.invalid\n# BEGIN PC-MESH\n* * * * * old-supervisor\n# END PC-MESH\n15 4 * * * owner-job\n# BEGIN UPDATEWULF\n@reboot new-daemon\n# END UPDATEWULF\n'
        result=machine_enable.managed_cron_removed(original)
        self.assertEqual(result,'MAILTO=owner@example.invalid\n15 4 * * * owner-job\n')
        broken='# BEGIN PC-MESH\n* * * * * old\n# END PC-MESH\n# BEGIN UPDATEWULF\n@reboot incomplete\n'
        with self.assertRaisesRegex(RuntimeError,'Incomplete managed cron block'):
            machine_enable.managed_cron_removed(broken)
        source=(Path(mesh.__file__).parent/'enable_machine_updates.py').read_text()
        self.assertNotIn("manage.py','stop",source)
        self.assertNotIn('SIGKILL',source)
        self.assertNotIn('SIGTERM',source)
        self.assertIn('cooperative_stop(state)',source)
        self.assertIn('wait_fresh_worker(state,started)',source)

    @unittest.skipIf(os.name=='nt','NetBSD rc.d adapter source checks')
    def test_netbsd_rcd_adapter_is_cooperative_and_removes_managed_cron(self):
        import enable_machine_updates_netbsd as netbsd_enable
        original='# BEGIN PC-MESH\n* * * * * old\n# END PC-MESH\n22 3 * * * keep-me\n# BEGIN UPDATEWULF\n@reboot old-v2\n# END UPDATEWULF\n'
        self.assertEqual(netbsd_enable.managed_cron_removed(original),'22 3 * * * keep-me\n')
        script=netbsd_enable.rc_script()
        self.assertIn('# REQUIRE: NETWORKING',script)
        self.assertIn('stop.request',script)
        self.assertIn('updatewulf_stop()',script)
        self.assertIn('extra_commands="status"',script)
        self.assertNotIn('SIGTERM',script)
        self.assertNotIn('SIGKILL',script)
        self.assertNotIn('kill ',script)
        source=(Path(mesh.__file__).parent/'enable_machine_updates_netbsd.py').read_text()
        self.assertNotIn('shell=True',source)
        self.assertIn("glob.glob('/etc/rc.d/*')",source)

    def test_pkgin_zero_in_stderr_and_invalid_output(self):
        with patch.object(mesh.os,'geteuid',return_value=1000,create=True), patch.object(mesh,'run',return_value=(0,'','nothing to do.')):
            self.assertEqual(mesh.scan_pkgin(Path('.'))['count'],0)
        with patch.object(mesh.os,'geteuid',return_value=1000,create=True), patch.object(mesh,'run',return_value=(1,'',"pkgin: You don't have enough rights for this operation.")):
            with self.assertRaises(RuntimeError): mesh.scan_pkgin(Path('.'))
        with patch.object(mesh.os,'geteuid',return_value=1000,create=True), patch.object(mesh,'run',return_value=(0,'2 packages to upgrade:','')):
            self.assertEqual(mesh.scan_pkgin(Path('.'))['count'],2)

    def test_prompt_uses_machine_name_without_dns_suffix_and_offline_fallback(self):
        now = time.time()
        fleet = {'generated_at':now,'offline_after':150,'stale_after':5400,
                 'nodes':[
                     {'id':'phobos','name':'PHOBOS','hostname':'PHOBOS.lan','received_at':now,
                      'updates':{'status':'OK','count':1,'checked_at':now}},
                     {'id':'alpha','name':'ALPHA-PC','received_at':0,
                      'updates':{'status':'UNKNOWN','count':None}},
                     {'id':'pi','name':'Gateway','enrolled_hostname':'gateway.local','received_at':0,
                      'updates':{'status':'UNKNOWN','count':None}},
                     {'id':'hp-netbsd','name':'unsafe name!','received_at':0,
                      'updates':{'status':'UNKNOWN','count':None}}]}
        self.assertEqual(mesh.display_machine_name(fleet['nodes'][0]),'PHOBOS')
        self.assertEqual(mesh.display_machine_name(fleet['nodes'][1]),'ALPHA-PC')
        self.assertEqual(mesh.display_machine_name(fleet['nodes'][2]),'gateway')
        self.assertEqual(mesh.display_machine_name(fleet['nodes'][3]),'hp-netbsd')
        prompt=mesh.fleet_preprompt(fleet,now=now,width=240,color=False)
        self.assertIn('PHOBOS 1 Update(s)',prompt)
        for name in ('ALPHA-PC','gateway','hp-netbsd','? Update(s)'):
            self.assertNotIn(name,prompt)
        self.assertNotIn('.local',prompt)
        self.assertNotIn('.lan',prompt)
        self.assertNotIn('?.local',prompt)
        # Rendering must not make display names usable as remote identities.
        self.assertEqual(mesh.canonical_hostname('PHOBOS.lan'),'PHOBOS')

    def test_complete_pending_prompt_is_one_line_and_omits_offline_zero(self):
        now=time.time()
        names=['Android-S23','ALPHA','RemoteStation','Builder','PHOBOS','Gateway','HubServer','A71']
        nodes=[{'id':name.lower(),'name':name,
                'received_at':now-500 if name=='Builder' else now,
                'updates':{'status':'OK','count':i,'checked_at':now}}
               for i,name in enumerate(names)]
        nodes.append({'id':'unknown','name':'unknown','received_at':0,
                      'updates':{'status':'UNKNOWN','count':None}})
        fleet={'nodes':nodes,'generated_at':now,'offline_after':150,'stale_after':5400}
        for width in (22,44,80,160,300):
            render=mesh.SGR_PATTERN.sub('',mesh.fleet_preprompt(fleet,now=now,width=width,color=True))
            self.assertNotIn('\\n',render)
            self.assertLess(len(render),width,(width,render))
            self.assertNotIn('Android-S23',render)
            self.assertNotIn('unknown',render)
            self.assertIn('UpdateWulf',render)
            if width == 300:
                for name in names[1:]:
                    self.assertIn(name,render)
                self.assertIn('+1',render)
                self.assertIn('[off]',render)
                self.assertNotIn('...',render)
        short=mesh.fleet_preprompt(fleet,now=now,width=44,color=False)
        self.assertLess(len(short),44)

    def test_update_case_insensitive_in_both_command_orders(self):
        self.assertEqual(mesh.parse_operator_order('Update','hubserver'),('update','hubserver'))
        self.assertEqual(mesh.parse_operator_order('gateway','UPDATE'),('update','gateway'))
        self.assertEqual(mesh.parse_operator_order('REFRESH','Builder'),('refresh','Builder'))

    def test_client_http_400_is_not_network_timeout_or_retried(self):
        import io
        from urllib.error import HTTPError
        from unittest.mock import Mock
        with patch.object(mesh.ssl,'create_default_context',return_value=Mock()):
            client=mesh.Client({'certificate':'unused','token':'fixture',
                                'hubs':['https://hub-a.invalid','https://hub-b.invalid']})
        response=HTTPError('https://hub-a.invalid/fleet',400,'Bad Request',
                           {'Content-Type':'application/json; charset=utf-8'},
                           io.BytesIO(b'{"error":"invalid cursor"}'))
        with patch.object(mesh.urllib.request,'urlopen',side_effect=response) as request:
            with self.assertRaisesRegex(RuntimeError,'hub rejected /fleet: HTTP 400; invalid cursor'):
                client.request('/fleet')
            self.assertEqual(request.call_count,1)

    @unittest.skipUnless(os.name != 'nt' and shutil.which('bash'),'Native Unix Bash required')
    def test_multiline_bash_prompt_shows_entire_cache(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'fleet-prompt.bash.80').write_text(
                '[ UpdateWulf ::: ALPHA 1 Update(s)\n  HubServer 92 Update(s) ]\n')
            (root/'heartbeat.txt').write_text(str(int(time.time()))+'\n')
            template=(Path(mesh.__file__).parent/'hooks/updatewulf.bash.in').read_text()
            hook=root/'prompt.bash'
            hook.write_text(template.replace('__STATE_QUOTED__',repr(str(root))))
            program='source "$1"; _updatewulf_prompt_attach; printf "%s\n" "$PS1"'
            result=subprocess.run(
                ['bash','--noprofile','--norc','-ic',program,'bash',str(hook)],
                capture_output=True,text=True,timeout=8)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('HubServer 92 Update(s)',result.stdout)
            self.assertEqual(result.stdout.count('UpdateWulf'),1)

    def test_readonly_hub_diagnose_does_not_enqueue(self):
        import io
        with patch.object(mesh.sys,'argv',['pc_mesh.py','diagnose']), \
             patch.object(mesh,'read_json',return_value={'hubs':['https://a.invalid','https://b.invalid'],'token':'test','certificate':'fixture'}), \
             patch.object(mesh,'Client') as client, \
             contextlib.redirect_stdout(io.StringIO()) as capture:
            client.return_value.request.return_value={'nodes':[{'id':'one'}]}
            self.assertEqual(mesh.main(),0)
        self.assertEqual(client.return_value.request.call_count,2)
        self.assertEqual([item.args[0] for item in client.return_value.request.call_args_list],['/fleet','/fleet'])
        self.assertIn('Hub 1: GET /fleet succeeded',capture.getvalue())
        self.assertIn('Hub 2: GET /fleet succeeded',capture.getvalue())
        self.assertNotIn('fixture',capture.getvalue())

    @unittest.skipIf(os.name == 'nt', 'pwd module is Unix-only')
    def test_netbsd_root_cli_shim_drops_privileges_before_exec(self):
        import install_netbsd_root_cli as cli
        source=cli.shim_source('exampleuser','/home/exampleuser/.local/bin/updatewulf','/usr/pkg/bin/python3')
        compile(source,'operator-shim','exec')
        self.assertLess(source.index('os.setuid'),source.index('os.execv'))
        self.assertIn('uid != account.pw_uid',source)
        self.assertIn('os.environ.clear()',source)
        self.assertNotIn('token',source.lower())

    @unittest.skipUnless(os.name != 'nt' and shutil.which('bash'),'Native Unix Bash syntax test')
    def test_bash_hook_syntax_no_duplicate_tail(self):
        """The Bash prompt must parse as a complete source file.

        An earlier broken tail was missed by an interactive source test that
        left a function defined before reporting the syntax error.
        """
        hook=Path(mesh.__file__).parent/'hooks/updatewulf.bash.in'
        result=subprocess.run(['bash','-n',str(hook)],
                              capture_output=True,text=True,timeout=8)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_cli_status_ansi_roles_and_no_color(self):
        import io
        expected = {
            "QUEUED": "36",
            "RUNNING": "33",
            "SUCCEEDED": "32",
            "FAILED": "31",
            "NEEDS_ADMIN": "35",
            "INTERRUPTED": "33",
        }
        for status, sgr in expected.items():
            with self.subTest(status=status):
                self.assertEqual(mesh.colored_status(status, True),
                                 "\x1b[" + sgr + "m" + status + "\x1b[0m")
                self.assertEqual(mesh.colored_status(status, False), status)
        self.assertEqual(mesh.colored_status("UNKNOWN", True), "UNKNOWN")
        self.assertFalse(mesh.ansi_enabled("auto", io.StringIO()))
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            self.assertFalse(mesh.ansi_enabled("auto", io.StringIO()))
            self.assertTrue(mesh.ansi_enabled("always", io.StringIO()))
        self.assertFalse(mesh.ansi_enabled("never", io.StringIO()))

    def test_fleet_summary_colors_only_status_and_json_is_raw(self):
        import io
        fleet = {
            "generated_at": time.time(),
            "nodes": [],
            "commands": [
                {"target": "phobos", "action": "install", "status": "NEEDS_ADMIN"},
                {"target": "hp", "action": "install", "status": "FAILED"},
                {"target": "hubserver", "action": "install", "status": "RUNNING"},
                {"target": "alpha", "action": "install", "status": "SUCCEEDED"},
            ],
        }
        colored = mesh.fleet_summary(fleet, width=100, color=True)
        self.assertIn("\x1b[33mRUNNING\x1b[0m", colored)
        self.assertIn("\x1b[32mSUCCEEDED\x1b[0m", colored)
        self.assertIn("\x1b[31mFAILED\x1b[0m", colored)
        self.assertIn("\x1b[35mNEEDS_ADMIN\x1b[0m", colored)
        self.assertNotIn("\x1b[", mesh.fleet_summary(fleet, width=100, color=False))
        with tempfile.TemporaryDirectory() as td:
            state = Path(td)
            mesh.save_json(state / "fleet.json", fleet)
            with patch.object(mesh.sys, "argv", ["pc_mesh.py", "status", "--json",
                                                "--color=always", "--state", str(state)]), \
                 contextlib.redirect_stdout(io.StringIO()) as out:
                result = mesh.main()
            self.assertEqual(result, 0)
            self.assertNotIn("\x1b[", out.getvalue())
            self.assertEqual(json.loads(out.getvalue())["commands"][1]["status"], "FAILED")

    def test_native_release_preflight_and_windows_elevation_persistence(self):
        source = (Path(mesh.__file__).parent / "enable_machine_updates_netbsd.py").read_text()
        self.assertIn("'apply_updates.py'", source)
        self.assertIn("'incomplete UpdateWulf release: missing '", source)
        win = (Path(mesh.__file__).parent / "install_windows.ps1").read_text()
        self.assertIn("$oldUserTask.Principal.RunLevel -eq 'Highest'", win)
        self.assertIn("New-ScheduledTaskPrincipal", win)
        self.assertIn("Incomplete UpdateWulf release: missing $required", win)

    def test_phone_summary_keeps_every_host_and_stays_narrow(self):
        fleet={'nodes':[{'id':'x'+str(i),'name':name,'received_at':time.time(),'updates':{'status':'OK','count':i,'checked_at':time.time()}} for i,name in enumerate(['Android','ALPHA','RemoteStation','Builder','PHOBOS','Gateway','HubServer'])]}
        result=mesh.fleet_summary(fleet,width=32)
        self.assertTrue(all(len(line)<=32 for line in result.splitlines()))
        for node in fleet['nodes']: self.assertIn(node['name'],result)

    def test_native_hp_pkgin_refresh_summary_is_counted(self):
        # Direct HP pkgin output, 2026-10-06: refresh is a pending package
        # action even when the version remains python313-3.13.15.
        output='calculating dependencies...done.\n\n1 package to refresh:\npython313-3.13.15\n\n0 to remove, 1 to refresh, 0 to upgrade, 0 to install\n0B to download, 0B of additional disk space will be used\n'
        with patch.object(mesh.os,'geteuid',return_value=1000,create=True), patch.object(mesh,'run',return_value=(0,output,'')):
            result=mesh.scan_pkgin(Path('.'))
            self.assertEqual(result['count'],1)
            self.assertEqual(result['packages'],['python313-3.13.15'])

    @unittest.skipIf(os.name=='nt','native Unix shell hook')
    def test_cli_wrapper_forwards_actions_and_login_hook_is_present(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory)/'home'; source=Path(directory)/'src'
            source.mkdir(); home.mkdir()
            (home/'.bash_profile').write_text('# .bashrc mentioned in a comment only\n')
            (source/'pc_mesh.py').write_text('import json,sys; print(json.dumps(sys.argv[1:]))\n')
            (source/'hooks').mkdir()
            shutil.copy2(Path(mesh.__file__).parent/'hooks/updatewulf.bash.in',source/'hooks/updatewulf.bash.in')
            hooks(source,home/'cache',home)
            command=home/'.local/bin/UpdateWulf'
            result=subprocess.check_output([str(command),'refresh','builder'],text=True)
            args=json.loads(result)
            self.assertIn('refresh',args); self.assertNotIn('status',args)
            self.assertTrue((home/'.local/bin/pc-mesh').exists())
            profile=(home/'.bash_profile').read_text()
            self.assertIn('prompt.bash',profile)
            hook=(home/'.config/pc-mesh/prompt.bash').read_text()
            self.assertIn('_updatewulf_prompt_attach',hook)
            self.assertIn('PROMPT_COMMAND',hook)
            self.assertIn('SHELL_COLOR_PS1_DECORATOR',hook)
            self.assertIn('fleet-prompt.bash.',hook)


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.path=Path(self.tmp.name)/'jobs.json'
        self.members={'a':{'allow_install':True},'b':{}}
        self.queue=control.ControlQueue(self.path,self.members,mesh.read_json,mesh.save_json)
        self.request='a'*24
    def tearDown(self): self.tmp.cleanup()
    def test_control_batch_is_atomic_and_idempotent(self):
        requests=[
            {'target':'a','action':'install','request_id':'1'*24},
            {'target':'b','action':'install','request_id':'2'*24},
        ]
        with self.assertRaises(PermissionError):
            self.queue.enqueue_many('operator',requests)
        self.assertEqual(self.queue.snapshot(),[])

        self.members['b']['allow_install']=True
        first=self.queue.enqueue_many('operator',requests)
        self.assertEqual(len(first),2)
        self.assertEqual(len(self.queue.snapshot()),2)
        second=self.queue.enqueue_many('operator',requests)
        self.assertEqual([j['id'] for j in second],[j['id'] for j in first])
        self.assertEqual(len(self.queue.snapshot()),2)

    def test_control_batch_rejects_duplicate_target_without_partial_enqueue(self):
        requests=[
            {'target':'a','action':'refresh','request_id':'3'*24},
            {'target':'a','action':'sync','request_id':'4'*24},
        ]
        with self.assertRaisesRegex(ValueError,'duplicate target'):
            self.queue.enqueue_many('operator',requests)
        self.assertEqual(self.queue.snapshot(),[])

    def test_ownership_idempotency_restart_and_no_replay(self):
        job=self.queue.enqueue('a','a','refresh',self.request)
        self.assertEqual(self.queue.enqueue('a','a','refresh',self.request)['id'],job['id'])
        for caller,target,action in [('a','b','refresh'),('operator','b','install'),('reader','a','refresh')]:
            with self.assertRaises(PermissionError): self.queue.enqueue(caller,target,action,'b'*24)
        with self.assertRaises(PermissionError): self.queue.result('b',job['id'],'RUNNING')
        self.queue.result('a',job['id'],'RUNNING')
        restarted=control.ControlQueue(self.path,self.members,mesh.read_json,mesh.save_json)
        self.assertEqual(restarted.pending('a'),[])
        restarted.result('a',job['id'],'SUCCEEDED')
        self.assertEqual(restarted.result('a',job['id'],'RUNNING')['status'],'SUCCEEDED')
    def test_expired_host_request_does_not_run_later_or_block_new_work(self):
        job=self.queue.enqueue('operator','a','install',self.request)
        self.queue.jobs[0]['expires_at']=time.time()-1
        self.assertEqual(self.queue.pending('a'),[])
        self.assertEqual(self.queue.snapshot()[0]['status'],'EXPIRED')
        self.queue.enqueue('operator','a','refresh','b'*24)
    def test_arbitrary_command_cannot_be_submitted(self):
        for action in ['reboot','sh -c id','install; rm x']:
            with self.assertRaises(ValueError): self.queue.enqueue('operator','a',action,self.request)
    def test_unprivileged_install_never_attempts_elevation(self):
        with patch.object(control,'can_install',return_value=False), patch.object(control.subprocess,'Popen') as child:
            self.assertEqual(control.run_install('.',self.tmp.name,mesh.save_json)[0],'NEEDS_ADMIN')
            child.assert_not_called()

    def test_machine_update_worker_does_not_claim_user_git_jobs(self):
        stopping=threading.Event();requests=[]
        class Client:
            def request(self,path,data=None):
                requests.append(path);stopping.set()
                return {'commands':[{'id':'a'*24,'action':'sync','expires_at':time.time()+600}]}
        with patch.object(control,'run_install') as install:
            control.worker(Client(),self.tmp.name,stopping,None,None,install,mesh.read_json,mesh.save_json,mesh.LOG,allowed_actions={'refresh','install'})
            install.assert_not_called()
        self.assertEqual(requests,['/commands'])
        self.assertEqual(mesh.read_json(Path(self.tmp.name)/'executed-commands.json'),{})

    def test_install_rescans_and_removes_completed_pending_packages(self):
        stopping=threading.Event()
        job=self.queue.enqueue('operator','a','install',self.request)
        local={'status':'OK','count':1,'packages':['completed-package'],'checked_at':1}
        calls=[]
        queue=self.queue
        class Client:
            def request(self,path,data=None):
                if path=='/commands': return {'commands':queue.pending('a')}
                if path=='/command-result':
                    result=queue.result('a',data['id'],data['status'],data.get('detail',''))
                    if data['status']=='SUCCEEDED': stopping.set()
                    return result
                raise AssertionError(path)
        def install():
            calls.append('install')
            return 'SUCCEEDED','native installer exit 0'
        def refresh():
            calls.append('fresh-scan')
            local.update(count=0,packages=[],checked_at=2)
            mesh.save_json(Path(self.tmp.name)/'local.json',{'updates':local})
            return local
        control.worker(Client(),self.tmp.name,stopping,refresh,None,install,mesh.read_json,mesh.save_json,mesh.LOG)
        self.assertEqual(calls,['install','fresh-scan'])
        self.assertEqual(queue.pending('a'),[])
        self.assertEqual(queue.snapshot()[0]['status'],'SUCCEEDED')
        updates=mesh.read_json(Path(self.tmp.name)/'local.json')['updates']
        self.assertEqual(updates['count'],0)
        self.assertEqual(updates['packages'],[])


@unittest.skipUnless(shutil.which('openssl'),'native TLS fixture requires OpenSSL')
class HttpControl(unittest.TestCase):
    def test_https_roles_and_invalid_body(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); cert=root/'cert.pem'; key=root/'key.pem'
            config=root/'openssl-test.cnf'
            config.write_text('[req]\ndistinguished_name=dn\n[dn]\n')
            subprocess.run(['openssl','req','-config',str(config),'-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=IP:127.0.0.1','-keyout',str(key),'-out',str(cert)],check=True,capture_output=True)
            server=mesh.start_hub({'bind':'127.0.0.1','port':0,'certificate':str(cert),'private_key':str(key),'read_token':'reader','operator_token':'operator','members':[{'id':'a','name':'A','token':'host','allow_install':True}]},root)
            def client(token): return mesh.Client({'hubs':['https://127.0.0.1:'+str(server.server_port)],'token':token,'certificate':str(cert)})
            idle=socket.create_connection(('127.0.0.1',server.server_port),timeout=2)
            try:
                with self.assertRaisesRegex(RuntimeError,'401'): client('reader').request('/control',{'target':'a','action':'refresh','request_id':'a'*24})
                with self.assertRaisesRegex(RuntimeError,'403'): client('operator').request('/commands')
                with self.assertRaisesRegex(RuntimeError,'400'): client('host').request('/report',[])
                job=client('operator').request('/control',{'target':'a','action':'refresh','request_id':'a'*24})
                self.assertEqual(client('host').request('/commands')['commands'][0]['id'],job['id'])
                client('host').request('/command-result',{'id':job['id'],'status':'RUNNING'})
                self.assertEqual(client('host').request('/commands')['commands'],[])
                client('host').request('/command-result',{'id':job['id'],'status':'SUCCEEDED'})
                self.assertEqual(client('reader').request('/fleet')['commands'][0]['status'],'SUCCEEDED')
            finally:
                idle.close()
                server.shutdown(); server.server_close()


if __name__=='__main__': unittest.main()
