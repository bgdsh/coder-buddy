#!/bin/sh
set -eu

tries="${MPREMOTE_TRIES:-5}"
delay="${MPREMOTE_DELAY:-1}"
n=1

while :; do
  if mpremote "$@"; then
    exit 0
  fi
  if [ "$n" -ge "$tries" ]; then
    exit 1
  fi
  n=$((n + 1))
  sleep "$delay"
done
