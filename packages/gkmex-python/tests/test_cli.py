import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from tests.helpers import read_body, send_json, serve


ROOT = Path(__file__).resolve().parents[1]


def cli_environment(base_url=None):
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    if base_url is not None:
        environment["GKMEX_BASE_URL"] = base_url
    else:
        environment.pop("GKMEX_BASE_URL", None)
    return environment


def run_cli(*args, base_url=None):
    return subprocess.run(
        [sys.executable, "-m", "gkmex.cli", *args],
        cwd=ROOT,
        env=cli_environment(base_url),
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )


class CliTests(unittest.TestCase):
    def test_list_prints_indented_json_and_forwards_filters(self):
        expected = {"count": 1, "data": [{"id": "crane-1"}]}

        def route(handler, requests):
            requests.append(handler.path)
            send_json(handler, 200, expected)

        with serve(route) as (base_url, requests):
            result = run_cli(
                "list",
                "--brand",
                "Liebherr",
                "--type",
                "mobile",
                "--limit",
                "5",
                base_url=base_url,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), expected)
        self.assertTrue(result.stdout.endswith("\n"))
        self.assertIn("\n  \"count\"", result.stdout)
        self.assertEqual(result.stderr, "")
        self.assertEqual(
            requests,
            ["/api/v1/cranes?brand=Liebherr&type=mobile&limit=5"],
        )

    def test_get_prints_one_public_crane(self):
        expected = {
            "id": "crane-1",
            "price_eur": None,
            "url": "https://gkmex.com/en/crane/crane-1",
        }

        def route(handler, requests):
            requests.append(handler.path)
            send_json(handler, 200, expected)

        with serve(route) as (base_url, requests):
            result = run_cli("get", "crane-1", base_url=base_url)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), expected)
        self.assertEqual(result.stderr, "")
        self.assertEqual(requests, ["/api/v1/cranes/crane-1"])

    def test_compare_prints_the_mcp_structured_content(self):
        expected = {
            "count": 2,
            "data": [{"id": "crane-1"}, {"id": "crane-2"}],
        }

        def route(handler, requests):
            requests.append(json.loads(read_body(handler)))
            send_json(
                handler,
                200,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {
                        "isError": False,
                        "structuredContent": expected,
                    },
                },
            )

        with serve(route) as (base_url, requests):
            result = run_cli(
                "compare",
                "crane-1",
                "crane-2",
                base_url=base_url,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), expected)
        self.assertEqual(result.stderr, "")
        self.assertEqual(
            requests[0]["params"]["arguments"]["ids"],
            ["crane-1", "crane-2"],
        )

    def test_help_and_version_succeed_without_network_access(self):
        help_result = run_cli("--help", base_url="http://127.0.0.1:1")
        version_result = run_cli("--version", base_url="http://127.0.0.1:1")

        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("usage: gkmex", help_result.stdout)
        self.assertEqual(help_result.stderr, "")
        self.assertEqual(version_result.returncode, 0, version_result.stderr)
        self.assertEqual(version_result.stdout, "gkmex 1.0.0\n")
        self.assertEqual(version_result.stderr, "")

    def test_invalid_usage_exits_two_before_network_access(self):
        invalid_commands = (
            (),
            ("unknown",),
            ("list", "--type", "tower"),
            ("list", "--limit", "0"),
            ("list", "--limit", "101"),
            ("list", "--offset", "-1"),
            ("list", "--offset", "0", "--cursor", "next"),
            ("list", "--brand", ""),
            ("list", "--cursor", ""),
            ("get", " crane-1"),
            ("get", "."),
            ("compare", "one"),
            ("compare", "one", "one"),
            ("compare", "1", "2", "3", "4", "5", "6"),
        )

        for command in invalid_commands:
            with self.subTest(command=command):
                result = run_cli(*command, base_url="http://127.0.0.1:1")
                self.assertEqual(result.returncode, 2, result)
                self.assertEqual(result.stdout, "")
                self.assertIn("usage:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_api_failures_print_one_stable_line_and_exit_one(self):
        def route(handler, requests):
            send_json(handler, 404, {"error": "Crane not found"})

        with serve(route) as (base_url, _):
            result = run_cli("get", "missing", base_url=base_url)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "gkmex: Crane not found\n")
        self.assertNotIn("Traceback", result.stderr)

    def test_network_failures_print_one_stable_line_and_exit_one(self):
        result = run_cli(
            "list",
            "--limit",
            "1",
            base_url="http://127.0.0.1:1",
        )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "gkmex: Unable to reach Gkmex\n")
        self.assertNotIn("Traceback", result.stderr)

    def test_closed_stdout_pipeline_exits_quietly(self):
        expected = {
            "count": 5000,
            "data": [{"id": f"crane-{index}"} for index in range(5000)],
        }

        def route(handler, requests):
            send_json(handler, 200, expected)

        with serve(route) as (base_url, _):
            process = subprocess.Popen(
                [sys.executable, "-m", "gkmex.cli", "list"],
                cwd=ROOT,
                env=cli_environment(base_url),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertIsNotNone(process.stdout)
            self.assertIsNotNone(process.stderr)
            process.stdout.close()
            stderr = process.stderr.read()
            process.stderr.close()
            returncode = process.wait(timeout=10)

        self.assertEqual(returncode, 0, stderr)
        self.assertEqual(stderr, "")


if __name__ == "__main__":
    unittest.main()
