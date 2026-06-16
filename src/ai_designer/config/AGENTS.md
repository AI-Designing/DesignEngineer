# AGENTS.md — `src/ai_designer/config`

## Purpose

Secure configuration loading from env and YAML.

## Production role

Centralizes secrets and path resolution hooks.

## Key modules

secure_config.py

## Dependencies

python-dotenv, PyYAML

## Conventions

Never log secret values.

## Commands

grep OPPER .env.example

## Do not

Do not commit credentials.
