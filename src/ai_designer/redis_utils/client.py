from typing import Any, Dict, List, Optional

import redis


class RedisClient:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self.db = db
        self.connection: Optional[redis.Redis] = None

    def connect(self) -> bool:
        """Establish connection to Redis and return True if successful."""
        try:
            self.connection = redis.Redis(host=self.host, port=self.port, db=self.db)
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
