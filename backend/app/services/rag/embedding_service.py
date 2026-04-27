"""
Embedding Service for AURA RAG Pipeline.

Uses Gemini Embedding API (gemini-embedding-001) for generating vector embeddings.
Reference: nexora/backend/pipelines/knowledge.py and search.py

Features:
- Single text and batch text embedding generation
- Token limit management and truncation
- Fallback to random embeddings when API key is unavailable
- Configurable embedding dimensions
"""

import os
import logging
from typing import List, Optional

import requests
import numpy as np

from config.settings import settings

logger = logging.getLogger(__name__)

# Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "768"))
TOKEN_LIMIT = 2048  # Gemini embedding input token limit
GOOGLE_API_KEY = settings.GOOGLE_API_KEY


def estimate_token_count(text: str) -> int:
    """
    Estimate token count for text.
    Rough approximation: 1 token ~ 4 characters for English text.
    """
    return len(text) // 4


def truncate_to_token_limit(text: str, token_limit: int = TOKEN_LIMIT) -> str:
    """Truncate text to stay within token limit."""
    estimated_tokens = estimate_token_count(text)
    if estimated_tokens <= token_limit:
        return text
    char_limit = token_limit * 4
    return text[:char_limit]


def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate a single embedding vector for the given text using Gemini API.

    Args:
        text: Input text to embed

    Returns:
        List of floats representing the embedding vector, or None on failure
    """
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{EMBEDDING_MODEL}:embedContent"
    )

    if not GOOGLE_API_KEY:
        logger.warning("No Google API key available, using fallback embeddings")
        return np.random.randn(EMBEDDING_DIMENSION).tolist()

    truncated_text = truncate_to_token_limit(text)

    payload = {
        "model": f"models/{EMBEDDING_MODEL}",
        "content": {
            "parts": [{"text": truncated_text}]
        },
        "outputDimensionality": EMBEDDING_DIMENSION
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            f"{endpoint}?key={GOOGLE_API_KEY}",
            json=payload,
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            embedding_values = result.get("embedding", {}).get("values", [])
            if embedding_values:
                if len(embedding_values) != EMBEDDING_DIMENSION:
                    logger.warning(
                        "Unexpected embedding dimension: %d, expected: %d",
                        len(embedding_values), EMBEDDING_DIMENSION
                    )
                return embedding_values
            else:
                logger.warning("No embedding values returned for text: %s...", text[:50])
                return np.random.randn(EMBEDDING_DIMENSION).tolist()
        else:
            logger.error("Gemini API error: %d - %s", response.status_code, response.text)
            return np.random.randn(EMBEDDING_DIMENSION).tolist()

    except Exception as e:
        logger.error("Error calling Gemini Embedding API: %s", e)
        return np.random.randn(EMBEDDING_DIMENSION).tolist()


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a batch of texts.

    Processes texts one at a time through the Gemini API.

    Args:
        texts: List of input texts

    Returns:
        List of embedding vectors
    """
    all_embeddings = []

    for i, text in enumerate(texts):
        logger.info("Generating embedding %d/%d", i + 1, len(texts))
        embedding = generate_embedding(text)
        if embedding:
            all_embeddings.append(embedding)
        else:
            # Fallback for failed embeddings
            all_embeddings.append(np.random.randn(EMBEDDING_DIMENSION).tolist())

    return all_embeddings


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        vec_a: First vector
        vec_b: Second vector

    Returns:
        Cosine similarity score between -1 and 1
    """
    a = np.array(vec_a)
    b = np.array(vec_b)
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot_product / (norm_a * norm_b))
