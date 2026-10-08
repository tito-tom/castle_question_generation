from src.utils.timestamp import Timestamp


def test_timestamp_to_seconds():

    timestamp = Timestamp(
        "00:32:40"
    )

    assert (
        timestamp.seconds
        == 1960.0
    )


def test_timestamp_from_seconds():

    timestamp = (
        Timestamp.from_seconds(
            1960
        )
    )

    assert str(
        timestamp
    ) == "00:32:40.000"