#!/usr/bin/env sh
set -eu

CERT_ROOT="${1:-infrastructure/certs}"
CA_KEY="$CERT_ROOT/ca/ca.key"
CA_CERT="$CERT_ROOT/ca/ca.crt"
EDGE_DIR="$CERT_ROOT/edge"
EDGE_KEY="$EDGE_DIR/edge.key"

if [ ! -f "$CA_KEY" ] || [ ! -f "$CA_CERT" ]; then
  echo "Missing CA key or certificate under $CERT_ROOT/ca" >&2
  exit 1
fi
if [ ! -f "$EDGE_KEY" ] || [ ! -f "$EDGE_DIR/edge.crt" ]; then
  echo "Missing dedicated edge client certificate under $EDGE_DIR; regenerate certificates first" >&2
  exit 1
fi

# Runtime containers use UID/GID 10001. The CA private key stays root-owned
# and is never mounted into any runtime container.
chown -R 10001:10001 "$CERT_ROOT"
find "$CERT_ROOT" -type d -exec chmod 750 {} +
find "$CERT_ROOT" -type f -name '*.crt' -exec chmod 644 {} +
find "$CERT_ROOT" -type f -name '*.key' -exec chmod 600 {} +
chown root:root "$CA_KEY"
chmod 600 "$CA_KEY"
# Caddy runs as root with all capabilities dropped except NET_BIND_SERVICE.
# Keep its client key in a root-traversable directory and root-only file.
chown root:root "$EDGE_DIR"
chmod 750 "$EDGE_DIR"
chown root:root "$EDGE_KEY"
chmod 600 "$EDGE_KEY"

# The edge directory contains only the edge client identity and public CA
# certificate. It does not contain ca.key, coordinator.key, or party keys.
install -o root -g root -m 644 "$CA_CERT" "$EDGE_DIR/ca.crt"

echo "Certificate permissions set. CA private key remains root-owned and is not container-mounted."
echo "Caddy receives the edge identity directory with edge.key (0600) and ca.crt, but no other private keys."
