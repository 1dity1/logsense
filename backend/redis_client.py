import socket
import hashlib

class RedisLiteClient:
    def __init__(self, host="localhost", port=6379):
        self.host = host
        self.port = port

    def _send(self, cmd: str) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((self.host, self.port))
            s.sendall((cmd + "\n").encode())
            response = s.recv(4096).decode()
            s.close()
            return response.strip()
        except Exception:
            return None

    def get(self, key: str) -> str | None:
        resp = self._send(f"GET {key}")
        if not resp or resp == "$-1":
            return None
        lines = resp.split("\n")
        if len(lines) >= 2:
            return lines[1].strip()
        return None

    def setex(self, key: str, seconds: int, value: str) -> bool:
        # Escape quotes in value
        value = value.replace('"', "'")
        resp = self._send(f'SETEX {key} {seconds} "{value}"')
        return resp == "+OK"

    def hash_key(self, text: str) -> str:
        return "logsense:" + hashlib.md5(text.encode()).hexdigest()
