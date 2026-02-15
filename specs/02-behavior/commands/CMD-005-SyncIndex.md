---
id: CMD-005
kind: command
title: SyncIndex
status: draft
---

# CMD-005 — SyncIndex

## Purpose

Sincronizar los artefactos de índice (`.kdd-index/`) entre la máquina local del desarrollador y el servidor compartido. Soporta dos operaciones: **push** (subir índice local al servidor) y **pull** (descargar índice mergeado del servidor).

La sincronización se realiza a través de Git (los artefactos de índice son ficheros versionables) o mediante un endpoint dedicado del servidor, según la configuración del proyecto.

## Input

| Parameter | Type | Required | Validation |
|-----------|------|----------|------------|
| `direction` | `string` | Sí | `push` o `pull` |
| `index_path` | `string` | No | Ruta local a `.kdd-index/`. Default: `.kdd-index/` |
| `remote` | `string` | No | URL o nombre del remoto. Default: `origin` |
| `transport` | `string` | No | Método de transporte: `git` (default), `api` |

## Preconditions

- **Push**: existe un [[IndexManifest]] local válido en `index_path`.
- **Pull**: el servidor o remoto es accesible.
- **Git transport**: el repositorio tiene un remoto configurado y el usuario tiene permisos de push/pull.
- **API transport**: el endpoint del servidor está configurado y accesible.

## Postconditions

### Push
- Los artefactos de `.kdd-index/` se han subido al servidor/remoto.
- El servidor puede usar los artefactos para ejecutar [[CMD-004-MergeIndex]].
- Los datos del [[KDDDocument]] original **no** se transmiten — solo los artefactos derivados (nodos, edges, embeddings, manifest). Esto respeta [[REQ-003-Privacy]].

### Pull
- El [[IndexManifest]] mergeado se ha descargado a `index_path`.
- Los [[GraphNode|nodos]], [[GraphEdge|edges]] y [[Embedding|embeddings]] del índice mergeado están disponibles localmente.
- Las consultas de retrieval locales operan sobre el índice mergeado.

## Possible Errors

| Code | Condition | Message |
|------|-----------|---------|
| `NO_LOCAL_INDEX` | Push sin índice local | "No local index found at {index_path}" |
| `REMOTE_UNREACHABLE` | El servidor o remoto no es accesible | "Cannot reach remote: {remote}" |
| `AUTH_FAILED` | Credenciales de Git o API inválidas | "Authentication failed for remote: {remote}" |
| `PUSH_REJECTED` | El servidor rechazó el push (e.g. versión incompatible) | "Push rejected: {reason}" |
| `NO_REMOTE_INDEX` | Pull sin índice mergeado disponible en servidor | "No merged index available on remote" |
| `TRANSPORT_ERROR` | Error durante la transferencia | "Sync failed during {direction}: {detail}" |
