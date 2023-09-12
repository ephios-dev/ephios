#!/bin/bash

while [ true ]; do
    sleep 60
    echo "Running cron job"
    /usr/local/bin/python3 -m ephios run_periodic
done