#!/usr/bin/env bash
set -eu

printf 'Current branch: %s\n' "$(git branch --show-current)"
printf 'HEAD commit: %s\n' "$(git rev-parse HEAD)"

if origin_url=$(git remote get-url origin 2>/dev/null); then
  printf 'Configured origin remote: %s\n' "$origin_url"
else
  printf 'Configured origin remote: (not configured)\n'
fi

if [ -n "$(git status --porcelain)" ]; then
  printf 'Status: changes\n'
else
  printf 'Status: clean\n'
fi
