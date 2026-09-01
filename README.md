# ottoman

A lightweight, file‑driven watcher daemon that monitors ComfyUI workflow files on a server instance, resolves required models and inputs, downloads missing assets, and maintains a local cache. Designed for hybrid Docker + local development.

You can save template workflows and easily obtain the models and inputs they need to run.

## Features
- Watches workflow directories for changes
- Parses ComfyUI workflow JSON
- Resolves model dependencies
- Downloads missing models and inputs with retry logic
- Maintains a persistent cache directory
- Runs cleanly in Docker or local dev

## Running
In your shell, set the environment variables that `docker-compose.yml` uses to know where your Comfy files should go.

Build and run:

    docker compose up --build

Or run locally:

    python -m daemon.daemon

## Configuration
Edit `daemon/config.yaml` to control:
- watched directories  
- cache location  
- download endpoints  
- retry/backoff behavior  

## Development
Use the included devcontainer for a fully configured environment:

    devcontainer open .

The daemon code is live‑mounted for rapid iteration.


