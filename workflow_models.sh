#!/usr/bin/env bash
# Given a workflow file, download the models used in it to a local directory
# specified by the user with --models-dir.
# This is useful for offline use of the workflow.

python -m daemon.workflow_models --models-dir /mnt/d/comfy/models --download "$1"
