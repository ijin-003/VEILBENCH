#!/usr/bin/env bash
# Install Docker Engine + Compose plugin on a supported Ubuntu LTS VPS.
# Optional firewall setup is explicit to avoid locking out SSH users.
set -Eeuo pipefail

CONFIGURE_FIREWALL=0
SSH_PORT="${SSH_PORT:-22}"
while (($#)); do
  case "$1" in
    --configure-firewall) CONFIGURE_FIREWALL=1 ;;
    --ssh-port)
      shift
      [[ $# -gt 0 ]] || { echo "Missing value for --ssh-port" >&2; exit 2; }
      SSH_PORT="$1"
      ;;
    --help|-h)
      echo "Usage: sudo bash scripts/bootstrap_ubuntu_vps.sh [--configure-firewall] [--ssh-port 22]"
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script with sudo/root." >&2
  exit 1
fi
if [[ ! -r /etc/os-release ]]; then
  echo "Cannot identify Linux distribution." >&2
  exit 1
fi
. /etc/os-release
if [[ "${ID:-}" != "ubuntu" ]]; then
  echo "This bootstrap script supports Ubuntu only (detected: ${ID:-unknown})." >&2
  exit 1
fi
if [[ ! "$SSH_PORT" =~ ^[0-9]{1,5}$ ]] || ((SSH_PORT < 1 || SSH_PORT > 65535)); then
  echo "Invalid SSH port: $SSH_PORT" >&2
  exit 2
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl gnupg openssl python3 python3-venv unzip
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
ARCH="$(dpkg --print-architecture)"
CODENAME="${VERSION_CODENAME:?Ubuntu VERSION_CODENAME is required}"
printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' "$ARCH" "$CODENAME" \
  > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

docker --version
docker compose version

if ((CONFIGURE_FIREWALL)); then
  apt-get install -y ufw
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow "${SSH_PORT}/tcp" comment 'VEILBENCH SSH'
  ufw allow 80/tcp comment 'VEILBENCH HTTP ACME'
  ufw allow 443/tcp comment 'VEILBENCH HTTPS'
  ufw allow 443/udp comment 'VEILBENCH HTTP3'
  ufw --force enable
  ufw status verbose
else
  cat <<EOF
Docker is installed and running.
Firewall was NOT changed. Configure your provider firewall/security group to allow:
  TCP ${SSH_PORT} (restrict source IP where possible)
  TCP 80
  TCP 443
  UDP 443 (optional HTTP/3)
Do not expose PostgreSQL, FastAPI, party control, or MPyC peer ports publicly.
EOF
fi
