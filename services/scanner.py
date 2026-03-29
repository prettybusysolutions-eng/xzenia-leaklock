"""Scanning service - orchestrates CSV/Excel scanning."""
from csv_scanner import scan_csv
import uuid


def scan_file(file_bytes: bytes) -> dict:
    """Main entry point for scanning a file."""
    result = scan_csv(file_bytes)
    result['scan_id'] = result.get('scan_id', str(uuid.uuid4()))
    return result


def scan_multiple(files: list) -> dict:
    """Scan multiple files and merge results."""
    combined = {
        'scan_id': str(uuid.uuid4()),
        'rows_parsed': 0,
        'total_revenue': 0.0,
        'total_leakage': 0,
        'patterns_triggered': 0,
        'leaks': {},
        'column_mapping': {},
    }
    
    for f in files:
        result = scan_file(f)
        combined['rows_parsed'] += result.get('rows_parsed', 0)
        combined['total_revenue'] += result.get('total_revenue', 0)
        
        for leak in result.get('leaks', []):
            pname = leak.get('pattern_name', '')
            if pname not in combined['leaks'] or leak.get('amount_estimate', 0) > combined['leaks'][pname].get('amount_estimate', 0):
                combined['leaks'][pname] = leak
    
    combined['leaks'] = sorted(combined['leaks'].values(), key=lambda x: x.get('amount_estimate', 0), reverse=True)
    combined['total_leakage'] = sum(l.get('amount_estimate', 0) for l in combined['leaks'])
    combined['patterns_triggered'] = len(combined['leaks'])
    
    return combined
