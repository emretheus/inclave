from enclave_core.errors import EnclaveError


def test_enclave_error_is_exception() -> None:
    assert issubclass(EnclaveError, Exception)


def test_enclave_error_message_round_trip() -> None:
    err = EnclaveError("boom")
    assert str(err) == "boom"
