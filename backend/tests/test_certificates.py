"""Tests for the local development certificate generator."""

import os
import subprocess
import tempfile

import pytest

from backend.mpc.certificates import check_openssl_available, generate_certificates

# ── OpenSSL availability ─────────────────────────────────────────────────────

def test_check_openssl_available_returns_bool():
    """check_openssl_available() should return a boolean."""
    result = check_openssl_available()
    assert isinstance(result, bool)


# ── Certificate generation (conditional on openssl presence) ────────────────

OPENSSL_AVAILABLE = check_openssl_available()


@pytest.mark.skipif(not OPENSSL_AVAILABLE, reason="OpenSSL CLI not available")
class TestCertificateGeneration:
    """Tests that run only when OpenSSL CLI is installed."""

    def test_generates_ca_and_party_certs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_certificates(
                output_dir=tmpdir, parties_count=3, validity_days=30
            )

            # CA files
            assert os.path.isfile(os.path.join(tmpdir, "ca", "ca.key"))
            assert os.path.isfile(os.path.join(tmpdir, "ca", "ca.crt"))

            # Per-party MPyC and HTTPS-control files
            for i in range(3):
                party = result["parties"][i]
                assert os.path.isfile(party["mpyc"]["key"])
                assert os.path.isfile(party["mpyc"]["cert"])
                assert os.path.isfile(party["control"]["key"])
                assert os.path.isfile(party["control"]["cert"])
            assert os.path.isfile(result["api"]["cert"])
            assert os.path.isfile(result["coordinator"]["cert"])

    def test_idempotent_generation(self):
        """Running generate_certificates twice should not fail (existing files are skipped)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result1 = generate_certificates(output_dir=tmpdir, parties_count=3)
            result2 = generate_certificates(output_dir=tmpdir, parties_count=3)
            assert result1.keys() == result2.keys()

    def test_party_keys_are_distinct(self):
        """Each party must have its own distinct private key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_certificates(output_dir=tmpdir, parties_count=3)
            keys = []
            for i in range(3):
                with open(result["parties"][i]["mpyc"]["key"]) as f:
                    keys.append(f.read())
            # All keys must be unique
            assert len(set(keys)) == 3

    def test_all_certs_share_same_ca(self):
        """All party certificates should reference the same CA cert path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_certificates(output_dir=tmpdir, parties_count=3)
            ca_paths = {result["parties"][i]["mpyc"]["ca_cert"] for i in range(3)}
            assert len(ca_paths) == 1  # All share same CA cert


@pytest.mark.skipif(OPENSSL_AVAILABLE, reason="Only runs when OpenSSL is NOT available")
class TestWithoutOpenSSL:
    """Tests that verify graceful behavior when OpenSSL is missing."""

    def test_check_reports_unavailable(self):
        assert check_openssl_available() is False

    def test_generate_raises_without_openssl(self):
        """generate_certificates should raise when openssl is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises((FileNotFoundError, subprocess.CalledProcessError)):
                generate_certificates(output_dir=tmpdir, parties_count=3)
