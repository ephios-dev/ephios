#!/bin/bash

while [ true ]; do
    echo "Running cron job"
    uv run python -m ephios run_periodic
    sleep 60
done
