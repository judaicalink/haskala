"""
Unit tests for haskala_rdf/push.py.

These tests mock requests rather than reaching the real Fuseki — the
goal is to nail the exact HTTP shape (URL, params, headers, body) the
push helper produces. An integration test against a live Fuseki would
belong somewhere else (CI service container or a dedicated suite).
"""
from unittest.mock import patch

from django.test import TestCase
from rdflib import Graph, URIRef, Literal

from haskala_rdf.push import PushTarget, push_graph, target_from_settings


def _sample_graph():
    g = Graph()
    g.add((URIRef("http://example.org/s"),
           URIRef("http://example.org/p"),
           Literal("hello")))
    return g


class PushGraphTest(TestCase):
    """The two protocols call different HTTP verbs and content types."""

    def test_gsp_uses_put_with_turtle_body(self):
        target = PushTarget(
            url="http://fuseki.example/data",
            graph_iri="http://example.org/g",
            protocol="gsp",
        )
        with patch("haskala_rdf.push.requests") as mock_requests:
            mock_requests.put.return_value.status_code = 204
            mock_requests.put.return_value.raise_for_status.return_value = None
            push_graph(_sample_graph(), target)

        mock_requests.put.assert_called_once()
        _args, kwargs = mock_requests.put.call_args
        self.assertEqual(kwargs["params"], {"graph": "http://example.org/g"})
        self.assertEqual(
            kwargs["headers"]["Content-Type"],
            "text/turtle; charset=utf-8",
        )
        self.assertIn(b"hello", kwargs["data"])

    def test_update_routes_through_djangordf_fuseki_backend(self):
        """The 'update' protocol delegates to djangordf's FusekiBackend
        so SPARQL writes flow through the JudaicaLink-internal RDF
        layer instead of plain requests.post()."""
        target = PushTarget(
            url="http://fuseki.example/update",
            graph_iri="http://example.org/g",
            protocol="update",
        )
        with patch("djangordf.backends.fuseki.FusekiBackend") as MockBackend:
            instance = MockBackend.return_value
            instance.update.return_value = None
            push_graph(_sample_graph(), target)

        # FusekiBackend was instantiated with the dataset root (the
        # /update suffix is stripped before handing it over).
        MockBackend.assert_called_once()
        kwargs = MockBackend.call_args.kwargs
        self.assertEqual(kwargs["endpoint"], "http://fuseki.example")

        # The backend's update() was called once with a single SPARQL
        # transaction wrapping DROP + INSERT DATA on the target graph.
        instance.update.assert_called_once()
        sparql = instance.update.call_args.args[0]
        self.assertIn("DROP SILENT GRAPH <http://example.org/g>", sparql)
        self.assertIn("INSERT DATA", sparql)
        # N-Triples-encoded triple from the sample graph.
        self.assertIn("<http://example.org/s>", sparql)

    def test_basic_auth_threaded_through(self):
        target = PushTarget(
            url="http://fuseki.example/data",
            graph_iri="http://example.org/g",
            protocol="gsp",
            auth=("admin", "secret"),
        )
        with patch("haskala_rdf.push.requests") as mock_requests:
            mock_requests.put.return_value.raise_for_status.return_value = None
            push_graph(_sample_graph(), target)
        _args, kwargs = mock_requests.put.call_args
        self.assertEqual(kwargs["auth"], ("admin", "secret"))

    def test_unknown_protocol_raises(self):
        target = PushTarget(
            url="http://fuseki.example/data",
            graph_iri="http://example.org/g",
            protocol="ftp",
        )
        with self.assertRaises(ValueError):
            push_graph(_sample_graph(), target)


class TargetFromSettingsTest(TestCase):
    def test_disabled_when_url_empty(self):
        class Cfg:
            HASKALA_SPARQL_PUSH_URL = ""
        self.assertIsNone(target_from_settings(Cfg))

    def test_basic_auth_picked_up(self):
        class Cfg:
            HASKALA_SPARQL_PUSH_URL = "http://fuseki/data"
            HASKALA_SPARQL_PUSH_GRAPH = "http://g/"
            HASKALA_SPARQL_PUSH_PROTOCOL = "gsp"
            HASKALA_SPARQL_PUSH_USER = "alice"
            HASKALA_SPARQL_PUSH_PASSWORD = "bob"
            HASKALA_SPARQL_PUSH_TIMEOUT = 30
        target = target_from_settings(Cfg)
        self.assertEqual(target.url, "http://fuseki/data")
        self.assertEqual(target.graph_iri, "http://g/")
        self.assertEqual(target.protocol, "gsp")
        self.assertEqual(target.auth, ("alice", "bob"))
        self.assertEqual(target.timeout_seconds, 30)

    def test_no_auth_when_user_blank(self):
        class Cfg:
            HASKALA_SPARQL_PUSH_URL = "http://fuseki/data"
            HASKALA_SPARQL_PUSH_USER = ""
            HASKALA_SPARQL_PUSH_PASSWORD = ""
        target = target_from_settings(Cfg)
        self.assertIsNone(target.auth)
