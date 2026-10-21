#!/usr/bin/env bash
# Uso: scripts/preflight.sh <nó-ou-ip>
# Confere SSH, sudo sem senha, internet e GPU antes de rodar os playbooks.
set -u
host="${1:?uso: preflight.sh <nó-ou-ip>}"
ok=0
check() {
  local nome="$1"; shift
  if ssh -o BatchMode=yes -o ConnectTimeout=5 "lab-hpc@$host" "$@" >/dev/null 2>&1; then
    echo "OK    $nome"
  else
    echo "FALHA $nome"; ok=1
  fi
}
check "SSH por chave" true
check "sudo sem senha" sudo -n true
check "internet (apt)" curl -fsS --max-time 5 -o /dev/null https://archive.ubuntu.com
if ssh -o BatchMode=yes "lab-hpc@$host" nvidia-smi -L >/dev/null 2>&1; then
  echo "OK    nvidia-smi"
else
  echo "AVISO nvidia-smi ausente: nó seguirá só com CPU (ok antes de instalar o driver)"
fi
exit "$ok"
