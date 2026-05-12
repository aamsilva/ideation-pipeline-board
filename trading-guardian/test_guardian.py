import subprocess
import unittest
import os
import json

# Define paths
HERMES_HOME = os.path.expanduser("~/.hermes")
TRADING_GUARDIAN_PATH = "/Volumes/disco1tb/projects/trading-guardian"
AUTO_RESEARCH_PATH = os.path.join(HERMES_HOME, "scripts", "auto_research.py")


class TestHermesAndTradingGuardian(unittest.TestCase):

    def test_hermes_gateway_running(self):
        # Check if hermes gateway is running using ps aux
        process = subprocess.Popen(["ps", "aux"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        hermes_process_running = any([b"hermes_cli.main gateway run" in line for line in stdout.splitlines()])
        self.assertTrue(hermes_process_running, "Hermes gateway is not running")

    def test_trading_guardian_daemon_running(self):
        # Check if trading guardian daemon is running using ps aux
        process = subprocess.Popen(["ps", "aux"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        guardian_daemon_running = any([b"guardian_daemon.py" in line for line in stdout.splitlines()])
        self.assertTrue(guardian_daemon_running, "Trading guardian daemon is not running")

    def test_auto_research_can_be_started(self):
        # Test that auto research experiments can be started and checked for status
        command = ["python3", AUTO_RESEARCH_PATH, "start", "skill_improvement", "test_skill", "1"]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        try:
            data = json.loads(stdout.decode("utf-8"))
            exp_id = data.get("exp_id")
            self.assertIsNotNone(exp_id, "Experiment ID not found")
            # Check status
            command = ["python3", AUTO_RESEARCH_PATH, "status", exp_id]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            status_data = json.loads(stdout.decode("utf-8"))
            self.assertEqual(status_data.get("status"), "running", "Experiment status is not Running")

        except Exception as e:
            self.fail(f"Failed to start or check auto research {e}\n{stderr.decode('utf-8')}")

if __name__ == '__main__':
    unittest.main()