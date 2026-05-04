from inclave_core.errors import InClaveError


def test_inclave_error_is_exception() -> None:
    assert issubclass(InClaveError, Exception)


def test_inclave_error_message_round_trip() -> None:
    err = InClaveError("boom")
    assert str(err) == "boom"
