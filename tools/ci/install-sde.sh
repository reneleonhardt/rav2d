#!/usr/bin/env bash
set -euo pipefail

kit=sde-external-10.13.1-2026-07-28-lin
archive="$RUNNER_TEMP/$kit.tar.xz"
curl --fail --location --retry 3 "https://downloadmirror.intel.com/924984/$kit.tar.xz" --output "$archive"
echo "94e97d623fec54385686e1e7ba65ebc9941748c05ee451423948334892bf2b50  $archive" | sha256sum --check
tar -xf "$archive" -C "$RUNNER_TEMP"
echo "$RUNNER_TEMP/$kit" >> "$GITHUB_PATH"
sudo sysctl -w kernel.yama.ptrace_scope=0
