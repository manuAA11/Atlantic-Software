#!/usr/bin/env bash
set -euo pipefail
multigym_xvfb=/workspace/.local/xvfb/usr/bin/Xvfb
if [ -x "$multigym_xvfb" ]; then exit 0; fi
mkdir -p /workspace/.local/apt-downloads /workspace/.local/xvfb
multigym_package=/workspace/.local/apt-downloads/xvfb_21.1.16-1.3+deb13u3_amd64.deb
multigym_retained=/workspace/.local/apt-downloads/xvfb_2%3a21.1.16-1.3+deb13u3_amd64.deb
if [ -f "$multigym_retained" ]; then
  cp "$multigym_retained" "$multigym_package"
elif [ ! -f "$multigym_package" ]; then
  curl --fail --location --retry 2 --output "$multigym_package" 'https://deb.debian.org/debian/pool/main/x/xorg-server/xvfb_21.1.16-1.3%2bdeb13u3_amd64.deb'
fi
# Checksum verified from Debian's signed APT metadata during onboarding.
printf '%s  %s\n' '365da2b6c93339f34337c434a9489bb6411a240fa47b9f49693d3091745f28c2' "$multigym_package" | sha256sum -c -
dpkg-deb -x "$multigym_package" /workspace/.local/xvfb
"$multigym_xvfb" -version 2>&1 | head -n 8 || true
