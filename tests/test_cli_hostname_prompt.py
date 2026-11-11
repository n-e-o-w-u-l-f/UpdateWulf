"""Offline acceptance for host-first remote updates and compact ANSI prompts."""
import io
import json
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import pc_mesh as mesh


class HostnamesAndPrompt(unittest.TestCase):
    def fleet(self, now=2000):
        return {
            "generated_at": now, "offline_after": 150, "stale_after": 5400,
            "nodes": [
                {"id": "alpha", "name": "ALPHA", "hostname": "ALPHA-PC",
                 "received_at": now - 180, "updates": {"count": 1, "status": "OK", "checked_at": now - 400}},
                {"id": "builder", "name": "Builder", "hostname": "builder.fritz.box",
                 "received_at": now - 4, "updates": {"count": 0, "status": "OK", "checked_at": now - 4}},
                {"id": "pi", "name": "Gateway", "hostname": "gateway",
                 "received_at": now - 2, "updates": {"count": 0, "status": "OK", "checked_at": now - 2}},
                {"id": "hp", "name": "RemoteStation", "hostname": "station-node.fritz.box",
                 "received_at": now - 1, "updates": {"count": 26, "status": "OK", "checked_at": now - 1}},
                {"id": "spin", "name": "HubServer", "enrolled_hostname": "hubserver",
                 "received_at": now - 3, "updates": {"count": 1, "status": "OK", "checked_at": now - 3}},
            ],
        }

    def test_action_first_and_host_first(self):
        for order in [("update", "alpha-pc.local"), ("alpha-pc.local", "update")]:
            self.assertEqual(mesh.parse_operator_order(*order), ("update", "alpha-pc.local"))
        self.assertEqual(mesh.parse_operator_order("gateway.local", "refresh"), ("refresh", "gateway.local"))
        self.assertEqual(mesh.parse_operator_order("hubserver.local", "sync"), ("sync", "hubserver.local"))

    def test_hostname_mapping_cannot_be_confused_with_friendly_name(self):
        fleet = self.fleet()
        for name, expected in [
            ("ALPHA-PC.local", ["alpha"]), ("builder.local", ["builder"]),
            ("gateway.local", ["pi"]), ("station-node.local", ["hp"]),
            ("hubserver.local", ["spin"]), ("alpha", ["alpha"]),
        ]:
            self.assertEqual(mesh.resolve_fleet_targets(fleet, name), expected)
        for invalid in ["ALPHA.local", "RemoteStation.local", "other.local", "x;reboot", ""]:
            with self.assertRaises(ValueError, msg=invalid):
                mesh.resolve_fleet_targets(fleet, invalid)
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            fleet["nodes"].append({"id": "duplicate", "hostname": "builder"})
            mesh.resolve_fleet_targets(fleet, "builder.local")

    def test_freshness_hub_stale_is_not_equivalent_to_offline(self):
        fleet = self.fleet()
        alpha = fleet["nodes"][0]
        self.assertEqual(mesh.prompt_node_status(alpha, fleet, 2000), ("1 Update(s)", "off"))
        self.assertEqual(mesh.prompt_node_status(alpha, fleet, 4000), ("1 Update(s)", "stale"))
        alpha["received_at"] = 1999
        alpha["updates"]["status"] = "ERROR"
        self.assertEqual(mesh.prompt_node_status(alpha, fleet, 2000)[1], "err")
        fleet["generated_at"] = 1990
        alpha["received_at"] = 0
        self.assertEqual(mesh.prompt_node_status(alpha, fleet, 2000)[1], "?")

    def test_one_line_style_and_color_scopes(self):
        fleet = self.fleet()
        ansi = mesh.fleet_preprompt(fleet, now=2000, width=300, color=True)
        plain = re.sub(r"\x1b\[[0-9;]*m", "", ansi)
        self.assertEqual(plain.count("\n"), 0)
        self.assertTrue(plain.startswith("[ UpdateWulf ::: "))
        self.assertTrue(plain.endswith(" ]"))
        self.assertIn("ALPHA-PC 1 Update(s) [off]", plain)
        self.assertNotIn("gateway 0 Update(s)", plain)
        self.assertIn("+2", plain)
        self.assertNotIn(".local", plain)
        self.assertIn("\x1b[1;38;5;255mALPHA-PC\x1b[0m 1 Update(s)", ansi)
        self.assertEqual(mesh.fleet_preprompt(fleet, now=2000, width=300, color=False), plain)
        self.assertIn("\x1b[1;38;5;85mUpdateWulf\x1b[0m", ansi)
        self.assertIn("\x1b[38;5;39m:::\x1b[0m", ansi)
        self.assertIn("[\x1b[38;5;196moff\x1b[0m]", ansi)
        self.assertNotIn("\x1b[38;5;196m[", ansi)
        self.assertNotIn("\x1b[38;5;196m]", ansi)
        safe = mesh.bash_safe_prompt(ansi)
        self.assertIn(r"\[", safe)
        self.assertIn(r"\]", safe)

    def test_zero_devices_are_counted_separately_from_truncated_devices(self):
        fleet=self.fleet()
        full=mesh.fleet_preprompt(fleet,now=2000,width=1000,color=False)
        self.assertIn('+2',full)
        self.assertNotIn('gateway',full)
        short=mesh.fleet_preprompt(fleet,now=2000,width=80,color=False)
        self.assertTrue(short.endswith('... ]'))
        self.assertIn('+2',short)
        self.assertLessEqual(len(short),80)
        for node in fleet['nodes']:
            node['updates']['count']=0
        fleet['nodes'][0]['updates']['status']='ERROR'
        visible=mesh.fleet_preprompt(fleet,now=2000,width=1000,color=False)
        self.assertIn('ALPHA-PC',visible)
        self.assertIn('+4',visible)

    def test_narrow_prompt_never_wraps_or_breaks_hostname(self):
        for width in [22, 28, 40, 55, 80, 120]:
            rendered = mesh.fleet_preprompt(self.fleet(), now=2000, width=width, color=True)
            stripped = re.sub(r"\x1b\[[0-9;]*m", "", rendered)
            self.assertLessEqual(len(stripped), width)
            self.assertNotIn("\n", stripped)
            self.assertTrue(stripped.endswith(" ]"))

    def test_authenticated_hub_carries_actual_reported_hostname(self):
        with tempfile.TemporaryDirectory() as d:
            hub = mesh.Hub({"members": [{"id": "alpha", "name": "ALPHA"}]}, d)
            hub.report("alpha", {"hostname": "ALPHA-PC.fritz.box",
                                "updates": {"status": "OK", "count": 1,
                                            "checked_at": time.time(), "packages": []}})
            self.assertEqual(hub.snapshot()["nodes"][0]["hostname"], "ALPHA-PC")
            with self.assertRaises(ValueError):
                hub.report("rogue", {"hostname": "ALPHA-PC", "updates": {"status": "OK", "count": 0,
                                   "checked_at": time.time(), "packages": []}})

    def test_real_cli_dispatches_host_first_to_same_authorized_hub(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            config = base / "config.json"
            config.write_text(json.dumps({"id": "operator", "token": "fixture"}))
            fleet = self.fleet(now=time.time())
            calls = []
            class StubClient:
                def __init__(self, config):
                    self.config = config
                def request(self, path, data=None, timeout=10):
                    calls.append((path, data))
                    if path == "/fleet":
                        return fleet
                    if path == "/control":
                        return {"target": data["target"], "action": data["action"],
                                "status": "QUEUED", "id": "a" * 24}
                    raise AssertionError(path)
            argv = ["pc_mesh.py", "ALPHA-PC.local", "update", "--config", str(config),
                    "--state", str(base), "--wait", "0"]
            with patch.object(mesh, "Client", StubClient), patch.object(sys, "argv", argv):
                with patch("sys.stdout", new_callable=io.StringIO) as output:
                    self.assertEqual(mesh.main(), 0)
            self.assertEqual(calls[1][0], "/control")
            self.assertEqual(calls[1][1]["target"], "alpha")
            self.assertEqual(calls[1][1]["action"], "install")
            self.assertIn("QUEUED", output.getvalue())
            self.assertNotIn("SUCCEEDED", output.getvalue())


    def test_update_waits_by_default_and_reports_admin_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config = base / "config.json"
            config.write_text('{"id":"operator"}')
            fleet = self.fleet(now=time.time())
            job = {"id": "a" * 24, "target": "alpha", "action": "install", "status": "QUEUED"}
            class StubClient:
                def __init__(self, config):
                    self.sent = False
                def request(self, path, data=None):
                    if path == "/control":
                        self.sent = True
                        return job
                    if path == "/fleet":
                        if self.sent:
                            return dict(fleet, commands=[dict(job, status="NEEDS_ADMIN", detail="native administrator required")])
                        return fleet
                    raise AssertionError(path)
            argv = ["pc_mesh.py", "alpha", "update", "--config", str(config), "--state", str(base)]
            with patch.object(mesh, "Client", StubClient), patch.object(sys, "argv", argv):
                with patch("sys.stdout", new_callable=io.StringIO) as output:
                    self.assertEqual(mesh.main(), 1)
            self.assertIn("NEEDS_ADMIN", output.getvalue())
            self.assertNotIn("QUEUED", output.getvalue())

if __name__ == "__main__":
    unittest.main()
