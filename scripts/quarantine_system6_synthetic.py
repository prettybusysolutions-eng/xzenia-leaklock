#!/usr/bin/env python3
"""Quarantine known synthetic System 6 consequence cases.

Safe to run when there are no matching rows.
Marks demo/sample-derived cases as synthetic so they stay visible to operators
but never count as proof.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.db import quarantine_synthetic_cases


def main():
    updated = quarantine_synthetic_cases(source_kind_markers=['demo', 'sample', 'seed', 'test'])
    print(f'quarantined_rows={updated}')


if __name__ == '__main__':
    main()
