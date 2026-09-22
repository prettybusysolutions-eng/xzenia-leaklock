# Quickstart

The credential-free path runs LeakLock's public regression suite without a
Stripe account or production database.

```bash
git clone https://github.com/prettybusysolutions-eng/xzenia-leaklock.git
cd xzenia-leaklock
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt pytest
.venv/bin/python -m pytest -q
```

To start the local application, configure PostgreSQL using `.env.example`, then
run:

```bash
.venv/bin/flask --app 'app:create_app()' run --host 127.0.0.1 --port 5050
curl --fail http://127.0.0.1:5050/health
```

Passing local tests demonstrates repository behavior only. It does not prove a
settled payment, production deployment, recovered revenue, or external adoption.
