from pathlib import Path
import re

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


# ResolveAI project policy storage.
POLICY_DIR = Path(__file__).resolve().parents[3] / "data" / "policies"
CHROMA_DIR = Path(__file__).resolve().parents[2] / "chroma_db"
COLLECTION_NAME = "resolveai_policies"

# A conservative initial threshold for ChromaDB's distance metric.
# Lower distances generally indicate closer matches. Validate this value
# against your own queries and policy corpus.
MAX_POLICY_DISTANCE = 1.5

POLICIES = {
    "damaged_product": {
        "title": "Damaged Product and Replacement Policy",
        "text": (
            "Customers should report damaged products within 7 calendar "
            "days of delivery. A photograph of the damaged product is "
            "required before a replacement request is created. Verify "
            "order ownership, delivery date, eligibility, and existing "
            "replacement requests before creating a replacement."
        ),
    },
    "return": {
        "title": "Product Return Policy",
        "text": (
            "Delivered products can be returned within 7 calendar days "
            "unless the product is marked non-returnable. A return "
            "already created for the same order cannot be duplicated."
        ),
    },
    "refund": {
        "title": "Refund Policy",
        "text": (
            "A paid order may be refunded when no previous refund exists. "
            "Refunds cannot exceed the paid amount. Automatic refunds "
            "above INR 10,000 require human approval."
        ),
    },
    "cancellation": {
        "title": "Order Cancellation Policy",
        "text": (
            "Orders may be cancelled before shipment. Shipped or delivered "
            "orders cannot be automatically cancelled."
        ),
    },
    "delivery": {
        "title": "Delivery and Tracking Policy",
        "text": (
            "Customers can ask for order tracking and delivery status. "
            "Use the order record as the source of truth. If tracking "
            "information is unavailable or the delivery appears delayed, "
            "explain the available information or escalate for review."
        ),
    },
    "payment": {
        "title": "Payment Policy",
        "text": (
            "Payment questions must be checked against the payment record. "
            "Do not claim a payment succeeded or failed without evidence. "
            "Escalate missing or inconsistent payment records for review."
        ),
    },
    "general": {
        "title": "General Customer Support Policy",
        "text": (
            "Investigate the customer request using verified account, "
            "order, and payment records. Follow the applicable policy. "
            "Escalate cases that cannot be safely resolved automatically."
        ),
    },
}


def _normalise(text: str) -> str:
    """Normalise text for simple, predictable keyword matching."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _keyword_fallback(query: str, limit: int = 1) -> list[dict]:
    """Retrieve policies with keyword scoring when vector retrieval is weak."""
    q = _normalise(query)
    terms = set(q.split())

    # Add common ways customers describe each policy topic.
    aliases = {
        "damaged_product": {
            "damage", "damaged", "broken", "cracked", "defective",
            "faulty", "replacement", "replace",
        },
        "return": {
            "return", "returns", "send", "back", "give", "back",
            "nonreturnable", "non", "returnable",
        },
        "refund": {
            "refund", "refunded", "money", "back", "reimburse",
            "reimbursement", "charged",
        },
        "cancellation": {
            "cancel", "cancellation", "cancelled", "canceled",
        },
        "delivery": {
            "delivery", "delivered", "tracking", "track", "package",
            "parcel", "late", "delayed", "shipment", "shipping",
        },
        "payment": {
            "payment", "paid", "charge", "charged", "transaction",
            "card", "billing",
        },
        "general": set(),
    }

    scored = []

    for policy_id, policy in POLICIES.items():
        content = _normalise(f"{policy['title']} {policy['text']}")
        content_terms = set(content.split())

        # Score meaningful query terms that occur in policy text.
        score = sum(
            1
            for term in terms
            if len(term) > 2 and term in content_terms
        )

        # Give a stronger signal to topic-specific synonyms.
        score += 4 * len(terms.intersection(aliases.get(policy_id, set())))

        if score > 0:
            scored.append((score, policy_id, policy))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)

    if not scored:
        policy = POLICIES["general"]
        return [
            {
                "id": "general",
                "title": policy["title"],
                "text": policy["text"],
                "source": "built_in_policy",
                "distance": None,
            }
        ]

    return [
        {
            "id": policy_id,
            "title": policy["title"],
            "text": policy["text"],
            "source": "built_in_policy",
            "distance": None,
        }
        for _, policy_id, policy in scored[:max(1, limit)]
    ]


def _get_collection():
    """Create or reuse the persistent ChromaDB policy collection."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=DefaultEmbeddingFunction(),
        metadata={"description": "ResolveAI customer support policies"},
    )

    # Keep the collection synchronised with the policy definitions above.
    ids = list(POLICIES.keys())
    documents = [
        f"{policy['title']}\n{policy['text']}"
        for policy in POLICIES.values()
    ]
    metadatas = [
        {"title": policy["title"], "policy_id": policy_id}
        for policy_id, policy in POLICIES.items()
    ]

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    return collection


def retrieve_policy_chunks(query: str, limit: int = 1) -> list[dict]:
    """
    Retrieve the most relevant policy using ChromaDB.

    If the best vector result is weak, use keyword fallback instead.
    The distance threshold is a configurable heuristic, not a guarantee
    that a retrieved policy is factually sufficient for every question.
    """
    query = (query or "").strip()
    limit = max(1, min(limit, len(POLICIES)))

    if not query:
        return _keyword_fallback("general customer support", limit=limit)

    try:
        collection = _get_collection()
        result = collection.query(
            query_texts=[query],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )

        documents = result.get("documents", [[]])[0] or []
        metadatas = result.get("metadatas", [[]])[0] or []
        ids = result.get("ids", [[]])[0] or []
        distances = result.get("distances", [[]])[0] or []

        chunks = []

        for i, document in enumerate(documents):
            metadata = metadatas[i] or {}
            distance = distances[i] if i < len(distances) else None
            policy_id = (
                metadata.get("policy_id")
                or (ids[i] if i < len(ids) else "general")
            )

            # Use our canonical policy text instead of trusting arbitrary
            # stored document contents if the collection has stale data.
            canonical = POLICIES.get(policy_id)

            chunks.append(
                {
                    "id": policy_id,
                    "title": (
                        canonical["title"]
                        if canonical
                        else metadata.get("title", "Support policy")
                    ),
                    "text": (
                        canonical["text"]
                        if canonical
                        else document
                    ),
                    "source": "chromadb",
                    "distance": distance,
                }
            )

        if chunks:
            best_distance = chunks[0].get("distance")

            # Only accept the vector result when it passes the current
            # heuristic. Otherwise use the keyword fallback.
            if (
                best_distance is not None
                and best_distance <= MAX_POLICY_DISTANCE
            ):
                return chunks

    except Exception as exc:
        print(f"[ResolveAI RAG] Vector retrieval unavailable: {exc}")

    return _keyword_fallback(query, limit=limit)


def search_policy(query: str) -> str:
    """
    Backward-compatible wrapper for existing agent code.
    Returns retrieved policy text as a readable string.
    """
    chunks = retrieve_policy_chunks(query)

    return "\n\n".join(
        f"Policy: {chunk['title']}\n{chunk['text']}"
        for chunk in chunks
    )



# from pathlib import Path

# import chromadb
# from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


# # ResolveAI/backend/data/policies
# POLICY_DIR = Path(__file__).resolve().parents[3] / "data" / "policies"

# CHROMA_DIR = Path(__file__).resolve().parents[2] / "chroma_db"
# COLLECTION_NAME = "resolveai_policies"

# POLICIES = {
#     "damaged_product": {
#         "title": "Damaged Product and Replacement Policy",
#         "text": (
#             "Customers should report damaged products within 7 calendar "
#             "days of delivery. A photograph of the damaged product is "
#             "required before a replacement request is created. Verify "
#             "order ownership, delivery date, eligibility, and existing "
#             "replacement requests before creating a replacement."
#         ),
#     },
#     "return": {
#         "title": "Product Return Policy",
#         "text": (
#             "Delivered products can be returned within 7 calendar days "
#             "unless the product is marked non-returnable. A return "
#             "already created for the same order cannot be duplicated."
#         ),
#     },
#     "refund": {
#         "title": "Refund Policy",
#         "text": (
#             "A paid order may be refunded when no previous refund exists. "
#             "Refunds cannot exceed the paid amount. Automatic refunds "
#             "above INR 10,000 require human approval."
#         ),
#     },
#     "cancellation": {
#         "title": "Order Cancellation Policy",
#         "text": (
#             "Orders may be cancelled before shipment. Shipped or delivered "
#             "orders cannot be automatically cancelled."
#         ),
#     },
#     "delivery": {
#         "title": "Delivery and Tracking Policy",
#         "text": (
#             "Customers can ask for order tracking and delivery status. "
#             "Use the order record as the source of truth. If tracking "
#             "information is unavailable or the delivery appears delayed, "
#             "explain the available information or escalate for review."
#         ),
#     },
#     "payment": {
#         "title": "Payment Policy",
#         "text": (
#             "Payment questions must be checked against the payment record. "
#             "Do not claim a payment succeeded or failed without evidence. "
#             "Escalate missing or inconsistent payment records for review."
#         ),
#     },
#     "general": {
#         "title": "General Customer Support Policy",
#         "text": (
#             "Investigate the customer request using verified account, "
#             "order, and payment records. Follow the applicable policy. "
#             "Escalate cases that cannot be safely resolved automatically."
#         ),
#     },
# }


# def _keyword_fallback(query: str, limit: int = 3) -> list[dict]:
#     """Simple fallback when the vector database is unavailable."""
#     q = query.lower()
#     terms = set(q.replace("-", " ").split())
#     scored = []

#     for policy_id, policy in POLICIES.items():
#         content = f"{policy['title']} {policy['text']}".lower()
#         score = sum(1 for term in terms if len(term) > 2 and term in content)

#         if policy_id == "damaged_product" and any(
#             word in q for word in ("damage", "damaged", "broken", "replacement")
#         ):
#             score += 5
#         if policy_id == "refund" and "refund" in q:
#             score += 5
#         if policy_id == "return" and "return" in q:
#             score += 5
#         if policy_id == "cancellation" and any(
#             word in q for word in ("cancel", "cancellation")
#         ):
#             score += 5
#         if policy_id == "delivery" and any(
#             word in q for word in ("delivery", "tracking", "delayed", "late")
#         ):
#             score += 5
#         if policy_id == "payment" and any(
#             word in q for word in ("payment", "charged", "transaction")
#         ):
#             score += 5

#         if score:
#             scored.append((score, policy_id, policy))

#     scored.sort(key=lambda item: item[0], reverse=True)

#     if not scored:
#         policy = POLICIES["general"]
#         return [{
#             "id": "general",
#             "title": policy["title"],
#             "text": policy["text"],
#             "source": "built_in_policy",
#         }]

#     return [
#         {
#             "id": policy_id,
#             "title": policy["title"],
#             "text": policy["text"],
#             "source": "built_in_policy",
#         }
#         for _, policy_id, policy in scored[:limit]
#     ]


# def _get_collection():
#     """Create or reuse the persistent ChromaDB policy collection."""
#     CHROMA_DIR.mkdir(parents=True, exist_ok=True)

#     client = chromadb.PersistentClient(path=str(CHROMA_DIR))

#     collection = client.get_or_create_collection(
#         name=COLLECTION_NAME,
#         embedding_function=DefaultEmbeddingFunction(),
#         metadata={"description": "ResolveAI customer support policies"},
#     )

#     # Keep the collection synchronized with the policies defined above.
#     ids = list(POLICIES.keys())
#     documents = [
#         f"{policy['title']}\n{policy['text']}"
#         for policy in POLICIES.values()
#     ]
#     metadatas = [
#         {"title": policy["title"], "policy_id": policy_id}
#         for policy_id, policy in POLICIES.items()
#     ]

#     collection.upsert(
#         ids=ids,
#         documents=documents,
#         metadatas=metadatas,
#     )

#     return collection


# def retrieve_policy_chunks(query: str, limit: int = 3) -> list[dict]:
#     """
#     Retrieve relevant policy chunks using vector similarity.
#     Falls back to keyword matching if ChromaDB or its embedding model fails.
#     """
#     if not query.strip():
#         query = "general customer support"

#     try:
#         collection = _get_collection()

#         result = collection.query(
#             query_texts=[query],
#             n_results=min(limit, len(POLICIES)),
#             include=["documents", "metadatas", "distances"],
#         )

#         documents = result.get("documents", [[]])[0]
#         metadatas = result.get("metadatas", [[]])[0]
#         ids = result.get("ids", [[]])[0]
#         distances = result.get("distances", [[]])[0]

#         chunks = []

#         for i, document in enumerate(documents):
#             metadata = metadatas[i] or {}
#             chunks.append({
#                 "id": ids[i],
#                 "title": metadata.get("title", "Support policy"),
#                 "text": document,
#                 "source": "chromadb",
#                 "distance": distances[i] if distances else None,
#             })

#         if chunks:
#             return chunks

#     except Exception as exc:
#         print(f"[ResolveAI RAG] Vector retrieval unavailable: {exc}")

#     return _keyword_fallback(query, limit)


# def search_policy(query: str) -> str:
#     """
#     Backward-compatible function used by the existing agent.
#     Returns retrieved policy text without changing the current agent interface.
#     """
#     chunks = retrieve_policy_chunks(query)

#     return "\n\n".join(
#         f"Policy: {chunk['title']}\n{chunk['text']}"
#         for chunk in chunks
#     )
