
from src.models.event import Event


def test_structured_event():

    data = {
        "start_seconds": 40.0,
        "end_seconds": 45.0,
        "actor": "person_5",
        "action": "retrieves",
        "object": "drink",
        "target": "fridge",
        "description": (
            "Person 5 retrieves a drink from the fridge."
        )
    }

    event = Event.from_dict(data)

    assert event.actor == "person_5"
    assert event.action == "retrieves"
    assert event.object_name == "drink"
    assert event.target == "fridge"
    assert event.confidence is None


def test_optional_object_and_confidence():

    data = {
        "start_seconds": 2.0,
        "end_seconds": 5.0,
        "description": "Person 1 walks into the kitchen.",
        "object": None,
        "confidence": None
    }

    event = Event.from_dict(data)

    assert event.object_name is None
    assert event.confidence is None
