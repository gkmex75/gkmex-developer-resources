import unittest
import urllib.parse
from unittest.mock import MagicMock, patch

from gkmex import GkmexClient, GkmexError
from tests.helpers import send_json, serve


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


if __name__ == "__main__":
    unittest.main()
