#!/usr/bin/env bash
# Backend: Cursor agent CLI — not enabled.
# Cursor documents `agent -p --output-format text "<prompt>"`, but no model
# flag and no way to disable tools, so a read-only, tool-free call cannot be
# guaranteed. Until those are confirmed, this backend always fails, which
# sends captures down the pending-marker path. Choose another backend with
# CALAMUS_BACKEND (for example claude or generic).
echo "cursor backend: unverified (see scripts/backends/cursor.sh)" >&2
exit 2
