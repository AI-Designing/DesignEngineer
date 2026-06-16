# AGENTS.md — `tests/benchmarks`

## Purpose

FreeCAD corpus benchmarks and golden scripts.

## Production role

Regression harness for headless geometry operations.

## Key modules

corpus.yaml, test_freecad_corpus.py, golden_scripts.py

## Dependencies

FreeCAD binary on PATH or FREECAD_PATH

## Conventions

Skip when FreeCAD unavailable.

## Commands

pytest tests/benchmarks/ -v

## Do not

Do not fail CI when FreeCAD is not installed unless explicitly required.
