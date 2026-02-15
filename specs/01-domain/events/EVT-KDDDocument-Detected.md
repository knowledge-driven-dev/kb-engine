---
id: EVT-KDDDocument-Detected
kind: event
title: "KDDDocument Detected"
status: draft
---

# EVT-KDDDocument-Detected

## Descripción

Se emite cuando el pipeline de indexación descubre un fichero nuevo dentro de `/specs` que contiene front-matter válido con un `kind` KDD reconocido. Es el punto de entrada al ciclo de vida de un [[KDDDocument]].

Este evento se produce tanto durante una indexación completa (scan de todo `/specs`) como durante una indexación incremental ([[CMD-002-IndexIncremental]]) cuando `git diff` reporta un fichero nuevo.

## Payload

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `source_path` | `string` | Ruta relativa del fichero detectado (e.g. `specs/01-domain/entities/Pedido.md`) |
| `source_hash` | `string` | Hash SHA-256 del contenido del fichero |
| `kind` | `KDDKind` | Tipo de artefacto KDD detectado por [[BR-DOCUMENT-001]] |
| `layer` | `KDDLayer` | Capa KDD inferida de la ruta del fichero |
| `detected_at` | `datetime` | Timestamp de detección |

## Productor

- Pipeline de indexación local (al escanear `/specs` o procesar `git diff`)

## Consumidores

- Extractor de nodos: selecciona el extractor correcto según `kind` e inicia el parsing
- Logger de indexación: registra el fichero detectado para trazabilidad
