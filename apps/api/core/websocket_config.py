"""WebSocket configuration and constants for Step 7F."""

import os

# WebSocket authentication timeout (hard limit)
WS_AUTH_TIMEOUT_SECONDS = 5

# WebSocket message size limit
WS_MAX_MESSAGE_SIZE = 2_000  # 2KB for messages

# Messages per second per socket (rate limit)
WS_MESSAGES_PER_SECOND = 10

# Max concurrent sockets per user
WS_MAX_SOCKETS_PER_USER = 5

# Idle connection timeout (ping/pong)
WS_IDLE_TIMEOUT_SECONDS = 5 * 60  # 5 minutes

# Heartbeat interval (ping)
WS_HEARTBEAT_INTERVAL_SECONDS = 30

# Connection registry cleanup (single-worker limitation)
WS_SINGLE_WORKER_ENFORCEMENT = os.getenv("WEB_CONCURRENCY", "1") == "1"
"""
IMPORTANT: The ConnectionManager is an in-process dict.
With multiple workers, messages sent via one worker are NOT delivered
to sockets connected to another worker. This is a hard limitation
of the memory-based connection registry.

Deployment target: Render (default), Cloud Run, or other.
Set WEB_CONCURRENCY=1 and max_instances=1 in deployment config if using memory registry.
Implement Redis message bus if multiple workers are needed.
"""

MESSAGE_BUS_TYPE = os.getenv("MESSAGE_BUS", "memory")  # "memory" or "redis"
"""
Message bus type for multi-worker deployments.
- memory: In-process dict, single worker only, no Redis required
- redis: Publish/subscribe for multi-worker, requires REDIS_URL env var
"""

REDIS_URL = os.getenv("REDIS_URL", "")
"""
Redis connection URL for MESSAGE_BUS=redis deployments.
Format: redis://[:password@]host[:port][/db]
Only required if MESSAGE_BUS=redis.
TLS/SSL: Use rediss:// scheme for TLS connections.
"""
