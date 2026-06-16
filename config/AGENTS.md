# AGENTS.md — `config`

## Purpose

Runtime YAML and infra configs (Redis, Prometheus).

## Production role

Mounted into Docker containers; read by app at startup.

## Key modules

config.yaml, redis.conf, prometheus.yml

## Dependencies

Env vars override YAML paths

## Conventions

No secrets in config.yaml — use .env

## Commands

docker compose config

## Do not

Do not commit machine-specific absolute paths.
