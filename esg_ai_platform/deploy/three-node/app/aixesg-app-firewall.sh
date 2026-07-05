#!/usr/bin/env bash
set -euo pipefail

iptables -N AIXESG-APP 2>/dev/null || true
iptables -F AIXESG-APP
iptables -A AIXESG-APP -i tailscale0 -s 100.125.1.6 -p tcp -m conntrack --ctorigdst 100.72.157.21 --ctorigdstport 8020 -j RETURN
iptables -A AIXESG-APP -i tailscale0 -p tcp -m conntrack --ctorigdst 100.72.157.21 --ctorigdstport 8020 -j DROP
iptables -C DOCKER-USER -j AIXESG-APP 2>/dev/null || iptables -I DOCKER-USER 1 -j AIXESG-APP

