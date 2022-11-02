#!/bin/bash

set -o nounset
set -o errexit
set -o pipefail

env -i HOME="$HOME" PATH="$PATH" \
  cyhy-commander --stdout-log ${CONTAINER_VERBOSE+--debug} ${CYHY_CONFIG_SECTION+--section=${CYHY_CONFIG_SECTION}} "$@"
