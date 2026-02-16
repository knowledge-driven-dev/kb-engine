"""CMD-005 — SyncIndex command.

Synchronizes index artifacts between local machine and shared server.
Supports push (upload local) and pull (download merged).

Spec: specs/02-behavior/commands/CMD-005-SyncIndex.md
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from kdd.domain.ports import ArtifactStore, Transport

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    success: bool
    direction: str  # "push" or "pull"
    error: str | None = None


def sync_push(
    artifact_store: ArtifactStore,
    transport: Transport,
    *,
    index_path: str = ".kdd-index",
    remote: str = "origin",
) -> SyncResult:
    """Push local index artifacts to remote server (CMD-005 push).

    Privacy guarantee (REQ-003): Only transmits derived artifacts
    (.kdd-index/), never original spec content.
    """
    manifest = artifact_store.read_manifest()
    if manifest is None:
        return SyncResult(success=False, direction="push", error="NO_LOCAL_INDEX")

    try:
        transport.push(index_path, remote)
    except Exception as e:
        return SyncResult(success=False, direction="push", error=f"TRANSPORT_ERROR: {e}")

    return SyncResult(success=True, direction="push")


def sync_pull(
    transport: Transport,
    *,
    remote: str = "origin",
    target_path: str = ".kdd-index",
) -> SyncResult:
    """Pull merged index artifacts from remote server (CMD-005 pull).

    Replaces local .kdd-index/ with the merged index from the server.
    """
    try:
        transport.pull(remote, target_path)
    except Exception as e:
        return SyncResult(success=False, direction="pull", error=f"TRANSPORT_ERROR: {e}")

    return SyncResult(success=True, direction="pull")
