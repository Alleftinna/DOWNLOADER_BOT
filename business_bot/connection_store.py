import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ConnectionStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._connection_id: str | None = None
        self._user_id: int | None = None
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self._connection_id = data.get("connection_id")
            user_id = data.get("user_id")
            self._user_id = int(user_id) if user_id is not None else None
            logger.info("Loaded business connection from %s", self.path)
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            logger.warning("Could not load business connection file: %s", exc)

    def save(self, connection_id: str, user_id: int | None = None) -> None:
        self._connection_id = connection_id
        self._user_id = user_id
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"connection_id": connection_id}
        if user_id is not None:
            payload["user_id"] = user_id
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info("Saved business connection id=%s user_id=%s", connection_id, user_id)

    def clear(self) -> None:
        self._connection_id = None
        self._user_id = None
        if self.path.exists():
            self.path.unlink()
        logger.info("Cleared business connection")

    def get_connection_id(self) -> str | None:
        return self._connection_id

    def get_user_id(self) -> int | None:
        return self._user_id

    def is_connected(self) -> bool:
        return bool(self._connection_id)
