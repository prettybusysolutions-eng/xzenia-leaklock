#!/usr/bin/env python3
"""Preflight for the GitHub-first consequence loop."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.github_consequence import readiness_json


if __name__ == '__main__':
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(readiness_json(repo_dir))
