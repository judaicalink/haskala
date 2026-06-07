"""
Push a built RDF graph to a remote SPARQL endpoint.

Two protocols are supported:

- **Graph Store Protocol (GSP)** — the default. Uploads the serialized
  Turtle as the entire content of one named graph via HTTP PUT. Fuseki
  exposes this at ``/<dataset>/data``.
- **SPARQL 1.1 Update** — falls back to inline ``DROP SILENT GRAPH …;
  INSERT DATA { GRAPH … { … } }`` over HTTP POST when ``protocol="update"``.
  Fuseki's update endpoint is ``/<dataset>/update``.

Both paths replace the named graph wholesale; calling the push twice
produces the same end state.
"""
from __future__ import annotations

from dataclasses import dataclass

import requests
from rdflib import Graph


@dataclass(frozen=True)
class PushTarget:
    url: str
    graph_iri: str
    protocol: str = "gsp"
    auth: tuple[str, str] | None = None
    timeout_seconds: int = 60


def push_graph(graph: Graph, target: PushTarget) -> requests.Response:
    """
    Push *graph* to *target.url*. Returns the underlying HTTP Response.

    Raises ``requests.HTTPError`` on a 4xx/5xx response so callers can
    fail loudly. Otherwise the caller gets the response object back
    and can inspect status / headers.
    """
    body = graph.serialize(format="turtle")
    if isinstance(body, str):
        body = body.encode("utf-8")

    if target.protocol == "gsp":
        response = requests.put(
            target.url,
            params={"graph": target.graph_iri},
            data=body,
            headers={"Content-Type": "text/turtle; charset=utf-8"},
            auth=target.auth,
            timeout=target.timeout_seconds,
        )
    elif target.protocol == "update":
        # Strip the @prefix and @base lines out of the Turtle and wrap
        # the rest in a SPARQL UPDATE block. rdflib's `application/
        # sparql-update` is easier to construct from N-Triples than
        # from Turtle because UPDATE statements use SPARQL syntax for
        # prefixes — keep things simple and ship the triples raw.
        nt = graph.serialize(format="nt")
        if isinstance(nt, str):
            nt = nt.encode("utf-8")
        update = (
            f"DROP SILENT GRAPH <{target.graph_iri}> ;\n"
            f"INSERT DATA {{ GRAPH <{target.graph_iri}> {{\n"
        ).encode("utf-8") + nt + b"\n} }"
        response = requests.post(
            target.url,
            data=update,
            headers={"Content-Type": "application/sparql-update; charset=utf-8"},
            auth=target.auth,
            timeout=target.timeout_seconds,
        )
    else:
        raise ValueError(
            f"Unsupported push protocol: {target.protocol!r} "
            f"(expected 'gsp' or 'update')"
        )

    response.raise_for_status()
    return response


def target_from_settings(settings_module) -> PushTarget | None:
    """
    Build a PushTarget from the Django settings module. Returns None
    when the push is disabled (HASKALA_SPARQL_PUSH_URL is empty), so
    callers can `if t := target_from_settings(settings)` cleanly.
    """
    url = getattr(settings_module, "HASKALA_SPARQL_PUSH_URL", "") or ""
    if not url:
        return None
    graph_iri = (
        getattr(settings_module, "HASKALA_SPARQL_PUSH_GRAPH", "")
        or "http://data.judaicalink.org/data/haskala"
    )
    protocol = getattr(settings_module, "HASKALA_SPARQL_PUSH_PROTOCOL", "gsp")
    user = getattr(settings_module, "HASKALA_SPARQL_PUSH_USER", "") or ""
    password = getattr(settings_module, "HASKALA_SPARQL_PUSH_PASSWORD", "") or ""
    auth = (user, password) if user else None
    timeout = int(getattr(settings_module, "HASKALA_SPARQL_PUSH_TIMEOUT", 60))
    return PushTarget(
        url=url,
        graph_iri=graph_iri,
        protocol=protocol,
        auth=auth,
        timeout_seconds=timeout,
    )
