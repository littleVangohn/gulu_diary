#!/usr/bin/env bash
set -euo pipefail

GO_VERSION="${GO_VERSION:-1.22.12}"
GO_TARBALL="go${GO_VERSION}.linux-amd64.tar.gz"
GO_URL="https://go.dev/dl/${GO_TARBALL}"

apt-get update
apt-get install -y curl tar redis-server redis-tools wrk python3 ca-certificates

go env -w GOPROXY=https://goproxy.cn,direct 2>/dev/null || true
go env -w GOSUMDB=sum.golang.google.cn 2>/dev/null || true

systemctl enable redis-server
systemctl restart redis-server
redis-cli ping

if ! command -v go >/dev/null 2>&1 || ! go version | grep -q "go${GO_VERSION}"; then
  curl -fsSLO "$GO_URL"
  rm -rf /usr/local/go
  tar -C /usr/local -xzf "$GO_TARBALL"
  ln -sf /usr/local/go/bin/go /usr/local/bin/go
  ln -sf /usr/local/go/bin/gofmt /usr/local/bin/gofmt
  rm -f "$GO_TARBALL"
fi

go version
go env GOPROXY
go env GOSUMDB
echo "dependencies installed"
