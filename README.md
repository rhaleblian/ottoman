# ottoman

A lightweight, file‑driven watcher daemon that monitors ComfyUI workflow files, resolves required models and inputs, and downloads missing assets. Designed for hybrid Docker + local development.

## Features
- Watches workflow directories for changes
- Parses ComfyUI workflow JSON
- Resolves model dependencies
- Downloads missing models and inputs with retry logic
- Runs cleanly in Docker or local dev

## Development
Use the included devcontainer for a fully configured environment:

    devcontainer open .

Or run locally:

    python -m daemon.daemon

## Docker
Build and run:

    docker compose up --build

The daemon code is live‑mounted for rapid iteration.

## Configuration
Edit `daemon/config.yaml` to control:
- watched directories  
- download endpoints  
- retry/backoff behavior  


