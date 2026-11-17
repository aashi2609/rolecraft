"""Single source of truth for embedding provider settings.

Migrations cannot import application code, so the migration hardcodes
the dimension; tests/test_embedding_config_consistency.py asserts the
hardcoded value equals EMBEDDING_DIM.
"""

EMBEDDING_MODEL = "text-embedding-3-small"
# Native output size of text-embedding-3-small (1536). We do NOT send the
# "dimensions" parameter — native size gives the best quality and pgvector
# handles it fine. See Step F report for the decision record.
EMBEDDING_DIM = 1536
# Bump when the text builders change shape so stale vectors are re-embedded.
EMBEDDING_INPUT_VERSION = "v1"
