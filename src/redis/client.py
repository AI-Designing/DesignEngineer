class RedisClient:
    def __init__(self, host='localhost', port=6379, db=0):
        self.host = host
        self.port = port
        self.db = db
        self.connection = None

    def connect(self):
        import redis
        self.connection = redis.StrictRedis(host=self.host, port=self.port, db=self.db)
        return self.connection.ping()

    def set(self, key, value):
        if self.connection is None:
            raise ConnectionError("Redis client is not connected.")
        self.connection.set(key, value)

    def get(self, key):
        if self.connection is None:
            raise ConnectionError("Redis client is not connected.")
        return self.connection.get(key)