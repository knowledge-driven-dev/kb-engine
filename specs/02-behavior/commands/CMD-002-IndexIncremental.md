---
id: CMD-002
kind: command
title: IndexIncremental
status: draft
---

# CMD-002 — IndexIncremental

## Purpose

Re-indexar únicamente los [[KDDDocument|documentos]] que han sido modificados, creados o eliminados desde la última indexación. La detección de cambios se basa en `git diff` contra el commit registrado en el [[IndexManifest]] (`git_commit`).

Este comando es el punto de entrada habitual para la indexación en el workflow del desarrollador, triggered típicamente por un git hook post-commit.

## Input

| Parameter | Type | Required | Validation |
|-----------|------|----------|------------|
| `index_path` | `string` | No | Ruta a `.kdd-index/`. Default: `.kdd-index/` en la raíz del repositorio |
| `base_commit` | `string` | No | Commit base para el diff. Default: `IndexManifest.git_commit` del índice existente |
| `head_commit` | `string` | No | Commit head para el diff. Default: `HEAD` |

## Preconditions

- El repositorio Git es válido y los commits referenciados existen.
- Existe un [[IndexManifest]] previo en `index_path` (para indexación incremental; si no existe, se ejecuta indexación completa).

## Postconditions

- Para cada fichero **nuevo** en el diff dentro de `/specs`: se ejecuta [[CMD-001-IndexDocument]].
- Para cada fichero **modificado** en el diff: se emite [[EVT-KDDDocument-Stale]], se eliminan los artefactos anteriores (nodo, edges, embeddings) y se re-ejecuta [[CMD-001-IndexDocument]].
- Para cada fichero **eliminado** en el diff: se emite [[EVT-KDDDocument-Deleted]] y se eliminan en cascada el [[GraphNode]], [[GraphEdge|edges]] y [[Embedding|embeddings]] asociados.
- El `git_commit` del [[IndexManifest]] se actualiza al `head_commit`.
- Las `stats` del [[IndexManifest]] reflejan los conteos actualizados.
- El tiempo total de ejecución cumple el SLO de < 2s por documento modificado ([[REQ-001-Performance]]).

## Possible Errors

| Code | Condition | Message |
|------|-----------|---------|
| `GIT_NOT_AVAILABLE` | El directorio no es un repositorio Git válido | "Not a git repository" |
| `COMMIT_NOT_FOUND` | El `base_commit` o `head_commit` no existe | "Commit not found: {commit}" |
| `NO_MANIFEST` | No hay índice previo y no se puede hacer diff incremental | "No existing index found, running full indexation" |
| `PARTIAL_FAILURE` | Algunos documentos fallaron al indexar | "Incremental indexing completed with {n} errors" |
