import time

import pytest

from backend.security.tokens import FounderTokenError, issue_founder_token, verify_founder_token


def test_token_is_limited_to_one_session_and_party():
    token = issue_founder_token("secret", "session-a", 1, int(time.time()) + 60)
    capability = verify_founder_token(token, "secret", "session-a", 1)
    assert capability.session_id == "session-a"
    assert capability.party_id == 1

    with pytest.raises(FounderTokenError):
        verify_founder_token(token, "secret", "session-b", 1)
    with pytest.raises(FounderTokenError):
        verify_founder_token(token, "secret", "session-a", 2)


def test_token_expiry_and_tampering_are_rejected():
    expired = issue_founder_token("secret", "session-a", 0, 1)
    with pytest.raises(FounderTokenError, match="expired"):
        verify_founder_token(expired, "secret", "session-a", 0, now=2)

    valid = issue_founder_token("secret", "session-a", 0, int(time.time()) + 60)
    with pytest.raises(FounderTokenError):
        verify_founder_token(valid[:-1] + "x", "secret", "session-a", 0)
