import json
import os
from typing import Any

class Result_store:
    def __init__(self, filepath: str = "results.json") -> None:
        self.filepath = filepath
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w") as f:
                json.dump([], f)

    def _load(self) -> list[dict[str, Any]]:
        try:
            with open(self.filepath, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save(self, data: list[dict[str, Any]]) -> None:
        with open(self.filepath, "w") as f:
            json.dump(data, f)

    def add_to_database(self, new_item: dict[str, Any]) -> None:
        data = self._load()
        for i, item in enumerate(data):
            if item.get("job_id") == new_item.get("job_id"):
                data[i] = new_item
                self._save(data)
                return
        data.append(new_item)
        self._save(data)

    def check_status(self, job_id: str) -> dict[str, Any]:
        data = self._load()
        for item in data:
            if item.get("job_id") == job_id:
                return {"status": item.get("status"), "response": item.get("response", None)}
        
        return {"status": "queued",
                "n" : f"{len(data)} items in queue."}

result_store = Result_store()