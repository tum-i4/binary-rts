import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

JSON_INDENT: int = 2


class LogEvent:
    def __init__(
        self,
        name: str,
        value: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        self.name = name
        self.value = value
        self.timestamp = timestamp or datetime.now()

    def append(self, log_file: Path):
        with log_file.open("a+") as file:
            serializable_dict: Dict = self.__dict__.copy()
            serializable_dict["timestamp"] = self.timestamp.isoformat()
            file.write(f"{json.dumps(serializable_dict)}\n")

    @classmethod
    def get_time_diff(cls, event1: "LogEvent", event2: "LogEvent") -> timedelta:
        return event1.timestamp - event2.timestamp

    @classmethod
    def read_from_log(cls, log_file: Path) -> List["LogEvent"]:
        log_events: List["LogEvent"] = []
        with log_file.open("r") as file:
            for line in file:

                def _deserialization_object_hook(data: Dict):
                    return cls(
                        data["name"],
                        data["value"],
                        datetime.fromisoformat(data["timestamp"]),
                    )

                log_event: LogEvent = json.loads(
                    line.strip(), object_hook=_deserialization_object_hook
                )
                log_events.append(log_event)
        return log_events
