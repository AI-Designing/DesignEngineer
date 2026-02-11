from typing import Any, Dict, List, Optional, Tuple

import redis
from redis.connection import ConnectionPool


class RedisClient:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        max_connections: int = 50,
    ):
        self.host = host
        self.port = port
        self.db = db
        self.connection: Optional[redis.Redis] = None
        self.pool: Optional[ConnectionPool] = None
        self.max_connections = max_connections

    def connect(self) -> bool:
        """Establish connection to Redis with connection pooling."""
        try:
            # Create connection pool for efficient async/concurrent access
            self.pool = ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                max_connections=self.max_connections,
                decode_responses=False,  # We handle decoding manually for flexibility
            )
            self.connection = redis.Redis(connection_pool=self.pool)
            return self.connection.ping()
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
            return False

    def _check_connection(self):
        """Raise an error if Redis is not connected."""
        if self.connection is None:
            raise ConnectionError(
                "❌ Redis client is not connected. Call connect() first."
            )

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set a key-value pair with optional expiration time (in seconds)."""
        self._check_connection()
        return self.connection.set(key, value, ex=ex)

    def get(self, key: str) -> Optional[bytes]:
        """Get the value of a key."""
        self._check_connection()
        return self.connection.get(key)

    def delete(self, key: str) -> int:
        """Delete a key."""
        self._check_connection()
        return self.connection.delete(key)

    def exists(self, key: str) -> bool:
        """Check if a key exists."""
        self._check_connection()
        return bool(self.connection.exists(key))

    def keys(self, pattern: str = "*") -> List[str]:
        """Return a list of keys matching the given pattern."""
        self._check_connection()
        return [
            k.decode("utf-8") if isinstance(k, bytes) else k
            for k in self.connection.keys(pattern)
        ]

    def flushdb(self) -> bool:
        """Delete all keys in the current database."""
        self._check_connection()
        self.connection.flushdb()
        return True

    def hset(self, name: str, key: str, value: Any) -> int:
        """Set a field in a hash."""
        self._check_connection()
        return self.connection.hset(name, key, value)

    def hget(self, name: str, key: str) -> Optional[str]:
        """Get a field value from a hash."""
        self._check_connection()
        result = self.connection.hget(name, key)
        return result.decode("utf-8") if isinstance(result, bytes) else result

    def hgetall(self, name: str) -> Dict[str, str]:
        """Get all fields and values in a hash."""
        self._check_connection()
        result = self.connection.hgetall(name)
        return {
            k.decode("utf-8")
            if isinstance(k, bytes)
            else k: (v.decode("utf-8") if isinstance(v, bytes) else v)
            for k, v in result.items()
        }

    def hdel(self, name: str, key: str) -> int:
        """Delete a field from a hash."""
        self._check_connection()
        return self.connection.hdel(name, key)

    # Redis Streams operations
    def xadd(
        self,
        stream: str,
        fields: Dict[str, Any],
        maxlen: Optional[int] = 1000,
        approximate: bool = True,
    ) -> str:
        """
        Add entry to Redis Stream with automatic trimming.

        Args:
            stream: Stream name
            fields: Field-value pairs to add
            maxlen: Maximum stream length (default 1000, prevents unbounded growth)
            approximate: Use approximate trimming (~) for better performance

        Returns:
            Entry ID (e.g., '1234567890123-0')
        """
        self._check_connection()
        return self.connection.xadd(stream, fields, maxlen=maxlen, approximate=approximate)

    def xrange(
        self,
        stream: str,
        start: str = "-",
        end: str = "+",
        count: Optional[int] = None,
    ) -> List[Tuple[bytes, Dict[bytes, bytes]]]:
        """
        Read entries from Redis Stream.

        Args:
            stream: Stream name
            start: Start ID ('-' for beginning)
            end: End ID ('+' for end)
            count: Maximum number of entries

        Returns:
            List of (entry_id, fields) tuples
        """
        self._check_connection()
        return self.connection.xrange(stream, start, end, count)

    def xrevrange(
        self,
        stream: str,
        start: str = "+",
        end: str = "-",
        count: Optional[int] = None,
    ) -> List[Tuple[bytes, Dict[bytes, bytes]]]:
        """
        Read entries from Redis Stream in reverse order.

        Args:
            stream: Stream name
            start: Start ID ('+' for end)
            end: End ID ('-' for beginning)
            count: Maximum number of entries

        Returns:
            List of (entry_id, fields) tuples in reverse order
        """
        self._check_connection()
        return self.connection.xrevrange(stream, start, end, count)

    def xlen(self, stream: str) -> int:
        """Get the number of entries in a stream."""
        self._check_connection()
        return self.connection.xlen(stream)

    # Redis Pub/Sub operations
    def publish(self, channel: str, message: str) -> int:
        """
        Publish message to Redis Pub/Sub channel.

        Args:
            channel: Channel name
            message: Message to publish (typically JSON string)

        Returns:
            Number of subscribers that received the message
        """
        self._check_connection()
        return self.connection.publish(channel, message)

    def subscribe(self, *channels: str) -> redis.client.PubSub:
        """
        Create PubSub instance subscribed to channels.

        Args:
            channels: Channel names to subscribe to

        Returns:
            PubSub object for listening to messages
        """
        self._check_connection()
        pubsub = self.connection.pubsub()
        pubsub.subscribe(*channels)
        return pubsub

    # TTL operations
    def expire(self, key: str, seconds: int) -> bool:
        """
        Set TTL (time-to-live) on a key.

        Args:
            key: Key name
            seconds: Expiration time in seconds

        Returns:
            True if TTL was set, False if key doesn't exist
        """
        self._check_connection()
        return bool(self.connection.expire(key, seconds))

    def ttl(self, key: str) -> int:
        """
        Get remaining TTL of a key.

        Args:
            key: Key name

        Returns:
            Seconds remaining, -1 if no expiration, -2 if key doesn't exist
        """
        self._check_connection()
        return self.connection.ttl(key)


# Example usage:
if __name__ == "__main__":
    # Create Redis client
    client = RedisClient()

    # Connect to Redis
    if client.connect():
        print("✅ Connected to Redis successfully!")

        # Test basic operations
        client.set("test_key", "test_value")
        value = client.get("test_key")
        print(f"Retrieved value: {value}")

        # Test hash operations
        client.hset("user:1", "name", "John Doe")
        client.hset("user:1", "email", "john@example.com")
        user_data = client.hgetall("user:1")
        print(f"User data: {user_data}")

    else:
        print("❌ Failed to connect to Redis")
