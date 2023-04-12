#!/usr/bin/env bash

# Stop on errors
set -e

# Fires a payload at the API from a shell script

curl -X POST "http://localhost:8000/report" \
    -H "Content-Type: application/json" \
    --data-binary @test_payload.json
