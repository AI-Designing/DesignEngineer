#!/bin/bash
# Wrapper script to run pytest without ROS plugin conflicts

PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest "$@" -p pytest_cov -p no:cacheprovider
