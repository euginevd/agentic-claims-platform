"""Read-only access to the insurer's data: claims, policies, customers and the two documents.

This module never reads app/claims/evals. The agents get their data only through it, so they
can't see the handlers' decisions. In production this is a database behind an API.
"""

import json
import re
from functools import cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DOCUMENTS = {"policy_wording": "policy_wording.md", "claims_manual": "claims_manual.md"}
SECTION = re.compile(r"^## (\d+)\. (.+)$", re.MULTILINE)


def _load(name):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


@cache
def company():
    return _load("company.json")


@cache
def _by_id(name, key):
    return {row[key]: row for row in _load(name)}


def list_claims():
    return list(_by_id("claims.json", "claim_id").values())


def get_claim(claim_id):
    return _by_id("claims.json", "claim_id")[claim_id]


def get_policy(policy_id):
    return _by_id("policies.json", "policy_id")[policy_id]


def get_claim_history(customer_id):
    return _by_id("customers.json", "customer_id")[customer_id]["previous_claims"]


def document_text(document):
    return (DATA_DIR / DOCUMENTS[document]).read_text(encoding="utf-8")


@cache
def sections(document):
    """The numbered sections of a document, keyed by number: {1: (title, text), ...}."""
    text = document_text(document)
    matches = list(SECTION.finditer(text))
    found = {}
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        found[int(match.group(1))] = (match.group(2), text[match.start() : end].strip())
    return found


def search_documents(query):
    """The sections of either document that contain the query, as (document, number, title)."""
    query = query.lower()
    return [
        {"document": document, "section": number, "title": title}
        for document in DOCUMENTS
        for number, (title, text) in sections(document).items()
        if query in text.lower()
    ]


def read_section(document, number):
    title, text = sections(document)[number]
    return {"document": document, "section": number, "title": title, "text": text}
