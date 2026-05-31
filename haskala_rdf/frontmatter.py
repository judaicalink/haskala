"""
Re-export of build_frontmatter_md from export.py.

The export.py module hosts the implementation because it shares the
date/identifier defaults with the metagraph. The command imports it
from this short alias module to keep the import lines symmetric with
the beacon module.
"""
from .export import build_frontmatter_md

__all__ = ["build_frontmatter_md"]
