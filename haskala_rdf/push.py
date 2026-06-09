"""
Push a built RDF graph to a remote SPARQL endpoint.

Two protocols are supported:

- **Graph Store Protocol (GSP)** — the default. Uploads the serialized
  Turtle as the entire content of one named graph via HTTP PUT. Fuseki
  exposes this at ``/<dataset>/data``. djangordf's FusekiBackend does
  not cover GSP itself, so this path stays on plain ``requests.put``.
- **SPARQL 1.1 Update** — routes through
  :class:`djangordf.backends.fuseki.FusekiBackend`. We send one
  ``DROP SILENT GRAPH …; INSERT DATA { GRAPH … { … } }`` transaction
  that the backend posts to ``/<dataset>/update``.

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


def push_graph(graph: Graph, target: PushTarget):
    """
    Push *graph* to *target.url*. Returns either a ``requests.Response``
    (gsp path) or ``None`` (update path — djangordf's backend has no
    response object to surface).

    Raises ``requests.HTTPError`` on a 4xx/5xx response so callers can
    fail loudly.
    """
    if target.protocol == "gsp":
        body = graph.serialize(format="turtle")
        if isinstance(body, str):
            body = body.encode("utf-8")
        response = requests.put(
            target.url,
            params={"graph": target.graph_iri},
            data=body,
            headers={"Content-Type": "text/turtle; charset=utf-8"},
            auth=target.auth,
            timeout=target.timeout_seconds,
        )
        response.raise_for_status()
        return response

    if target.protocol == "update":
        # Route through djangordf's FusekiBackend so the same library
        # handles SPARQL writes everywhere in the JudaicaLink stack.
        # We pass the dataset root (stripping a /update / /data tail
        # if the caller pre-attached one).
        from djangordf.backends.fuseki import FusekiBackend

        endpoint = target.url
        for suffix in ("/update", "/data", "/query"):
            if endpoint.endswith(suffix):
                endpoint = endpoint[: -len(suffix)]
                break
        backend_kwargs: dict = {"endpoint": endpoint}
        if target.auth is not None:
            backend_kwargs["user"], backend_kwargs["password"] = target.auth
        backend = FusekiBackend(**backend_kwargs)

        # Serialize the graph to N-Triples and wrap in a single SPARQL
        # transaction. djangordf's backend.update() POSTs the body to
        # /<dataset>/update with the right content-type.
        nt = graph.serialize(format="nt")
        if isinstance(nt, bytes):
            nt = nt.decode("utf-8")
        sparql = (
            f"DROP SILENT GRAPH <{target.graph_iri}> ;\n"
            f"INSERT DATA {{ GRAPH <{target.graph_iri}> {{\n"
            f"{nt}\n"
            f"}} }}"
        )
        backend.update(sparql)
        return None

    raise ValueError(
        f"Unsupported push protocol: {target.protocol!r} "
        f"(expected 'gsp' or 'update')"
    )


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
