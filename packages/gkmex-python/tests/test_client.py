import unittest
import urllib.error
import urllib.parse
from unittest.mock import MagicMock, patch

from gkmex import GkmexClient, GkmexError
from tests.helpers import send_bytes, send_json, serve


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


if __name__ == "__main__":
    unittest.main()
