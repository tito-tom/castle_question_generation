
class Timestamp:
    def __init__(self, value: str):
        self._seconds = self._parse(value)
        self._value = value

    @staticmethod
    def _parse(value: str) -> float:
        parts = value.split(":")

        if len(parts) != 3:
            raise ValueError(
                f"Invalid timestamp format: {value}. "
                "Expected HH:MM:SS or HH:MM:SS.xxx."
            )

        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])

        if hours < 0:
            raise ValueError("Hours cannot be negative.")

        if not 0 <= minutes < 60:
            raise ValueError("Minutes must be between 0 and 59.")

        if not 0 <= seconds < 60:
            raise ValueError("Seconds must be between 0 and 60.")

        return hours * 3600 + minutes * 60 + seconds

    @classmethod
    def from_seconds(cls, seconds: float) -> "Timestamp":
        if seconds < 0:
            raise ValueError("Timestamp cannot be negative.")

        # Round to milliseconds to prevent 59.999999... issues
        total_milliseconds = round(seconds * 1000)

        hours, remainder = divmod(total_milliseconds, 3600000)
        minutes, remainder = divmod(remainder, 60000)
        whole_seconds, milliseconds = divmod(remainder, 1000)

        value = (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{whole_seconds:02d}."
            f"{milliseconds:03d}"
        )

        return cls(value)

    @property
    def seconds(self) -> float:
        return self._seconds

    @property
    def value(self) -> str:
        return self._value

    def __str__(self) -> str:
        return self._value
