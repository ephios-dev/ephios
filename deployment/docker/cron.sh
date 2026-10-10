#!/bin/bash

while [ true ]; do
    echo "Running cron job"
    python -m ephios run_periodic
    sleep 60
done
