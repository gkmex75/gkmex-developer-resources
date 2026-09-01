import json
import unittest
import urllib.error
import urllib.parse
from unittest.mock import MagicMock, patch

from gkmex import GkmexClient, GkmexError
from tests.helpers import read_body, send_bytes, send_json, send_sse, serve


class ClientTests(unittest.TestCase):
    def test_list_cranes_maps_only_supported_non_none_filters(self):
        expected = {
            "count": 1,
            "data": [{"id": "crane-1", "price_eur": 120000}],
        }

        def route(handler, requests):
            requests.append((handler.command, handler.path, handler.headers))
            send_json(handler, 200, expected)

        with serve(route) as (base_url, requests):
            result = GkmexClient(base_url).list_cranes(
                brand="Liebherr", type="mobile", limit=2, offset=1
            )

        method, target, headers = requests[0]
        parsed = urllib.parse.urlsplit(target)
        self.assertEqual(method, "GET")
        self.assertEqual(parsed.path, "/api/v1/cranes")
        self.assertEqual(
            urllib.parse.parse_qs(parsed.query),
            {
                "brand": ["Liebherr"],
                "type": ["mobile"],
                "limit": ["2"],
                "offset": ["1"],
            },
        )
        self.assertEqual(headers["Accept"], "application/json")
        self.assertEqual(result, expected)

    def test_get_crane_percent_encodes_the_id_and_preserves_poa(self):
        expected = {
            "id": "id/with space",
            "price_eur": None,
            "url": "https://gkmex.com/en/crane/id%2Fwith%20space",
        }

        def route(handler, requests):
            requests.append(handler.path)
            send_json(handler, 200, expected)

        with serve(route) as (base_url, requests):
            result = GkmexClient(base_url).get_crane("id/with space")

        self.assertEqual(requests, ["/api/v1/cranes/id%2Fwith%20space"])
        self.assertIsNone(result["price_eur"])
        self.assertEqual(result, expected)

    def test_base_url_path_and_timeout_apply_to_every_request(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'{"count":0,"data":[]}'
        response.headers = {"Content-Type": "application/json"}

        with patch(
            "gkmex.client.urllib.request.urlopen", return_value=response
        ) as open_url:
            result = GkmexClient(
                "https://example.test/prefix", timeout=7
            ).list_cranes()

        request = open_url.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://example.test/prefix/api/v1/cranes",
        )
        self.assertEqual(request.get_header("User-agent"), "gkmex-python/1.0.0")
        self.assertEqual(open_url.call_args.kwargs["timeout"], 7)
        self.assertEqual(result, {"count": 0, "data": []})

    def test_get_crane_rejects_non_canonical_ids_without_network_access(self):
        invalid_ids = (None, "", " ", " crane-1", "crane-1 ", ".", "..")

        with patch("gkmex.client.urllib.request.urlopen") as open_url:
            for value in invalid_ids:
                with self.subTest(value=value):
                    with self.assertRaisesRegex(
                        GkmexError,
                        "id must be a canonical public crane ID",
                    ):
                        GkmexClient().get_crane(value)

        open_url.assert_not_called()

    def test_list_cranes_rejects_invalid_filters_without_network_access(self):
        invalid_options = (
            {"limit": True},
            {"limit": 0},
            {"limit": -1},
            {"limit": 101},
            {"limit": "1"},
            {"offset": True},
            {"offset": -1},
            {"offset": "0"},
            {"type": "tower"},
            {"brand": 1},
            {"brand": ""},
            {"brand": " Liebherr"},
            {"brand": "Liebherr "},
            {"cursor": 1},
            {"cursor": ""},
            {"cursor": " next"},
            {"cursor": "next "},
            {"offset": 0, "cursor": "next"},
        )

        with patch("gkmex.client.urllib.request.urlopen") as open_url:
            for options in invalid_options:
                with self.subTest(options=options):
                    with self.assertRaises(GkmexError):
                        GkmexClient().list_cranes(**options)

        open_url.assert_not_called()

    def test_json_http_errors_preserve_status_and_public_details(self):
        def route(handler, requests):
            send_json(handler, 404, {"error": "Crane not found"})

        with serve(route) as (base_url, _):
            with self.assertRaises(GkmexError) as raised:
                GkmexClient(base_url).get_crane("missing")

        self.assertEqual(str(raised.exception), "Crane not found")
        self.assertEqual(raised.exception.status, 404)
        self.assertIsNone(raised.exception.code)
        self.assertEqual(
            raised.exception.details,
            {"error": "Crane not found"},
        )
        self.assertIsInstance(raised.exception.__cause__, urllib.error.HTTPError)

    def test_non_json_http_errors_use_a_stable_message(self):
        def route(handler, requests):
            send_bytes(
                handler,
                500,
                "text/html; charset=utf-8",
                b"<h1>internal detail</h1>",
            )

        with serve(route) as (base_url, _):
            with self.assertRaises(GkmexError) as raised:
                GkmexClient(base_url).list_cranes()

        self.assertEqual(
            str(raised.exception),
            "Gkmex request failed with HTTP 500",
        )
        self.assertEqual(raised.exception.status, 500)
        self.assertIsNone(raised.exception.details)
        self.assertNotIn("internal detail", str(raised.exception))

    def test_success_with_unsupported_media_type_is_rejected(self):
        def route(handler, requests):
            send_bytes(handler, 200, "text/plain", b'{}')

        with serve(route) as (base_url, _):
            with self.assertRaisesRegex(
                GkmexError,
                "Gkmex returned an unsupported media type",
            ):
                GkmexClient(base_url).list_cranes()

    def test_malformed_success_json_is_chained(self):
        for payload in (b"{", b"\xff"):
            with self.subTest(payload=payload):
                def route(handler, requests):
                    send_bytes(handler, 200, "application/json", payload)

                with serve(route) as (base_url, _):
                    with self.assertRaisesRegex(
                        GkmexError,
                        "Gkmex returned invalid JSON",
                    ) as raised:
                        GkmexClient(base_url).list_cranes()

                self.assertIsNotNone(raised.exception.__cause__)

    def test_network_failures_are_stable_and_chained(self):
        failures = (
            urllib.error.URLError("offline"),
            TimeoutError("timed out"),
            OSError("socket closed"),
        )

        for failure in failures:
            with self.subTest(failure=failure):
                with patch(
                    "gkmex.client.urllib.request.urlopen",
                    side_effect=failure,
                ):
                    with self.assertRaisesRegex(
                        GkmexError,
                        "Unable to reach Gkmex",
                    ) as raised:
                        GkmexClient().list_cranes()

                self.assertIs(raised.exception.__cause__, failure)

    def test_compare_cranes_posts_the_authoritative_mcp_request(self):
        comparison = {
            "count": 2,
            "data": [{"id": "crane-1"}, {"id": "crane-2"}],
        }

        def route(handler, requests):
            requests.append(
                {
                    "method": handler.command,
                    "path": handler.path,
                    "headers": handler.headers,
                    "body": json.loads(read_body(handler)),
                }
            )
            send_json(
                handler,
                200,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {
                        "content": [{"type": "text", "text": "comparison"}],
                        "structuredContent": comparison,
                        "isError": False,
                    },
                },
            )

        with serve(route) as (base_url, requests):
            result = GkmexClient(base_url).compare_cranes(
                ["crane-1", "crane-2"]
            )

        request = requests[0]
        self.assertEqual(request["method"], "POST")
        self.assertEqual(request["path"], "/mcp")
        self.assertEqual(request["headers"]["Content-Type"], "application/json")
        self.assertEqual(
            request["headers"]["Accept"],
            "application/json, text/event-stream",
        )
        self.assertEqual(
            request["body"],
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "compare_cranes",
                    "arguments": {"ids": ["crane-1", "crane-2"]},
                },
            },
        )
        self.assertEqual(result, comparison)

    def test_compare_cranes_preserves_a_configured_base_url_path(self):
        def route(handler, requests):
            requests.append(handler.path)
            read_body(handler)
            send_json(
                handler,
                200,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {
                        "structuredContent": {"count": 2, "data": [{}, {}]},
                        "isError": False,
                    },
                },
            )

        with serve(route) as (base_url, requests):
            GkmexClient(base_url + "/prefix").compare_cranes(["one", "two"])

        self.assertEqual(requests, ["/prefix/mcp"])

    def test_compare_cranes_rejects_invalid_ids_without_network_access(self):
        invalid = (
            None,
            "one",
            [],
            ["one"],
            ["one", "one"],
            ["1", "2", "3", "4", "5", "6"],
            ["one", ""],
            ["one", " two"],
            ["one", "two "],
            ["one", "."],
            ["one", ".."],
            ["one", 2],
        )

        with patch("gkmex.client.urllib.request.urlopen") as open_url:
            for ids in invalid:
                with self.subTest(ids=ids):
                    with self.assertRaises(GkmexError):
                        GkmexClient().compare_cranes(ids)

        open_url.assert_not_called()

    def test_compare_cranes_decodes_an_sse_json_rpc_result(self):
        comparison = {
            "count": 2,
            "data": [{"id": "crane-1"}, {"id": "crane-2"}],
        }
        envelope = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "structuredContent": comparison,
                "isError": False,
            },
        }

        def route(handler, requests):
            read_body(handler)
            send_sse(
                handler,
                ": keepalive\nevent: message\ndata: "
                + json.dumps(envelope)
                + "\n\n",
            )

        with serve(route) as (base_url, _):
            result = GkmexClient(base_url).compare_cranes(
                ["crane-1", "crane-2"]
            )

        self.assertEqual(result, comparison)

    def test_compare_cranes_rejects_malformed_sse(self):
        payloads = (": keepalive\n\n", "data: {\n\n")

        for payload in payloads:
            with self.subTest(payload=payload):
                def route(handler, requests):
                    read_body(handler)
                    send_sse(handler, payload)

                with serve(route) as (base_url, _):
                    with self.assertRaisesRegex(
                        GkmexError,
                        "Gkmex returned malformed SSE",
                    ):
                        GkmexClient(base_url).compare_cranes(["one", "two"])

    def test_compare_cranes_rejects_malformed_json_rpc_envelopes(self):
        envelopes = (
            [],
            {"jsonrpc": "1.0", "id": 1, "result": {}},
            {"jsonrpc": "2.0", "id": 2, "result": {}},
            {"jsonrpc": "2.0", "id": 1},
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {},
                "error": {"code": -1, "message": "bad"},
            },
        )

        for envelope in envelopes:
            with self.subTest(envelope=envelope):
                def route(handler, requests):
                    read_body(handler)
                    send_json(handler, 200, envelope)

                with serve(route) as (base_url, _):
                    with self.assertRaisesRegex(
                        GkmexError,
                        "unexpected JSON-RPC envelope",
                    ):
                        GkmexClient(base_url).compare_cranes(["one", "two"])

    def test_compare_cranes_maps_json_rpc_errors(self):
        def route(handler, requests):
            read_body(handler)
            send_json(
                handler,
                200,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "error": {
                        "code": -32602,
                        "message": "Crane not found",
                        "data": {"ids": ["missing"]},
                    },
                },
            )

        with serve(route) as (base_url, _):
            with self.assertRaises(GkmexError) as raised:
                GkmexClient(base_url).compare_cranes(["missing", "two"])

        self.assertEqual(str(raised.exception), "Crane not found")
        self.assertEqual(raised.exception.code, -32602)
        self.assertIsNone(raised.exception.status)
        self.assertEqual(raised.exception.details, {"ids": ["missing"]})

    def test_compare_cranes_maps_mcp_tool_errors(self):
        def route(handler, requests):
            read_body(handler)
            send_json(
                handler,
                200,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {
                        "isError": True,
                        "content": [
                            {"type": "text", "text": "Cannot compare cranes"}
                        ],
                    },
                },
            )

        with serve(route) as (base_url, _):
            with self.assertRaisesRegex(
                GkmexError,
                "Cannot compare cranes",
            ) as raised:
                GkmexClient(base_url).compare_cranes(["one", "two"])

        self.assertTrue(raised.exception.details["isError"])

    def test_compare_cranes_validates_structured_content(self):
        invalid_content = (
            None,
            [],
            {},
            {"count": "2", "data": [{}, {}]},
            {"count": True, "data": [{}]},
            {"count": 2, "data": {}},
            {"count": 1, "data": [{}, {}]},
        )

        for structured_content in invalid_content:
            with self.subTest(structured_content=structured_content):
                def route(handler, requests):
                    read_body(handler)
                    send_json(
                        handler,
                        200,
                        {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "result": {
                                "isError": False,
                                "structuredContent": structured_content,
                            },
                        },
                    )

                with serve(route) as (base_url, _):
                    with self.assertRaisesRegex(
                        GkmexError,
                        "unexpected MCP result",
                    ):
                        GkmexClient(base_url).compare_cranes(["one", "two"])


if __name__ == "__main__":
    unittest.main()
