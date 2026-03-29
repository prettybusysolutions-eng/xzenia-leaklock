"""LeakLock - Backward compatibility shim.

This file maintains backward compatibility with the old single-file structure.
The actual application logic is now in app.py and modularized under routes/, services/, models/, templates/.
"""
from app import create_app

app = create_app()

# Re-export for backward compatibility
from config import HOST, PORT

if __name__ == '__main__':
    print(f"🔒 LeakLock (modular) running on http://localhost:{PORT}")
    print(f"   / → Landing page")
    print(f"   /upload → CSV scanner")
    print(f"   /results/<id> → Scan results")
    print(f"   /pricing → Pricing tiers")
    print(f"   /report/<id> → Printable PDF report")
    print(f"   /privacy → Privacy policy")
    print(f"   /terms → Terms of service")
    print(f"   /health → Health check")
    app.run(host=HOST, port=PORT, debug=False)
