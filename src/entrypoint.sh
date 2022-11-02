#!/bin/bash

set -o nounset
set -o errexit
set -o pipefail

# ensure the permissions are set correctly
CYHY_UID="${CYHY_UID:-cyhy}"
CYHY_GID="${CYHY_GID:-cyhy}"

# skip files matching CONTAINER_PRESERVE_OWNER or already belonging to the right user and group
find /data \
  -regex "${CONTAINER_PRESERVE_OWNER:-}" -prune -or \
  "(" -user "${CYHY_UID}" -and -group "${CYHY_GID}" ")" -or \
  -exec chown "${CYHY_UID}:${CYHY_GID}" {} +

su --command "./launcher.sh $*" --group "${CYHY_GID}" "${CYHY_UID}"
