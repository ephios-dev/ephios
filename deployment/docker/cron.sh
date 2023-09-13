#!/bin/bash

while [ true ]; do
    echo "Running cron job"
    /usr/local/bin/python3 -m ephios run_periodic
    sleep 60
done