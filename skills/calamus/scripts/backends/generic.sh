#!/usr/bin/env bash
# Backend: any command. Runs CALAMUS_LLM_CMD with the prompt on stdin.
# CALAMUS_LLM_CMD is honored only from the environment or the user-level
# config file, never from a project file.
export CALAMUS_ACTIVE=1
[ -n "${CALAMUS_LLM_CMD:-}" ] || { echo "generic backend: CALAMUS_LLM_CMD is empty" >&2; exit 127; }
exec sh -c "$CALAMUS_LLM_CMD"
