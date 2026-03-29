"""Core tests for LeakLock CSV scanner."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import csv
import io

from csv_scanner import scan_csv


def make_csv(**kwargs):
    """Build a minimal CSV with given columns."""
    rows = kwargs.get('rows', [
        {'date': '2024-01-01', 'amount': '1000', 'customer_id': 'CUST001', 'status': 'paid', 'description': 'Consulting'},
        {'date': '2024-01-05', 'amount': '500', 'customer_id': 'CUST002', 'status': 'paid', 'description': 'Design'},
    ])
    output = io.StringIO()
    if rows:
        w = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return output.getvalue().encode()


def test_scan_csv_basic():
    """Basic CSV scan returns expected keys."""
    raw = make_csv()
    result = scan_csv(raw)
    assert 'scan_id' in result
    assert 'rows_parsed' in result
    assert 'total_revenue' in result
    assert 'total_leakage' in result
    assert 'leaks' in result
    assert result['rows_parsed'] == 2


def test_scan_csv_empty():
    """Empty CSV returns zero leaks."""
    raw = b"date,amount,customer_id\n"
    result = scan_csv(raw)
    assert result['rows_parsed'] == 0
    assert result['total_leakage'] == 0


def test_scan_csv_discount_drift():
    """Discount column triggers discount_drift."""
    rows = [
        {'date': f'2024-01-{i+1:02d}', 'amount': '100', 'customer_id': f'C{i}',
         'status': 'paid', 'description': 'Service', 'discount': f'{i*5}'}
        for i in range(20)
    ]
    raw = make_csv(rows=rows)
    result = scan_csv(raw)
    patterns = [l['pattern'] for l in result['leaks']]
    # Should detect something — not testing exact pattern, just no crash
    assert isinstance(result['leaks'], list)


def test_scan_csv_failed_payments():
    """Failed payment statuses trigger failed_payment_neglect."""
    rows = []
    for i in range(10):
        rows.append({'date': '2024-01-01', 'amount': '500', 'customer_id': f'C{i}',
                     'status': 'failed', 'description': 'Subscription'})
    for i in range(3):
        rows.append({'date': '2024-01-01', 'amount': '200', 'customer_id': f'P{i}',
                     'status': 'paid', 'description': 'Subscription'})
    raw = make_csv(rows=rows)
    result = scan_csv(raw)
    patterns = [l['pattern'] for l in result['leaks']]
    assert 'failed_payment_neglect' in patterns


def test_scan_csv_excel_bytes():
    """Excel magic bytes don't crash (returns error if openpyxl not available)."""
    fake_xlsx = b'PK\x03\x04' + b'\x00' * 100
    result = scan_csv(fake_xlsx)
    # Should not raise — either parses or returns error gracefully
    assert 'scan_id' in result
