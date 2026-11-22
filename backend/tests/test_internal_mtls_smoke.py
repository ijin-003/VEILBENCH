"""Exercise the internal mTLS smoke check against a local TLS server."""

import json
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from backend.mpc.certificates import check_openssl_available, generate_certificates
from backend.ops.smoke_test_internal_mtls import _check_party


@pytest.mark.skipif(not check_openssl_available(), reason="OpenSSL CLI not available")
def test_internal_mtls_smoke_accepts_client_certificate_and_rejects_anonymous(tmp_path):
    certificates = generate_certificates(str(tmp_path), parties_count=3, validity_days=30)
    party = certificates["parties"][0]

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps(
                {"status": "healthy", "party_id": 0, "mpyc_tls_enabled": True}
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            return

    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(party["control"]["cert"], party["control"]["key"])
    server_context.load_verify_locations(certificates["api"]["ca_cert"])
    server_context.verify_mode = ssl.CERT_REQUIRED

    class MutualTLSHTTPServer(ThreadingHTTPServer):
        def get_request(self):
            connection, address = super().get_request()
            return server_context.wrap_socket(connection, server_side=True), address

    server = MutualTLSHTTPServer(("127.0.0.1", 0), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    authenticated = ssl.create_default_context(cafile=certificates["api"]["ca_cert"])
    authenticated.load_cert_chain(party["mpyc"]["cert"], party["mpyc"]["key"])
    anonymous = ssl.create_default_context(cafile=certificates["api"]["ca_cert"])

    try:
        _check_party(
            f"https://127.0.0.1:{server.server_port}",
            0,
            authenticated,
            anonymous,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
