#!/usr/bin/env python3
"""Simple RAG example using ModelBridge for embeddings + chat.

Architecture:
  Documents → Embeddings (ModelBridge) → In-memory vectors → Context → Chat (ModelBridge)

ModelBridge is NOT a vector database — this example uses a simple in-memory store.
"""

import math
import os

from modelbridge import ModelBridge

DOCS = [
    "ModelBridge is an open-source AI gateway.",
    "ModelBridge routes requests to multiple AI providers.",
    "ModelBridge supports chat, embeddings, tools, and vision.",
]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def main():
    client = ModelBridge(
        base_url=os.environ.get("MODELBRIDGE_URL", "http://localhost:8000"),
        api_key=os.environ["MODELBRIDGE_API_KEY"],
    )

    vectors = []
    for doc in DOCS:
        emb = client.embeddings.create(model="auto", input=doc)
        vectors.append((doc, emb["data"][0]["embedding"]))

    query = "What providers does the gateway support?"
    q_emb = client.embeddings.create(model="auto", input=query)["data"][0]["embedding"]
    ranked = sorted(vectors, key=lambda x: cosine(q_emb, x[1]), reverse=True)
    context = "\n".join(d[0] for d in ranked[:2])

    answer = client.chat.completions.create(
        model="auto",
        messages=[
            {"role": "system", "content": f"Use this context:\n{context}"},
            {"role": "user", "content": query},
        ],
    )
    print(answer["choices"][0]["message"]["content"])


if __name__ == "__main__":
    main()
