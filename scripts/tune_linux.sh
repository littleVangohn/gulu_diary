#!/usr/bin/env bash
set -euo pipefail

cat >/etc/sysctl.d/99-competition-race.conf <<'EOF'
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.core.netdev_max_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_tw_reuse = 1
EOF

sysctl --system

cat >/etc/security/limits.d/99-competition-race.conf <<'EOF'
* soft nofile 65535
* hard nofile 65535
root soft nofile 65535
root hard nofile 65535
EOF

echo "linux tuned. Re-login or restart service shell to fully apply nofile limits."
