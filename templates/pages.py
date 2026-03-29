"""Page templates for LeakLock — Premium Dark UI."""
import json


def _csrf():
    """Get current CSRF token for embedding in forms."""
    try:
        from flask_wtf.csrf import generate_csrf
        return generate_csrf()
    except Exception:
        return ''


BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #060d1b;
  --surface: #0d1a2e;
  --surface2: #111f33;
  --border: rgba(255,255,255,0.08);
  --primary: #38bdf8;
  --primary-glow: rgba(56,189,248,0.25);
  --accent: #818cf8;
  --success: #34d399;
  --danger: #f87171;
  --warning: #fbbf24;
  --text: #f1f5f9;
  --text-2: #94a3b8;
  --text-3: #475569;
  --radius: 12px;
  --radius-lg: 20px;
}

html { scroll-behavior: smooth; }

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

/* NAV */
.nav {
  position: sticky; top: 0; z-index: 100;
  background: rgba(6,13,27,0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
  padding: 0 40px;
  height: 64px;
  display: flex; align-items: center; justify-content: space-between;
}
.nav .logo {
  font-size: 20px; font-weight: 800;
  color: var(--text); letter-spacing: -0.5px;
  text-decoration: none;
}
.nav .logo span { color: var(--primary); }
.nav-links { display: flex; align-items: center; gap: 4px; }
.nav-links a {
  color: var(--text-2); text-decoration: none; font-size: 14px;
  font-weight: 500; padding: 8px 14px; border-radius: 8px;
  transition: all 0.2s;
}
.nav-links a:hover { color: var(--text); background: rgba(255,255,255,0.06); }
.nav-links .nav-cta {
  background: var(--primary); color: #060d1b !important;
  font-weight: 700; margin-left: 8px;
}
.nav-links .nav-cta:hover { background: #7dd3fc; transform: translateY(-1px); box-shadow: 0 4px 16px var(--primary-glow); }

/* CONTAINER */
.container { max-width: 1060px; margin: 0 auto; padding: 60px 24px; }

/* BUTTONS */
.btn-primary {
  display: inline-flex; align-items: center; gap: 8px;
  background: var(--primary); color: #060d1b;
  padding: 14px 28px; border-radius: 10px;
  font-size: 15px; font-weight: 700;
  text-decoration: none; cursor: pointer; border: none;
  transition: all 0.2s; white-space: nowrap;
}
.btn-primary:hover {
  background: #7dd3fc; transform: translateY(-2px);
  box-shadow: 0 8px 24px var(--primary-glow);
}
.btn-ghost {
  display: inline-flex; align-items: center; gap: 8px;
  background: transparent; color: var(--primary);
  padding: 13px 27px; border-radius: 10px;
  font-size: 15px; font-weight: 600;
  text-decoration: none; cursor: pointer;
  border: 1px solid rgba(56,189,248,0.4);
  transition: all 0.2s;
}
.btn-ghost:hover {
  background: rgba(56,189,248,0.08); transform: translateY(-1px);
  border-color: var(--primary);
}

/* CARDS */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 28px;
  transition: border-color 0.2s, transform 0.2s, box-shadow 0.2s;
}
.card:hover {
  border-color: rgba(56,189,248,0.2);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}

/* FOOTER */
.footer {
  text-align: center; color: var(--text-3);
  font-size: 13px; padding: 40px 24px;
  border-top: 1px solid var(--border);
  margin-top: 60px;
}
.footer a { color: var(--text-3); text-decoration: none; }
.footer a:hover { color: var(--text-2); }

/* FAQ */
.faq-item {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  transition: border-color 0.2s;
}
.faq-item:hover { border-color: rgba(56,189,248,0.2); }
.faq-item summary {
  padding: 20px 24px;
  font-size: 15px; font-weight: 600; color: var(--text);
  cursor: pointer; list-style: none;
  display: flex; justify-content: space-between; align-items: center;
  user-select: none;
}
.faq-item summary::-webkit-details-marker { display: none; }
.faq-item summary::after {
  content: '+'; color: var(--primary); font-size: 20px; font-weight: 300;
  transition: transform 0.2s;
}
.faq-item[open] summary::after { transform: rotate(45deg); }
.faq-body {
  padding: 0 24px 20px;
  font-size: 14px; color: var(--text-2); line-height: 1.75;
  border-top: 1px solid var(--border);
  padding-top: 16px;
}
"""


def nav_html(active=''):
    return """<nav class="nav">
  <a href="/" class="logo">Leak<span>Lock</span></a>
  <div class="nav-links" id="nav-links">
    <a href="/">Home</a>
    <a href="/upload">Upload CSV</a>
    <a href="/pricing">Pricing</a>
    <a href="/dental">Dental</a>
    <a href="/upload" class="nav-cta">Free Scan &#8594;</a>
  </div>
  <button class="nav-burger" id="nav-burger" onclick="document.getElementById('nav-links').classList.toggle('open')" aria-label="Menu">
    <span></span><span></span><span></span>
  </button>
</nav>
<style>
.nav-burger { display: none; flex-direction: column; gap: 5px; background: none; border: none; cursor: pointer; padding: 8px; }
.nav-burger span { display: block; width: 22px; height: 2px; background: var(--text-2); border-radius: 2px; transition: all 0.2s; }
@media (max-width: 768px) {
  .nav-burger { display: flex; }
  .nav-links { display: none; position: absolute; top: 64px; left: 0; right: 0; background: rgba(6,13,27,0.98); border-bottom: 1px solid var(--border); padding: 16px; flex-direction: column; gap: 4px; }
  .nav-links.open { display: flex; }
  .nav-links a { padding: 12px 16px; }
  .nav-links .nav-cta { margin-left: 0; margin-top: 8px; text-align: center; }
}
</style>"""


def page_landing():
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LeakLock &#8212; Stop Leaving Money on the Table</title>
<style>
{BASE_CSS}

/* HERO */
.hero-wrap {{
  position: relative; overflow: hidden;
  text-align: center; padding: 100px 24px 80px;
}}
.orb {{
  position: absolute; border-radius: 50%; filter: blur(80px);
  pointer-events: none; animation: float 8s ease-in-out infinite;
}}
.orb-1 {{ width: 400px; height: 400px; background: rgba(56,189,248,0.12); top: -100px; left: -100px; }}
.orb-2 {{ width: 300px; height: 300px; background: rgba(129,140,248,0.10); bottom: -50px; right: -50px; animation-delay: -4s; }}
.orb-3 {{ width: 250px; height: 250px; background: rgba(52,211,153,0.07); top: 50%; left: 50%; transform: translate(-50%,-50%); animation-delay: -2s; }}
@keyframes float {{
  0%, 100% {{ transform: translateY(0) scale(1); }}
  50% {{ transform: translateY(-30px) scale(1.05); }}
}}
.hero-badge {{
  display: inline-flex; align-items: center; gap: 8px;
  background: rgba(56,189,248,0.1); border: 1px solid rgba(56,189,248,0.2);
  color: #7dd3fc; font-size: 13px; font-weight: 600;
  padding: 6px 16px; border-radius: 100px; margin-bottom: 28px;
  letter-spacing: 0.3px;
}}
.hero-badge .dot {{
  width: 6px; height: 6px; background: #38bdf8; border-radius: 50%;
  animation: pulse-glow 2s ease-in-out infinite;
}}
@keyframes pulse-glow {{
  0%, 100% {{ opacity: 1; box-shadow: 0 0 0 0 rgba(56,189,248,0.5); }}
  50% {{ opacity: 0.8; box-shadow: 0 0 0 6px rgba(56,189,248,0); }}
}}
.hero-title {{
  font-size: clamp(36px, 6vw, 64px); font-weight: 900; line-height: 1.1;
  letter-spacing: -2px; margin-bottom: 20px;
  background: linear-gradient(135deg, #f1f5f9 0%, #94a3b8 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}}
.hero-sub {{
  font-size: clamp(16px, 2vw, 20px); color: var(--text-2);
  max-width: 560px; margin: 0 auto 40px; line-height: 1.6;
}}
.hero-actions {{ display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; }}

/* STATS BAR */
.stats-bar {{
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px;
  background: var(--border); border: 1px solid var(--border);
  border-radius: var(--radius-lg); overflow: hidden; margin-bottom: 80px;
}}
.stat-cell {{ background: var(--surface); padding: 32px 24px; text-align: center; }}
.stat-cell .num {{
  font-size: 40px; font-weight: 900; letter-spacing: -1.5px;
  color: var(--primary);
}}
.stat-cell .lbl {{ font-size: 14px; color: var(--text-2); margin-top: 4px; font-weight: 500; }}

/* SECTION TITLES */
.section-label {{
  font-size: 12px; font-weight: 700; color: var(--primary);
  text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 12px;
}}
.section-title {{
  font-size: clamp(24px, 3vw, 36px); font-weight: 800;
  letter-spacing: -1px; margin-bottom: 12px;
}}
.section-sub {{ font-size: 16px; color: var(--text-2); margin-bottom: 40px; }}

/* STEPS */
.steps {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; position: relative; }}
.step-card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: 28px; transition: all 0.3s;
}}
.step-card:hover {{ border-color: rgba(56,189,248,0.3); transform: translateY(-4px); }}
.step-num {{
  width: 40px; height: 40px; background: rgba(56,189,248,0.1);
  border: 1px solid rgba(56,189,248,0.3); border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 800; color: var(--primary); margin-bottom: 16px;
}}
.step-title {{ font-size: 16px; font-weight: 700; margin-bottom: 8px; color: var(--text); }}
.step-body {{ font-size: 14px; color: var(--text-2); line-height: 1.6; }}

/* PATTERN TAGS */
.patterns-wrap {{ display: flex; flex-wrap: wrap; gap: 10px; }}
.ptag {{
  background: var(--surface2); border: 1px solid var(--border);
  color: var(--text-2); font-size: 13px; font-weight: 500;
  padding: 8px 16px; border-radius: 100px; transition: all 0.2s; cursor: default;
}}
.ptag:hover {{ background: rgba(56,189,248,0.1); border-color: rgba(56,189,248,0.3); color: var(--primary); }}

/* TRUST BAR */
.trust-bar {{
  display: flex; justify-content: center; gap: 32px; flex-wrap: wrap;
  padding: 20px 0; color: var(--text-3); font-size: 13px;
  border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);
  margin: 48px 0;
}}
.trust-bar span {{ display: flex; align-items: center; gap: 8px; }}

/* SECTION SPACING */
.section {{ margin-bottom: 80px; }}
</style>
</head>
<body>
{nav_html()}

<div class="hero-wrap">
  <div class="orb orb-1"></div>
  <div class="orb orb-2"></div>
  <div class="orb orb-3"></div>
  <div style="position:relative;z-index:1;">
    <div class="hero-badge"><span class="dot"></span> 15 Revenue Leak Patterns Detected</div>
    <h1 class="hero-title">Your billing data<br>is leaking. We'll<br>prove it in 60 seconds.</h1>
    <p class="hero-sub">Upload your billing export. LeakLock scans for 15 revenue leak patterns and tells you exactly what you're losing — and how to get it back. Free scan, no card required.</p>
    <div class="hero-actions">
      <a href="/upload" class="btn-primary">Start Free Scan &#8594;</a>
      <a href="#how-it-works" class="btn-ghost">See How It Works</a>
    </div>
  </div>
</div>

<div class="container">

  <div class="stats-bar">
    <div class="stat-cell">
      <div class="num" data-count data-target="15" data-suffix="">15</div>
      <div class="lbl">Leak Patterns Detected</div>
    </div>
    <div class="stat-cell">
      <div class="num" data-count data-target="40" data-prefix="$" data-suffix="K">$40K</div>
      <div class="lbl">Avg. Finding</div>
    </div>
    <div class="stat-cell">
      <div class="num" data-count data-target="90" data-suffix="%">90%</div>
      <div class="lbl">You Keep</div>
    </div>
  </div>

  <div class="section" id="how-it-works">
    <div class="section-label">Process</div>
    <h2 class="section-title">How It Works</h2>
    <p class="section-sub">Four steps from upload to recovered revenue.</p>
    <div class="steps">
      <div class="step-card">
        <div class="step-num">1</div>
        <div class="step-title">Upload</div>
        <div class="step-body">Drop in your billing CSV or Excel file. Takes 30 seconds. No signup required.</div>
      </div>
      <div class="step-card">
        <div class="step-num">2</div>
        <div class="step-title">Analyze</div>
        <div class="step-body">We scan for 15 revenue leak patterns across your entire billing history instantly.</div>
      </div>
      <div class="step-card">
        <div class="step-num">3</div>
        <div class="step-title">Review</div>
        <div class="step-body">See exactly what's leaking, how much each issue costs, and where it's happening.</div>
      </div>
      <div class="step-card">
        <div class="step-num">4</div>
        <div class="step-title">Recover</div>
        <div class="step-body">Fix it yourself and keep 90% &#8212; or let us guide you and keep 80%. No finding = no fee.</div>
      </div>
    </div>
  </div>

  <div class="trust-bar">
    <span>&#128274; SSL Encrypted</span>
    <span>&#128465;&#65039; Data Deleted After Scan</span>
    <span>&#128179; No Card Required</span>
    <span>&#9989; No Finding = No Fee</span>
  </div>

  <div class="section">
    <div class="section-label">Detection</div>
    <h2 class="section-title">15 Revenue Leak Patterns</h2>
    <p class="section-sub">Every scan checks for all of these simultaneously.</p>
    <div class="patterns-wrap">
      <span class="ptag">Duplicate Charges</span>
      <span class="ptag">Under-billing</span>
      <span class="ptag">Wrong Procedure Codes</span>
      <span class="ptag">Unrecovered Denials</span>
      <span class="ptag">Write-offs Too High</span>
      <span class="ptag">Missing Modifiers</span>
      <span class="ptag">Untimely Filing</span>
      <span class="ptag">Coordination of Benefits</span>
      <span class="ptag">Fee Schedule Mismatch</span>
      <span class="ptag">Bundling Violations</span>
      <span class="ptag">Upcoding</span>
      <span class="ptag">Downcoding</span>
      <span class="ptag">Payer Mix Errors</span>
      <span class="ptag">Refund Due</span>
      <span class="ptag">Contract Leakage</span>
    </div>
  </div>

  <div class="section">
    <div class="section-label">Common Questions</div>
    <h2 class="section-title">FAQ</h2>
    <div style="display:flex;flex-direction:column;gap:2px;max-width:720px;">
      <details class="faq-item">
        <summary>Is my billing data safe?</summary>
        <div class="faq-body">Yes. Your CSV is processed in memory and deleted immediately after the scan completes. We never store your raw billing data. Results (pattern findings only) are retained for up to 30 days so you can return to them.</div>
      </details>
      <details class="faq-item">
        <summary>What file formats do you accept?</summary>
        <div class="faq-body">CSV, Excel (.xlsx, .xls), and TSV files up to 100MB. We auto-detect columns — no template required. Export your billing file directly from your practice management software.</div>
      </details>
      <details class="faq-item">
        <summary>What if you don't find anything?</summary>
        <div class="faq-body">You pay nothing. LeakLock only charges a percentage of what we actually find. No finding, no fee — ever. The scan itself is always free.</div>
      </details>
      <details class="faq-item">
        <summary>What's the difference between Self-Serve and Done-With-You?</summary>
        <div class="faq-body">Self-Serve: you get the full report and fix it yourself — you keep 90% of recovered revenue and pay 10% to us. Done-With-You: one of our billing specialists walks you through recovery step by step — you keep 80%, we take 20%.</div>
      </details>
    </div>
  </div>

  <div style="background: linear-gradient(135deg, var(--surface) 0%, var(--surface2) 100%); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 56px; text-align: center;">
    <div class="section-label" style="margin-bottom:16px;">Get Started Free</div>
    <h2 style="font-size:clamp(24px,4vw,40px);font-weight:900;letter-spacing:-1px;margin-bottom:12px;">Ready to Find Your Leaks?</h2>
    <p style="color:var(--text-2);font-size:16px;margin-bottom:32px;max-width:480px;margin-left:auto;margin-right:auto;">Upload your billing data now. Free scan, no card, no signup required. Results in under 60 seconds.</p>
    <a href="/upload" class="btn-primary" style="font-size:16px;padding:16px 36px;">Start Free Scan &#8594;</a>
  </div>

</div>

<div class="footer">
  LeakLock &#169; 2026 &#8212; Revenue Leak Detection
  &bull; <a href="/privacy">Privacy</a>
  &bull; <a href="/terms">Terms</a>
  &bull; <a href="/dental">Dental Practices</a>
</div>

<script>
function animateCount(el, target, prefix, suffix, duration) {{
  prefix = prefix || '';
  suffix = suffix || '';
  duration = duration || 1500;
  var start = Date.now();
  function update() {{
    var elapsed = Date.now() - start;
    var progress = Math.min(elapsed / duration, 1);
    var eased = 1 - Math.pow(1 - progress, 3);
    var current = Math.round(eased * target);
    el.textContent = prefix + current.toLocaleString() + suffix;
    if (progress < 1) requestAnimationFrame(update);
  }}
  update();
}}

var observer = new IntersectionObserver(function(entries) {{
  entries.forEach(function(e) {{
    if (e.isIntersecting) {{
      var el = e.target;
      animateCount(el, parseInt(el.dataset.target), el.dataset.prefix, el.dataset.suffix);
      observer.unobserve(el);
    }}
  }});
}}, {{ threshold: 0.3 }});

document.querySelectorAll('[data-count]').forEach(function(el) {{ observer.observe(el); }});
</script>
</body>
</html>"""


def page_upload(error=None):
    error_html = f'<div style="background:rgba(248,113,113,0.1);border:1px solid rgba(248,113,113,0.3);color:var(--danger);padding:14px 18px;border-radius:10px;margin-bottom:24px;font-size:14px;">{error}</div>' if error else ''
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LeakLock &#8212; Upload Your Billing Data</title>
<style>
{BASE_CSS}

.upload-layout {{ display: grid; grid-template-columns: 1fr 380px; gap: 40px; align-items: start; }}
.upload-form-card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: 40px;
}}
.upload-title {{ font-size: 28px; font-weight: 800; margin-bottom: 8px; letter-spacing: -0.5px; }}
.upload-sub {{ color: var(--text-2); font-size: 15px; margin-bottom: 32px; }}
.form-group {{ margin-bottom: 24px; }}
.form-label {{
  font-size: 13px; font-weight: 600; color: var(--text-2);
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; display: block;
}}
.form-input {{
  width: 100%; padding: 14px 16px; border-radius: 10px;
  border: 1px solid var(--border); background: rgba(255,255,255,0.04);
  color: var(--text); font-size: 15px; outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  font-family: inherit;
}}
.form-input:focus {{ border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-glow); }}
.dropzone {{
  border: 2px dashed var(--border); border-radius: var(--radius);
  padding: 48px 24px; text-align: center; cursor: pointer;
  transition: all 0.3s; position: relative; background: transparent;
}}
.dropzone.drag-over {{
  border-color: var(--primary); box-shadow: 0 0 0 4px var(--primary-glow);
  background: rgba(56,189,248,0.05);
}}
.dropzone-icon {{ font-size: 40px; margin-bottom: 12px; }}
.dropzone-text {{ font-size: 15px; font-weight: 600; color: var(--text-2); margin-bottom: 4px; }}
.dropzone-sub {{ font-size: 13px; color: var(--text-3); }}
.file-selected {{ font-size: 13px; color: var(--primary); margin-top: 8px; font-weight: 600; }}
.progress-bar {{
  height: 4px; background: var(--border); border-radius: 2px;
  margin-top: 20px; overflow: hidden; display: none;
}}
.progress-fill {{
  height: 100%;
  background: linear-gradient(90deg, var(--primary), var(--accent), var(--primary));
  border-radius: 2px; width: 30%;
  animation: shimmer-progress 1.5s linear infinite;
  background-size: 200% 100%;
}}
@keyframes shimmer-progress {{
  0% {{ background-position: 200% 0; }}
  100% {{ background-position: -200% 0; }}
}}
.submit-btn {{
  width: 100%; padding: 16px; background: var(--primary); color: #060d1b;
  border: none; border-radius: 10px; font-size: 16px; font-weight: 700;
  cursor: pointer; transition: all 0.2s; font-family: inherit;
  display: flex; align-items: center; justify-content: center; gap: 10px;
}}
.submit-btn:hover {{ background: #7dd3fc; transform: translateY(-1px); box-shadow: 0 6px 20px var(--primary-glow); }}
.submit-btn:disabled {{ opacity: 0.6; cursor: not-allowed; transform: none; }}
.spinner {{
  width: 18px; height: 18px; border: 2px solid rgba(6,13,27,0.3);
  border-top-color: #060d1b; border-radius: 50%;
  animation: spin 0.8s linear infinite; display: none;
}}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}

/* INFO PANEL */
.info-panel {{ position: sticky; top: 80px; }}
.info-card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: 28px; margin-bottom: 16px;
}}
.info-card h3 {{ font-size: 16px; font-weight: 700; margin-bottom: 16px; }}
.pattern-row {{
  display: flex; align-items: center; gap: 10px;
  padding: 10px 0; border-bottom: 1px solid var(--border); font-size: 14px;
  color: var(--text-2);
}}
.pattern-row:last-child {{ border-bottom: none; }}
.pattern-dot {{
  width: 8px; height: 8px; background: var(--primary);
  border-radius: 50%; flex-shrink: 0;
}}
.badge-row {{
  display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px;
}}
.badge-sm {{
  background: var(--surface2); border: 1px solid var(--border);
  color: var(--text-3); font-size: 12px; padding: 4px 10px;
  border-radius: 100px; font-weight: 500;
}}

/* CONNECT BUTTONS */
.connect-btn {{
  display: flex; align-items: center; gap: 10px;
  padding: 12px 16px; border-radius: 10px;
  background: rgba(255,255,255,0.04); border: 1px solid var(--border);
  color: var(--text); text-decoration: none; font-size: 14px; font-weight: 600;
  transition: all 0.2s;
}}
.connect-btn:hover {{
  background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.15);
  transform: translateX(3px);
}}
</style>
</head>
<body>
{nav_html()}
<div class="container">
<div class="upload-layout">
  <div>
    <div class="upload-form-card">
      <h1 class="upload-title">Upload Your Billing Data</h1>
      <p class="upload-sub">We scan for 15 revenue leak patterns. Your data is deleted immediately after scanning.</p>
      {error_html}
      <form method="POST" enctype="multipart/form-data" id="upload-form">
        <input type="hidden" name="csrf_token" value="{_csrf()}">
        <div class="form-group">
          <label class="form-label">&#128274; Email Address</label>
          <input type="email" name="email" class="form-input" placeholder="you@practice.com" required>
        </div>
        <div class="form-group">
          <label class="form-label">Billing File</label>
          <div class="dropzone" id="dropzone">
            <div class="dropzone-icon">&#128196;</div>
            <div class="dropzone-text">Drop your file here, or click to browse</div>
            <div class="dropzone-sub">CSV, Excel (.xlsx), or TSV</div>
            <div class="file-selected" id="file-name" style="display:none;"></div>
          </div>
          <input type="file" name="files" id="file-input" accept=".csv,.xlsx,.xls,.tsv" multiple style="display:none;">
        </div>
        <button type="submit" class="submit-btn" id="submit-btn">
          <span class="spinner" id="spinner"></span>
          <span id="btn-text">Find My Revenue Leaks &#8594;</span>
        </button>
        <div style="display:flex;align-items:center;justify-content:center;gap:16px;margin-top:14px;font-size:12px;color:var(--text-3);">
          <span>&#128274; SSL Encrypted</span>
          <span>&#128465; CSV deleted immediately after scan</span>
          <span>&#9989; No card required</span>
        </div>
      </form>
      <div class="progress-bar" id="progress-bar"></div>
      <div class="progress-bar" id="progress-bar2">
        <div class="progress-fill"></div>
      </div>
      <p style="text-align:center;margin-top:16px;font-size:13px;color:var(--text-3);">
        <a href="/sample" style="color:var(--primary);text-decoration:none;">&#9654; Try with Sample Data</a>
        &nbsp;&bull;&nbsp;
        <a href="/sample" style="color:var(--text-3);text-decoration:none;">Download Sample CSV</a>
      </p>
    </div>

    <div style="margin-top:20px;background:linear-gradient(135deg,rgba(99,91,255,0.1),rgba(56,189,248,0.08));border:1px solid rgba(99,91,255,0.25);border-radius:var(--radius-lg);padding:28px;text-align:center;">
      <div style="font-size:22px;margin-bottom:8px;">💳</div>
      <div style="font-size:17px;font-weight:700;margin-bottom:6px;">Have a Stripe account?</div>
      <div style="font-size:14px;color:var(--text-2);margin-bottom:18px;">Skip the upload. We pull directly from Stripe and run the full scan in seconds.</div>
      <a href="/scan/stripe-direct" class="btn-primary" style="font-size:15px;padding:14px 32px;">Scan My Stripe Account Now &#8594;</a>
      <div style="font-size:12px;color:var(--text-3);margin-top:10px;">Read-only. No write access. Results in under 10 seconds.</div>
    </div>
  </div>

  <div class="info-panel">
    <div class="info-card" style="margin-bottom:16px;">
      <h3 style="margin-bottom:16px;">Connect Your Account</h3>
      <p style="font-size:13px;color:var(--text-2);margin-bottom:16px;">Skip the upload &#8212; connect directly and we pull your data automatically.</p>
      <div style="display:flex;flex-direction:column;gap:8px;">
        <a href="/connect/quickbooks" class="connect-btn" style="--c:#2CA01C;">
          <span>📒</span> Connect QuickBooks
        </a>
        <a href="/connect/stripe" class="connect-btn" style="--c:#635BFF;">
          <span>💳</span> Connect Stripe
        </a>
        <a href="/connect/square" class="connect-btn" style="--c:#3E4348;">
          <span>⬛</span> Connect Square
        </a>
        <a href="/connect/xero" class="connect-btn" style="--c:#13B5EA;">
          <span>🔷</span> Connect Xero
        </a>
        <a href="/connect/freshbooks" class="connect-btn" style="--c:#1DB65D;">
          <span>📗</span> Connect FreshBooks
        </a>
      </div>
      <p style="font-size:11px;color:var(--text-3);margin-top:12px;">Read-only access. Disconnect anytime.</p>
    </div>
    <div class="info-card">
      <h3>What We Scan For</h3>
      <div class="badge-row">
        <span class="badge-sm">Up to 100MB</span>
        <span class="badge-sm">CSV / Excel / TSV</span>
        <span class="badge-sm">Instant Results</span>
      </div>
      <div class="pattern-row"><div class="pattern-dot"></div> Duplicate Charges</div>
      <div class="pattern-row"><div class="pattern-dot"></div> Wrong Procedure Codes</div>
      <div class="pattern-row"><div class="pattern-dot"></div> Unrecovered Denials</div>
      <div class="pattern-row"><div class="pattern-dot"></div> Write-off Errors</div>
      <div class="pattern-row"><div class="pattern-dot"></div> Fee Schedule Mismatches</div>
      <div class="pattern-row"><div class="pattern-dot"></div> + 10 More Patterns</div>
    </div>
    <div class="info-card" style="background:rgba(56,189,248,0.05);border-color:rgba(56,189,248,0.15);">
      <h3 style="color:var(--primary);">&#9989; No Finding = No Fee</h3>
      <p style="font-size:14px;color:var(--text-2);line-height:1.6;">The scan is always free. You only pay if we find revenue leaks &#8212; and only on what we recover.</p>
    </div>
  </div>
</div>
</div>

<div class="footer">
  LeakLock &#169; 2026 &bull; <a href="/privacy">Privacy</a> &bull; <a href="/terms">Terms</a>
</div>

<script>
var dropzone = document.getElementById('dropzone');
var fileInput = document.getElementById('file-input');
var form = document.getElementById('upload-form');
var progressBar = document.getElementById('progress-bar2');
var submitBtn = document.getElementById('submit-btn');
var spinner = document.getElementById('spinner');
var btnText = document.getElementById('btn-text');
var fileName = document.getElementById('file-name');

dropzone.addEventListener('click', function() {{ fileInput.click(); }});

dropzone.addEventListener('dragover', function(e) {{
  e.preventDefault();
  dropzone.classList.add('drag-over');
}});
dropzone.addEventListener('dragleave', function() {{
  dropzone.classList.remove('drag-over');
}});
dropzone.addEventListener('drop', function(e) {{
  e.preventDefault();
  dropzone.classList.remove('drag-over');
  fileInput.files = e.dataTransfer.files;
  updateFileName();
}});

fileInput.addEventListener('change', updateFileName);

function updateFileName() {{
  if (fileInput.files.length > 0) {{
    fileName.textContent = '&#10003; ' + fileInput.files[0].name;
    fileName.style.display = 'block';
    dropzone.querySelector('.dropzone-text').style.display = 'none';
    dropzone.querySelector('.dropzone-sub').style.display = 'none';
  }}
}}

form.addEventListener('submit', function(e) {{
  if (!fileInput.files.length) {{
    e.preventDefault();
    dropzone.style.borderColor = 'var(--danger)';
    dropzone.querySelector('.dropzone-text').textContent = 'Please select a file first';
    return;
  }}
  submitBtn.disabled = true;
  spinner.style.display = 'block';
  btnText.textContent = 'Scanning...';
  progressBar.style.display = 'block';
}});
</script>
</body>
</html>"""


def page_results(scan):
    leaks = scan.get('leaks', [])
    total_revenue = scan.get('total_revenue', 0)
    total_leakage = scan.get('total_leakage', 0)
    rows_parsed = scan.get('rows_parsed', 0)
    patterns_triggered = scan.get('patterns_triggered', 0)
    scan_id = scan.get('scan_id', '')

    # Revenue Health Score
    leak_pct = (total_leakage / total_revenue * 100) if total_revenue else 0
    health_score = max(0, min(100, int(100 - leak_pct * 1.5)))
    if health_score >= 80:
        score_color = 'var(--success)'
        score_label = 'Healthy'
    elif health_score >= 50:
        score_color = 'var(--warning)'
        score_label = 'At Risk'
    else:
        score_color = 'var(--danger)'
        score_label = 'Critical'

    source = scan.get('source', '')
    account_name = scan.get('account_name', '')
    source_badge = ''
    if source == 'stripe_direct' and account_name:
        source_badge = f'<div style="display:inline-flex;align-items:center;gap:8px;background:rgba(99,91,255,0.12);border:1px solid rgba(99,91,255,0.3);color:#a78bfa;font-size:13px;font-weight:600;padding:6px 14px;border-radius:100px;margin-bottom:20px;">💳 {account_name}</div>'

    leaks_html = ''
    for leak in leaks:
        sev = leak.get('severity', 'medium')
        det = leak.get('details', {})
        if isinstance(det, str):
            try:
                det = json.loads(det)
            except Exception:
                det = {}
        pattern_name = leak.get('pattern_name') or det.get('pattern_name') or leak.get('pattern', '').replace('_', ' ').title()
        description = leak.get('description') or det.get('description') or ''
        how_to_fix = leak.get('how_to_fix', '')
        amt = leak.get('amount_estimate', 0)
        sev_icon = '🔴' if sev == 'high' else '🟡' if sev == 'medium' else '🔵'
        severity_label = 'Critical' if sev == 'high' else 'Medium' if sev == 'medium' else 'Low'
        amt_display = f'${amt:,.0f}' if amt else 'Review'
        fix_html = f'<div class="leak-fix"><strong>How to fix:</strong> {how_to_fix}</div>' if how_to_fix else ''

        leaks_html += f"""<div class="leak-card">
          <div class="leak-bar {sev}"></div>
          <div>
            <div class="leak-name">{sev_icon} {pattern_name}</div>
            <div class="leak-desc">{description}</div>
            {fix_html}
            <span class="leak-sev sev-{sev}">{severity_label}</span>
          </div>
          <div class="leak-amount">{amt_display}</div>
        </div>"""

    if not leaks_html:
        leaks_html = '<div style="text-align:center;padding:56px;color:var(--text-3);"><div style="font-size:48px;margin-bottom:16px;">&#9989;</div><div style="font-size:18px;font-weight:700;color:var(--text-2);">No significant leaks detected</div><p style="margin-top:8px;">Your billing looks clean! No revenue leaks found in this dataset.</p></div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LeakLock &#8212; Scan Results</title>
<style>
{BASE_CSS}

.results-hero {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: 40px; margin-bottom: 32px;
}}
.results-title {{ font-size: 22px; font-weight: 700; margin-bottom: 28px; color: var(--text-2); }}
.results-stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }}
.rstat {{ text-align: center; }}
.rstat .val {{ font-size: 32px; font-weight: 900; letter-spacing: -1px; }}
.rstat .val.danger {{ color: var(--danger); }}
.rstat .val.primary {{ color: var(--primary); }}
.rstat .lbl {{ font-size: 12px; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }}
.leaks-section-title {{
  font-size: 18px; font-weight: 700; margin-bottom: 16px;
  display: flex; align-items: center; gap: 12px;
}}
.leak-count-badge {{
  background: rgba(248,113,113,0.15); color: var(--danger);
  font-size: 13px; font-weight: 700; padding: 3px 10px; border-radius: 100px;
}}
.leak-card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 20px 24px;
  display: grid; grid-template-columns: 4px 1fr auto;
  gap: 20px; align-items: center; margin-bottom: 12px; transition: all 0.2s;
}}
.leak-card:hover {{ transform: translateX(4px); border-color: rgba(255,255,255,0.12); }}
.leak-bar {{ width: 4px; height: 100%; border-radius: 4px; min-height: 48px; align-self: stretch; }}
.leak-bar.high {{ background: var(--danger); }}
.leak-bar.medium {{ background: var(--warning); }}
.leak-bar.low {{ background: var(--success); }}
.leak-name {{ font-size: 16px; font-weight: 700; margin-bottom: 4px; }}
.leak-desc {{ font-size: 13px; color: var(--text-2); }}
.leak-sev {{ font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 100px; display: inline-block; margin-top: 6px; }}
.sev-high {{ background: rgba(248,113,113,0.15); color: var(--danger); }}
.sev-medium {{ background: rgba(251,191,36,0.15); color: var(--warning); }}
.sev-low {{ background: rgba(52,211,153,0.15); color: var(--success); }}
.leak-amount {{ font-size: 22px; font-weight: 800; color: var(--danger); white-space: nowrap; }}
.recovery-cta {{
  background: linear-gradient(135deg, #0d1a2e 0%, #111f33 100%);
  border: 1px solid var(--border); border-radius: var(--radius-lg);
  padding: 48px; text-align: center; margin-top: 32px;
}}
.recovery-cta h2 {{ font-size: 28px; font-weight: 800; margin-bottom: 8px; letter-spacing: -0.5px; }}
.recovery-cta .sub {{ color: var(--text-2); margin-bottom: 40px; font-size: 16px; }}
.recovery-options {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; max-width: 600px; margin: 0 auto 32px; }}
.recovery-option {{
  background: rgba(255,255,255,0.03); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 24px; transition: all 0.2s; text-align: left;
}}
.recovery-option:hover {{ border-color: rgba(56,189,248,0.3); background: rgba(56,189,248,0.05); }}
.recovery-option .fee {{ font-size: 32px; font-weight: 900; color: var(--primary); }}
.recovery-option .tier-name {{ font-size: 14px; font-weight: 700; margin: 8px 0 4px; color: var(--text); }}
.recovery-option .tier-desc {{ font-size: 13px; color: var(--text-2); line-height: 1.5; }}
.email-inline {{
  background: rgba(255,255,255,0.03); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 20px; display: flex;
  align-items: center; gap: 12px; max-width: 480px; margin: 0 auto;
}}
.email-inline input {{
  flex: 1; padding: 12px 16px; border-radius: 8px;
  border: 1px solid var(--border); background: rgba(255,255,255,0.06);
  color: var(--text); font-size: 14px; outline: none;
  transition: border-color 0.2s; font-family: inherit;
}}
.email-inline input:focus {{ border-color: var(--primary); }}
.email-inline button {{
  padding: 12px 20px; background: var(--surface2); color: var(--text-2);
  border: 1px solid var(--border); border-radius: 8px; font-size: 14px;
  font-weight: 600; cursor: pointer; white-space: nowrap;
  transition: all 0.2s; font-family: inherit;
}}
.email-inline button:hover {{ color: var(--text); border-color: rgba(255,255,255,0.2); }}
.actions-row {{
  display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; margin-bottom: 16px;
}}
.leak-fix {{
  font-size: 13px; color: var(--success); margin-top: 8px; line-height: 1.5;
  background: rgba(52,211,153,0.07); border-radius: 6px; padding: 8px 12px;
}}
.scan-again-bar {{
  display: flex; gap: 12px; justify-content: flex-end; flex-wrap: wrap;
  margin-bottom: 24px;
}}
@media (max-width: 640px) {{
  .results-stats {{ grid-template-columns: repeat(2, 1fr); }}
  .recovery-options {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
{nav_html()}
<div class="container">

  <div class="results-hero">
    <div class="results-title">&#128202; Scan Complete &#8212; {rows_parsed:,} transactions analyzed</div>
    {source_badge}
    <div style="display:flex;align-items:center;gap:32px;margin-bottom:28px;flex-wrap:wrap;">
      <div style="text-align:center;">
        <div style="font-size:64px;font-weight:900;letter-spacing:-3px;color:{score_color};line-height:1;">{health_score}</div>
        <div style="font-size:13px;color:var(--text-3);text-transform:uppercase;letter-spacing:0.5px;margin-top:4px;">Revenue Health Score</div>
        <div style="font-size:14px;font-weight:700;color:{score_color};margin-top:2px;">{score_label}</div>
      </div>
      <div style="flex:1;min-width:200px;">
        <div style="height:8px;background:rgba(255,255,255,0.06);border-radius:100px;overflow:hidden;">
          <div style="width:{health_score}%;height:100%;background:{score_color};border-radius:100px;transition:width 1s ease;"></div>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-3);margin-top:4px;"><span>Critical</span><span>Healthy</span></div>
      </div>
    </div>
    <div class="results-stats">
      <div class="rstat">
        <div class="val primary">${total_revenue:,.0f}</div>
        <div class="lbl">Revenue Analyzed</div>
      </div>
      <div class="rstat">
        <div class="val danger">${total_leakage:,.0f}</div>
        <div class="lbl">Leaked Revenue</div>
      </div>
      <div class="rstat">
        <div class="val primary">{patterns_triggered}</div>
        <div class="lbl">Patterns Triggered</div>
      </div>
      <div class="rstat">
        <div class="val">{len(leaks)}</div>
        <div class="lbl">Issues Found</div>
      </div>
    </div>
  </div>

  <div class="scan-again-bar">
    <a href="/upload" class="btn-ghost" style="font-size:13px;padding:9px 18px;">&#8593; Scan Another File</a>
    <a href="/scan/stripe-direct" class="btn-ghost" style="font-size:13px;padding:9px 18px;">💳 Re-scan Stripe</a>
    <a href="/report/{scan_id}" class="btn-ghost" style="font-size:13px;padding:9px 18px;">&#128196; Download PDF</a>
  </div>

  <div class="leaks-section-title">
    Detected Leak Patterns
    <span class="leak-count-badge">{len(leaks)} issues</span>
  </div>

  {leaks_html}

  <div class="recovery-cta">
    <h2>Recover This Revenue</h2>
    <p class="sub">Choose how you want to fix it. You only pay on what we recover.</p>

    <div class="recovery-options">
      <div class="recovery-option">
        <div class="fee">10%</div>
        <div class="tier-name">Self-Serve Recovery</div>
        <div class="tier-desc">Get the full playbook. Fix it yourself with step-by-step guidance. Keep 90% of everything recovered.</div>
        <a href="/checkout/self-serve?scan_id={scan_id}" class="btn-primary" style="margin-top:16px;width:100%;justify-content:center;">Get the Playbook</a>
      </div>
      <div class="recovery-option">
        <div class="fee">20%</div>
        <div class="tier-name">Done-With-You</div>
        <div class="tier-desc">Our team walks you through every fix. We handle the hard parts. Keep 80% of everything recovered.</div>
        <a href="/checkout/done-with-you?scan_id={scan_id}" class="btn-primary" style="margin-top:16px;width:100%;justify-content:center;background:var(--accent);">Work With Us</a>
      </div>
    </div>

    <p style="color:var(--text-3);font-size:13px;margin-bottom:24px;">No finding = no fee. Results expire in 30 days.</p>

    <form method="POST" action="/api/save-results">
      <input type="hidden" name="csrf_token" value="{_csrf()}">
      <input type="hidden" name="scan_id" value="{scan_id}">
      <div class="email-inline">
        <span style="font-size:13px;color:var(--text-3);white-space:nowrap;">&#128233; Email results</span>
        <input type="email" name="email" placeholder="you@practice.com" required>
        <button type="submit">Save</button>
      </div>
    </form>
  </div>

</div>
<div class="footer">
  LeakLock &#169; 2026 &bull; <a href="/privacy">Privacy</a> &bull; <a href="/terms">Terms</a>
</div>
</body>
</html>"""


def page_pricing():
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LeakLock &#8212; Pricing</title>
<style>
{BASE_CSS}

.pricing-hero {{ text-align: center; padding: 80px 24px 60px; }}
.pricing-hero h1 {{
  font-size: clamp(40px, 6vw, 72px); font-weight: 900; letter-spacing: -2.5px;
  background: linear-gradient(135deg, #f1f5f9 20%, #38bdf8 80%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  margin-bottom: 16px;
}}
.pricing-hero .sub {{ font-size: 18px; color: var(--text-2); max-width: 480px; margin: 0 auto; }}

.guardian-featured {{
  background: linear-gradient(135deg, rgba(124,58,237,0.15) 0%, rgba(56,189,248,0.1) 100%);
  border: 1px solid rgba(124,58,237,0.4);
  border-radius: var(--radius-lg); padding: 48px; text-align: center;
  margin-bottom: 48px; position: relative; overflow: hidden;
}}
.guardian-featured::before {{
  content: ''; position: absolute; top: -50%; left: -50%;
  width: 200%; height: 200%;
  background: radial-gradient(circle, rgba(124,58,237,0.12) 0%, transparent 60%);
  pointer-events: none;
}}
.guardian-featured .label {{
  display: inline-block;
  background: linear-gradient(90deg, #7c3aed, #38bdf8); color: white;
  font-size: 12px; font-weight: 700; padding: 4px 16px; border-radius: 100px;
  margin-bottom: 20px; letter-spacing: 0.5px; text-transform: uppercase;
}}
.guardian-featured h2 {{ font-size: 32px; font-weight: 800; margin-bottom: 8px; position: relative; }}
.guardian-featured .price {{
  font-size: 64px; font-weight: 900; letter-spacing: -2px;
  background: linear-gradient(90deg, #7c3aed, #38bdf8);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  position: relative;
}}
.guardian-featured .price-sub {{ color: var(--text-2); font-size: 16px; margin-bottom: 20px; position: relative; }}
.guardian-featured .desc {{ color: var(--text-2); font-size: 15px; max-width: 480px; margin: 0 auto 28px; position: relative; line-height: 1.6; }}

.tier-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-bottom: 60px; }}
.tier-card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: 32px;
}}
.tier-card.featured {{
  border-color: rgba(56,189,248,0.4);
  background: linear-gradient(135deg, rgba(56,189,248,0.05), var(--surface));
}}
.tier-name {{ font-size: 18px; font-weight: 700; margin-bottom: 8px; }}
.tier-price {{ font-size: 40px; font-weight: 900; letter-spacing: -1px; margin: 12px 0 4px; }}
.tier-price .per {{ font-size: 16px; font-weight: 400; color: var(--text-2); }}
.tier-desc {{
  font-size: 14px; color: var(--text-2); padding-bottom: 20px;
  margin-bottom: 20px; border-bottom: 1px solid var(--border); line-height: 1.5;
}}
.tier-features {{ list-style: none; margin-bottom: 28px; }}
.tier-features li {{
  font-size: 14px; color: var(--text-2); padding: 6px 0;
  display: flex; gap: 8px; align-items: flex-start;
}}
.tier-features li::before {{ content: '\\2713'; color: var(--success); font-weight: 700; flex-shrink: 0; margin-top: 1px; }}

.perf-section {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: 48px; margin-bottom: 48px;
}}
.perf-section h2 {{ font-size: 26px; font-weight: 800; margin-bottom: 4px; letter-spacing: -0.5px; }}
.perf-section .perf-sub {{ font-size: 15px; color: var(--text-2); margin-bottom: 32px; }}
.calc-row {{
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 0; border-bottom: 1px solid var(--border); font-size: 15px;
  color: var(--text-2);
}}
.calc-row:last-child {{ border-bottom: none; font-weight: 800; font-size: 18px; color: var(--success); }}
.calc-row .calc-label {{ font-weight: 500; }}
.calc-row .calc-val {{ font-weight: 700; color: var(--text); }}
.calc-row:last-child .calc-val {{ color: var(--success); }}

/* FAQ */
.faq-section {{ margin-bottom: 60px; }}
.faq-section h2 {{ font-size: 26px; font-weight: 800; margin-bottom: 24px; letter-spacing: -0.5px; }}
.faq-item {{
  border: 1px solid var(--border); border-radius: var(--radius);
  margin-bottom: 8px; overflow: hidden;
}}
.faq-question {{
  padding: 18px 24px; font-size: 15px; font-weight: 600;
  cursor: pointer; display: flex; justify-content: space-between;
  align-items: center; background: var(--surface);
  transition: background 0.2s;
}}
.faq-question:hover {{ background: var(--surface2); }}
.faq-chevron {{ transition: transform 0.2s; color: var(--text-3); }}
.faq-answer {{
  padding: 0 24px; max-height: 0; overflow: hidden;
  transition: max-height 0.3s ease, padding 0.3s;
  font-size: 14px; color: var(--text-2); line-height: 1.7;
}}
.faq-item.open .faq-answer {{ max-height: 200px; padding: 16px 24px; }}
.faq-item.open .faq-chevron {{ transform: rotate(180deg); }}
</style>
</head>
<body>
{nav_html()}
<div class="container">

  <div class="pricing-hero">
    <h1>No Finding. No Fee.</h1>
    <p class="sub">The scan is always free. You only pay when we find something &#8212; on what you actually recover.</p>
  </div>

  <div class="guardian-featured">
    <div class="label">&#11088; Most Popular</div>
    <h2>LeakLock Guardian</h2>
    <div class="price">$349<span style="font-size:24px;font-weight:400;">/mo</span></div>
    <div class="price-sub">Continuous monitoring. New leaks found every month.</div>
    <div class="desc">Guardian runs monthly scans on your billing data, catches new leaks as they appear, and sends you a recovery report with everything you need to fix it.</div>
    <a href="/checkout/guardian" class="btn-primary" style="font-size:16px;padding:16px 40px;">Start Guardian &#8594;</a>
  </div>

  <div class="tier-grid">
    <div class="tier-card">
      <div class="tier-name">Self-Serve Recovery</div>
      <div class="tier-price">10%<span class="per"> of recovered</span></div>
      <div class="tier-desc">You get the full playbook and fix it yourself. Keep 90% of everything recovered.</div>
      <ul class="tier-features">
        <li>Full scan report</li>
        <li>Step-by-step recovery guide</li>
        <li>All 15 leak patterns</li>
        <li>PDF export</li>
        <li>No finding = no fee</li>
      </ul>
      <a href="/upload" class="btn-ghost" style="width:100%;justify-content:center;">Start Free Scan</a>
    </div>
    <div class="tier-card featured">
      <div class="tier-name">Done-With-You Recovery</div>
      <div class="tier-price">20%<span class="per"> of recovered</span></div>
      <div class="tier-desc">Our team walks you through every fix. We handle the hard parts. Keep 80% of everything recovered.</div>
      <ul class="tier-features">
        <li>Everything in Self-Serve</li>
        <li>Guided recovery sessions</li>
        <li>Specialist support</li>
        <li>We handle the hard parts</li>
        <li>No finding = no fee</li>
      </ul>
      <a href="/upload" class="btn-primary" style="width:100%;justify-content:center;">Start Free Scan</a>
    </div>
    <div class="tier-card">
      <div class="tier-name">Guardian</div>
      <div class="tier-price">$349<span class="per">/mo</span></div>
      <div class="tier-desc">Continuous monthly monitoring. Catch new leaks as they appear.</div>
      <ul class="tier-features">
        <li>Monthly automated scans</li>
        <li>Leak alert reports</li>
        <li>All 15 leak patterns</li>
        <li>Cancel anytime</li>
      </ul>
      <a href="/checkout/guardian" class="btn-ghost" style="width:100%;justify-content:center;">Start Guardian</a>
    </div>
  </div>

  <div class="perf-section">
    <h2>If we find $40,000&#8230;</h2>
    <p class="perf-sub">Here's exactly what the math looks like on a typical scan.</p>
    <div class="calc-row">
      <span class="calc-label">Estimated leakage found</span>
      <span class="calc-val">$40,000</span>
    </div>
    <div class="calc-row">
      <span class="calc-label">Self-Serve fee (10%)</span>
      <span class="calc-val" style="color:var(--danger);">&#8722;$4,000</span>
    </div>
    <div class="calc-row">
      <span class="calc-label">Done-With-You fee (20%)</span>
      <span class="calc-val" style="color:var(--warning);">&#8722;$8,000</span>
    </div>
    <div class="calc-row">
      <span class="calc-label">&#9989; You keep (Self-Serve)</span>
      <span class="calc-val">$36,000</span>
    </div>
  </div>

  <div class="faq-section">
    <h2>Common Questions</h2>
    <div class="faq-item">
      <div class="faq-question" onclick="toggleFaq(this)">
        What if you don't find anything?
        <span class="faq-chevron">&#8964;</span>
      </div>
      <div class="faq-answer">
        If LeakLock doesn't find any revenue leaks in your data, you pay absolutely nothing. The scan is always free. We only charge a percentage of what we actually find and you recover.
      </div>
    </div>
    <div class="faq-item">
      <div class="faq-question" onclick="toggleFaq(this)">
        Is my billing data safe?
        <span class="faq-chevron">&#8964;</span>
      </div>
      <div class="faq-answer">
        Yes. Your CSV file is analyzed in memory and deleted immediately after the scan completes. We never store raw billing data. Scan results are retained for up to 30 days so you can access your report. All traffic is SSL encrypted.
      </div>
    </div>
    <div class="faq-item">
      <div class="faq-question" onclick="toggleFaq(this)">
        What file formats do you accept?
        <span class="faq-chevron">&#8964;</span>
      </div>
      <div class="faq-answer">
        We accept CSV, Excel (.xlsx, .xls), and TSV files up to 100MB. Most practice management systems can export billing data in CSV format. We also provide a sample CSV you can use to test the system before uploading your real data.
      </div>
    </div>
  </div>

</div>
<div class="footer">
  LeakLock &#169; 2026 &bull; <a href="/privacy">Privacy</a> &bull; <a href="/terms">Terms</a>
</div>

<script>
function toggleFaq(el) {{
  var item = el.parentElement;
  var isOpen = item.classList.contains('open');
  document.querySelectorAll('.faq-item').forEach(function(i) {{ i.classList.remove('open'); }});
  if (!isOpen) item.classList.add('open');
}}
</script>
</body>
</html>"""


def page_dental():
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LeakLock for Dental Practices</title>
<style>
{BASE_CSS}

.dental-hero-wrap {{
  position: relative; overflow: hidden;
  text-align: center; padding: 100px 24px 80px;
  background: radial-gradient(ellipse at center top, rgba(56,189,248,0.08) 0%, transparent 60%);
}}
.dental-badge {{
  display: inline-flex; align-items: center; gap: 8px;
  background: rgba(52,211,153,0.1); border: 1px solid rgba(52,211,153,0.25);
  color: #34d399; font-size: 13px; font-weight: 600;
  padding: 6px 16px; border-radius: 100px; margin-bottom: 28px;
}}
.dental-title {{
  font-size: clamp(32px, 5vw, 56px); font-weight: 900; line-height: 1.1;
  letter-spacing: -2px; margin-bottom: 20px;
  background: linear-gradient(135deg, #f1f5f9 0%, #34d399 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}}
.dental-sub {{
  font-size: clamp(16px, 2vw, 18px); color: var(--text-2);
  max-width: 520px; margin: 0 auto 40px; line-height: 1.6;
}}

.stat-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px; background: var(--border); border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; margin-bottom: 60px; }}
.stat-box {{ background: var(--surface); padding: 32px 24px; text-align: center; }}
.stat-box .val {{ font-size: 44px; font-weight: 900; letter-spacing: -1.5px; color: var(--primary); }}
.stat-box .lbl {{ font-size: 14px; color: var(--text-2); margin-top: 6px; font-weight: 500; }}

.leak-pattern-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 60px; }}
.leak-pattern-card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: 24px;
  transition: all 0.2s;
}}
.leak-pattern-card:hover {{ border-color: rgba(56,189,248,0.25); transform: translateY(-2px); }}
.leak-pattern-icon {{ font-size: 28px; margin-bottom: 12px; }}
.leak-pattern-name {{ font-size: 16px; font-weight: 700; margin-bottom: 8px; }}
.leak-pattern-desc {{ font-size: 14px; color: var(--text-2); line-height: 1.5; }}

.how-dental {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 40px; margin-bottom: 48px; }}
.how-dental h2 {{ font-size: 22px; font-weight: 800; margin-bottom: 24px; }}
.export-step {{ display: flex; gap: 16px; padding: 16px 0; border-bottom: 1px solid var(--border); align-items: flex-start; }}
.export-step:last-child {{ border-bottom: none; }}
.export-num {{
  width: 32px; height: 32px; background: rgba(56,189,248,0.1);
  border: 1px solid rgba(56,189,248,0.3); border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 800; color: var(--primary); flex-shrink: 0;
}}
.export-content {{ flex: 1; }}
.export-title {{ font-size: 15px; font-weight: 700; margin-bottom: 4px; }}
.export-body {{ font-size: 13px; color: var(--text-2); line-height: 1.5; }}

.testimonial {{
  background: linear-gradient(135deg, var(--surface2) 0%, var(--surface) 100%);
  border: 1px solid var(--border); border-radius: var(--radius-lg);
  padding: 40px; margin-bottom: 48px; text-align: center;
}}
.testimonial-quote {{ font-size: clamp(18px, 2.5vw, 24px); font-weight: 700; line-height: 1.4; color: var(--text); margin-bottom: 20px; }}
.testimonial-quote::before {{ content: '\\201C'; color: var(--primary); font-size: 1.5em; }}
.testimonial-quote::after {{ content: '\\201D'; color: var(--primary); font-size: 1.5em; }}
.testimonial-attr {{ font-size: 14px; color: var(--text-3); }}
.testimonial-attr strong {{ color: var(--text-2); }}

.section {{ margin-bottom: 60px; }}
.section-label {{ font-size: 12px; font-weight: 700; color: var(--success); text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 12px; }}
.section-title {{ font-size: clamp(22px, 3vw, 32px); font-weight: 800; letter-spacing: -0.5px; margin-bottom: 12px; }}
.section-sub {{ font-size: 15px; color: var(--text-2); margin-bottom: 32px; }}
</style>
</head>
<body>
{nav_html()}

<div class="dental-hero-wrap">
  <div class="dental-badge">&#129687; Built for Dental Practices</div>
  <h1 class="dental-title">We Find Your Hidden<br>Dental Billing Leaks.</h1>
  <p class="dental-sub">The average dental practice loses $40,000+ per year to billing errors. We scan your data and show you exactly where it's going.</p>
  <div style="display:flex;gap:16px;justify-content:center;flex-wrap:wrap;">
    <a href="/upload" class="btn-primary">Start Free Scan &#8594;</a>
    <a href="#how-it-works" class="btn-ghost">How It Works</a>
  </div>
</div>

<div class="container">

  <div class="stat-grid">
    <div class="stat-box">
      <div class="val">$40K</div>
      <div class="lbl">Average Finding Per Practice</div>
    </div>
    <div class="stat-box">
      <div class="val">8&#8211;12%</div>
      <div class="lbl">Typical Revenue Lost to Leaks</div>
    </div>
    <div class="stat-box">
      <div class="val">15</div>
      <div class="lbl">Patterns We Detect</div>
    </div>
  </div>

  <div class="section">
    <div class="section-label">Detection</div>
    <h2 class="section-title">Common Dental Billing Leaks</h2>
    <p class="section-sub">We check for every one of these on every scan.</p>
    <div class="leak-pattern-grid">
      <div class="leak-pattern-card">
        <div class="leak-pattern-icon">&#128260;</div>
        <div class="leak-pattern-name">Duplicate Claims</div>
        <div class="leak-pattern-desc">The same procedure billed twice &#8212; often rejected silently without a refund.</div>
      </div>
      <div class="leak-pattern-card">
        <div class="leak-pattern-icon">&#128203;</div>
        <div class="leak-pattern-name">Wrong Procedure Codes</div>
        <div class="leak-pattern-desc">Outdated or incorrect procedure codes in billing data lead to underpayments and revenue gaps.</div>
      </div>
      <div class="leak-pattern-card">
        <div class="leak-pattern-icon">&#128683;</div>
        <div class="leak-pattern-name">Missing Modifiers</div>
        <div class="leak-pattern-desc">Billing rows with missing or mismatched modifier fields that correlate with lower payment amounts.</div>
      </div>
      <div class="leak-pattern-card">
        <div class="leak-pattern-icon">&#8987;</div>
        <div class="leak-pattern-name">Untimely Filing</div>
        <div class="leak-pattern-desc">Rows with dates suggesting filing past typical payer windows, flagged for review.</div>
      </div>
      <div class="leak-pattern-card">
        <div class="leak-pattern-icon">&#128101;</div>
        <div class="leak-pattern-name">Coordination of Benefits</div>
        <div class="leak-pattern-desc">Patterns indicating under-collection where primary and secondary payer fields suggest uncollected balance.</div>
      </div>
      <div class="leak-pattern-card">
        <div class="leak-pattern-icon">&#128178;</div>
        <div class="leak-pattern-name">Write-off Errors</div>
        <div class="leak-pattern-desc">Writing off more than the contractual adjustment required &#8212; a silent revenue killer.</div>
      </div>
    </div>
  </div>

  <div class="how-dental" id="how-it-works">
    <h2>How to Export Your Billing Data</h2>
    <div class="export-step">
      <div class="export-num">1</div>
      <div class="export-content">
        <div class="export-title">Open your practice management system</div>
        <div class="export-body">Works with Dentrix, Eaglesoft, OpenDental, Curve Dental, Carestream, and most others.</div>
      </div>
    </div>
    <div class="export-step">
      <div class="export-num">2</div>
      <div class="export-content">
        <div class="export-title">Export your billing or claims report as CSV</div>
        <div class="export-body">Look for &ldquo;Claims Report&rdquo; or &ldquo;Production &amp; Collection&rdquo; in your reports menu. Export as CSV or Excel.</div>
      </div>
    </div>
    <div class="export-step">
      <div class="export-num">3</div>
      <div class="export-content">
        <div class="export-title">Upload to LeakLock</div>
        <div class="export-body">Drop the file on our upload page. Scan takes under 60 seconds for most practices.</div>
      </div>
    </div>
    <div class="export-step">
      <div class="export-num">4</div>
      <div class="export-content">
        <div class="export-title">Get your results</div>
        <div class="export-body">See exactly which patterns are leaking revenue and how much each one is costing you.</div>
      </div>
    </div>
  </div>

  <div style="background: linear-gradient(135deg, var(--surface) 0%, var(--surface2) 100%); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 56px; text-align: center;">
    <h2 style="font-size:clamp(24px,4vw,36px);font-weight:900;letter-spacing:-1px;margin-bottom:12px;">Ready to Find Your Leaks?</h2>
    <p style="color:var(--text-2);font-size:16px;margin-bottom:32px;max-width:440px;margin-left:auto;margin-right:auto;">Free scan, no card required. We only charge if we find something &#8212; and only on what you recover.</p>
    <a href="/upload" class="btn-primary" style="font-size:16px;padding:16px 36px;">Start Free Dental Scan &#8594;</a>
  </div>

</div>
<div class="footer">
  LeakLock &#169; 2026 &bull; <a href="/privacy">Privacy</a> &bull; <a href="/terms">Terms</a>
</div>
</body>
</html>"""


def page_payment_success(ptype='recovery', scan_id=''):
    msg_map = {
        'guardian': "You're now protected with LeakLock Guardian. Monthly scans will start immediately.",
        'starter': "Welcome to LeakLock Starter! Your recovery guide is ready.",
        'pro': "Welcome to LeakLock Pro! Check your email for your detailed remediation guide.",
        'enterprise': "Welcome to LeakLock Enterprise! Your dedicated analyst will reach out within 24 hours.",
        'self-serve': "Your self-serve recovery playbook is ready. Check your email.",
        'done-with-you': "Your done-with-you session is confirmed. We'll reach out within 24 hours.",
    }
    msg = msg_map.get(ptype, "Payment received! Thank you.")

    back_link = f'<a href="/results/{scan_id}" class="btn-ghost" style="margin-top:16px;">&#8592; Back to Scan Results</a>' if scan_id else '<a href="/" class="btn-ghost" style="margin-top:16px;">&#8592; Back to Home</a>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Payment Confirmed &#8212; LeakLock</title>
<style>
{BASE_CSS}

.success-wrap {{
  display: flex; justify-content: center; align-items: center;
  min-height: 100vh; background: var(--bg); padding: 24px;
}}
.success-card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: 56px 48px;
  text-align: center; max-width: 480px; width: 100%;
  animation: slide-up 0.5s ease;
}}
@keyframes slide-up {{
  from {{ transform: translateY(20px); opacity: 0; }}
  to {{ transform: translateY(0); opacity: 1; }}
}}
.success-icon {{
  font-size: 72px; margin-bottom: 24px;
  display: block;
  animation: pop 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) 0.2s both;
}}
@keyframes pop {{
  from {{ transform: scale(0); }}
  to {{ transform: scale(1); }}
}}
.success-card h1 {{
  font-size: 32px; font-weight: 800; margin-bottom: 12px;
  letter-spacing: -0.5px;
}}
.success-card p {{
  color: var(--text-2); font-size: 16px; margin-bottom: 8px;
  line-height: 1.6;
}}
.confetti-wrap {{
  position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  pointer-events: none; overflow: hidden; z-index: 0;
}}
.confetti-piece {{
  position: absolute; width: 8px; height: 8px; border-radius: 2px;
  animation: confetti-fall linear both;
}}
@keyframes confetti-fall {{
  0% {{ transform: translateY(-20px) rotate(0deg); opacity: 1; }}
  100% {{ transform: translateY(100vh) rotate(720deg); opacity: 0; }}
}}
</style>
</head>
<body>
<div class="confetti-wrap" id="confetti"></div>
<div class="success-wrap">
  <div class="success-card" style="position:relative;z-index:1;">
    <span class="success-icon">&#9989;</span>
    <h1>Payment Confirmed!</h1>
    <p>{msg}</p>
    <p style="font-size:13px;color:var(--text-3);margin-top:4px;">A confirmation has been sent to your email.</p>
    {back_link}
  </div>
</div>

<script>
var colors = ['#38bdf8','#818cf8','#34d399','#fbbf24','#f87171'];
var confetti = document.getElementById('confetti');
for (var i = 0; i < 60; i++) {{
  var piece = document.createElement('div');
  piece.className = 'confetti-piece';
  piece.style.left = Math.random() * 100 + 'vw';
  piece.style.background = colors[Math.floor(Math.random() * colors.length)];
  piece.style.animationDuration = (Math.random() * 3 + 2) + 's';
  piece.style.animationDelay = (Math.random() * 2) + 's';
  piece.style.width = (Math.random() * 8 + 4) + 'px';
  piece.style.height = (Math.random() * 8 + 4) + 'px';
  confetti.appendChild(piece);
}}
</script>
</body>
</html>"""


def page_privacy():
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LeakLock &#8212; Privacy Policy</title>
<style>
{BASE_CSS}

.legal-wrap {{ max-width: 720px; margin: 0 auto; }}
.legal-wrap h1 {{ font-size: 36px; font-weight: 800; letter-spacing: -1px; margin-bottom: 8px; }}
.legal-effective {{ color: var(--text-3); font-size: 14px; margin-bottom: 48px; }}
.legal-wrap h2 {{ font-size: 18px; font-weight: 700; color: var(--text); margin: 36px 0 12px; }}
.legal-wrap p {{ font-size: 15px; color: var(--text-2); line-height: 1.75; margin-bottom: 16px; }}
.legal-wrap ul {{ padding-left: 24px; margin-bottom: 16px; }}
.legal-wrap ul li {{ font-size: 15px; color: var(--text-2); line-height: 1.75; margin-bottom: 8px; }}
.legal-wrap a {{ color: var(--primary); text-decoration: none; }}
.legal-wrap a:hover {{ text-decoration: underline; }}
.legal-wrap strong {{ color: var(--text); }}
</style>
</head>
<body>
{nav_html()}
<div class="container">
<div class="legal-wrap">
  <h1>&#128274; Privacy Policy</h1>
  <p class="legal-effective">Effective Date: March 2026</p>

  <p>LeakLock (&ldquo;we&rdquo;, &ldquo;us&rdquo;, &ldquo;our&rdquo;) is committed to protecting your privacy. This policy explains what we collect, how we use it, and what rights you have.</p>

  <h2>What We Collect</h2>
  <ul>
    <li><strong>Email address (optional):</strong> Only if you voluntarily enter it to save results.</li>
    <li><strong>CSV billing data:</strong> Processed in memory only. Deleted immediately after scan completes.</li>
    <li><strong>Scan results:</strong> Retained temporarily (up to 30 days) so you can access your report.</li>
    <li><strong>IP address:</strong> Logged for rate limiting and abuse prevention only.</li>
  </ul>

  <h2>What We Do NOT Do</h2>
  <ul>
    <li>We do <strong>not</strong> sell your data to anyone.</li>
    <li>We do <strong>not</strong> share your email with advertisers or third parties.</li>
    <li>We do <strong>not</strong> store your CSV file after the scan is complete.</li>
    <li>We do <strong>not</strong> use your data to train AI models.</li>
  </ul>

  <h2>Data Retention</h2>
  <ul>
    <li><strong>CSV data:</strong> Deleted immediately after scan.</li>
    <li><strong>Scan results:</strong> Retained up to 30 days, then permanently deleted.</li>
    <li><strong>Emails:</strong> Retained until you request deletion.</li>
  </ul>

  <h2>Security</h2>
  <p>All traffic is encrypted via HTTPS/TLS. Payment processing is handled exclusively by Stripe &#8212; we never store card data.</p>

  <h2>Your Rights</h2>
  <p>You may request deletion of any data we hold about you at any time. Contact us at <a href="mailto:privacy@leaklock.io">privacy@leaklock.io</a> and we will process your request within 48 hours.</p>

  <h2>Contact</h2>
  <p>Questions about privacy? Email <a href="mailto:privacy@leaklock.io">privacy@leaklock.io</a></p>
</div>
</div>
<div class="footer">LeakLock &#169; 2026 &bull; <a href="/privacy">Privacy</a> &bull; <a href="/terms">Terms</a></div>
</body>
</html>"""


def page_terms():
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LeakLock &#8212; Terms of Service</title>
<style>
{BASE_CSS}

.legal-wrap {{ max-width: 720px; margin: 0 auto; }}
.legal-wrap h1 {{ font-size: 36px; font-weight: 800; letter-spacing: -1px; margin-bottom: 8px; }}
.legal-effective {{ color: var(--text-3); font-size: 14px; margin-bottom: 48px; }}
.legal-wrap h2 {{ font-size: 18px; font-weight: 700; color: var(--text); margin: 36px 0 12px; }}
.legal-wrap p {{ font-size: 15px; color: var(--text-2); line-height: 1.75; margin-bottom: 16px; }}
.legal-wrap ul {{ padding-left: 24px; margin-bottom: 16px; }}
.legal-wrap ul li {{ font-size: 15px; color: var(--text-2); line-height: 1.75; margin-bottom: 8px; }}
.legal-wrap a {{ color: var(--primary); text-decoration: none; }}
.legal-wrap a:hover {{ text-decoration: underline; }}
.legal-wrap strong {{ color: var(--text); }}
</style>
</head>
<body>
{nav_html()}
<div class="container">
<div class="legal-wrap">
  <h1>&#128203; Terms of Service</h1>
  <p class="legal-effective">Effective Date: March 2026</p>

  <h2>1. The Service</h2>
  <p>LeakLock provides automated billing analysis software. It is a data analysis tool only. <strong>Nothing in this service constitutes financial, legal, or medical billing advice.</strong></p>

  <h2>2. Estimates Are Algorithmic</h2>
  <p>Leakage estimates are algorithmic approximations based on pattern matching against your billing data. They are not guarantees of recoverable revenue. Actual recoverable amounts may vary.</p>

  <h2>3. Recovery Fee Structure</h2>
  <ul>
    <li><strong>Self-Serve:</strong> 10% of revenue recovered within 90 days of scan date.</li>
    <li><strong>Done-With-You:</strong> 20% of revenue recovered within 90 days.</li>
    <li><strong>Guardian:</strong> $349/month subscription after initial recovery period.</li>
  </ul>

  <h2>4. Your Data</h2>
  <p>You retain full ownership of your billing data. You grant LeakLock a limited license to process it for the purpose of providing scan results. CSV data is deleted immediately after scanning.</p>

  <h2>5. No Warranty</h2>
  <p>The service is provided &ldquo;as is&rdquo; without warranty of any kind, express or implied, including fitness for a particular purpose or merchantability.</p>

  <h2>6. Limitation of Liability</h2>
  <p>LeakLock&rsquo;s maximum liability to you under these terms shall not exceed the amounts paid by you in the 12 months prior to the claim.</p>

  <h2>7. Changes to Terms</h2>
  <p>We may update these terms at any time. Continued use of the service after changes constitutes acceptance of the updated terms.</p>

  <h2>Contact</h2>
  <p>Questions? Email <a href="mailto:legal@leaklock.io">legal@leaklock.io</a></p>
</div>
</div>
<div class="footer">LeakLock &#169; 2026 &bull; <a href="/privacy">Privacy</a> &bull; <a href="/terms">Terms</a></div>
</body>
</html>"""


def page_contact():
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LeakLock &#8212; Contact</title>
<style>
{BASE_CSS}
.contact-wrap {{ max-width: 600px; margin: 0 auto; }}
.contact-wrap h1 {{ font-size: 36px; font-weight: 800; letter-spacing: -1px; margin-bottom: 8px; }}
.contact-sub {{ color: var(--text-2); font-size: 16px; margin-bottom: 40px; }}
.contact-card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: 40px;
}}
.contact-row {{ display: flex; gap: 16px; align-items: flex-start; padding: 16px 0; border-bottom: 1px solid var(--border); }}
.contact-row:last-child {{ border-bottom: none; }}
.contact-icon {{ font-size: 24px; flex-shrink: 0; width: 40px; text-align: center; }}
.contact-label {{ font-size: 13px; font-weight: 600; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }}
.contact-val {{ font-size: 15px; color: var(--text); }}
.contact-val a {{ color: var(--primary); text-decoration: none; }}
.contact-val a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
{nav_html()}
<div class="container">
<div class="contact-wrap">
  <h1>Contact</h1>
  <p class="contact-sub">Questions, support, or partnership inquiries &#8212; we respond within one business day.</p>
  <div class="contact-card">
    <div class="contact-row">
      <div class="contact-icon">&#128233;</div>
      <div>
        <div class="contact-label">General &amp; Support</div>
        <div class="contact-val"><a href="mailto:hello@leaklock.io">hello@leaklock.io</a></div>
      </div>
    </div>
    <div class="contact-row">
      <div class="contact-icon">&#128274;</div>
      <div>
        <div class="contact-label">Privacy</div>
        <div class="contact-val"><a href="mailto:privacy@leaklock.io">privacy@leaklock.io</a></div>
      </div>
    </div>
    <div class="contact-row">
      <div class="contact-icon">&#128203;</div>
      <div>
        <div class="contact-label">Legal</div>
        <div class="contact-val"><a href="mailto:legal@leaklock.io">legal@leaklock.io</a></div>
      </div>
    </div>
  </div>
</div>
</div>
<div class="footer">
  LeakLock &#169; 2026 &bull; <a href="/privacy">Privacy</a> &bull; <a href="/terms">Terms</a>
</div>
</body>
</html>"""


def page_report(scan):
    from datetime import datetime as _dt
    leaks = scan.get('leaks', [])
    total_revenue = scan.get('total_revenue', 0)
    total_leakage = scan.get('total_leakage', 0)
    patterns_triggered = scan.get('patterns_triggered', 0)
    scan_id = scan.get('scan_id', '')
    date_str = _dt.now().strftime('%B %d, %Y')
    scan_id_short = (scan_id[:8] + '...') if len(scan_id) > 8 else scan_id

    leaks_html = ''
    for leak in leaks:
        sev = leak.get('severity', 'medium')
        det = leak.get('details', {})
        if isinstance(det, str):
            try:
                det = json.loads(det)
            except Exception:
                det = {}
        pattern_name = leak.get('pattern_name') or det.get('pattern_name') or leak.get('pattern', '').replace('_', ' ').title()
        description = leak.get('description') or det.get('description') or ''
        amt = leak.get('amount_estimate', 0)
        sev_color = '#dc2626' if sev == 'high' else '#d97706' if sev == 'medium' else '#059669'
        severity_label = 'Critical' if sev == 'high' else 'Medium' if sev == 'medium' else 'Low'
        leaks_html += f"""<div class="leak-item">
  <div class="leak-left" style="border-left-color:{sev_color};">
    <div class="leak-name">{pattern_name}</div>
    <div class="leak-sev" style="color:{sev_color};">{severity_label}</div>
    <div class="leak-desc">{description}</div>
  </div>
  <div class="leak-amount" style="color:{sev_color};">${amt:,}</div>
</div>"""

    if not leaks_html:
        leaks_html = '<p style="color:#64748b;padding:20px 0;">No significant leaks detected in this dataset.</p>'

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>LeakLock Revenue Analysis Report</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #060d1b; color: #f1f5f9; padding: 0;
}}
.report-header {{
  background: #0d1a2e; border-bottom: 1px solid rgba(255,255,255,0.08);
  padding: 24px 40px; display: flex; justify-content: space-between; align-items: center;
}}
.logo {{ font-size: 22px; font-weight: 800; color: #f1f5f9; }}
.logo span {{ color: #38bdf8; }}
.date {{ color: #475569; font-size: 14px; }}
.report-body {{ max-width: 840px; margin: 0 auto; padding: 40px 24px; }}
.summary {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 40px; }}
.sbox {{
  background: #0d1a2e; border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px; padding: 20px;
}}
.sbox .val {{ font-size: 32px; font-weight: 800; color: #f1f5f9; }}
.sbox .val.leak {{ color: #f87171; }}
.sbox .lbl {{ font-size: 12px; color: #475569; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
.section-title {{ font-size: 16px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px; }}
.leak-item {{
  background: #0d1a2e; border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px; padding: 20px; margin-bottom: 12px;
  display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;
}}
.leak-left {{ flex: 1; border-left: 4px solid #38bdf8; padding-left: 16px; }}
.leak-name {{ font-size: 16px; font-weight: 700; margin-bottom: 4px; }}
.leak-sev {{ font-size: 12px; font-weight: 600; margin-bottom: 6px; }}
.leak-desc {{ font-size: 13px; color: #94a3b8; line-height: 1.5; }}
.leak-amount {{ font-size: 24px; font-weight: 800; white-space: nowrap; }}
.cta {{
  background: linear-gradient(135deg, #0d1a2e 0%, #111f33 100%);
  border: 1px solid rgba(56,189,248,0.2); border-radius: 16px;
  padding: 32px; margin-top: 32px; text-align: center;
}}
.cta h3 {{ font-size: 20px; font-weight: 800; margin-bottom: 8px; }}
.cta p {{ font-size: 14px; color: #94a3b8; margin-bottom: 4px; }}
.cta .domain {{ color: #38bdf8; font-weight: 700; font-size: 16px; margin-top: 12px; }}
.report-footer {{
  text-align: center; color: #475569; font-size: 12px;
  padding: 24px; border-top: 1px solid rgba(255,255,255,0.08);
  margin-top: 24px;
}}
.no-print {{ /* visible on screen */ }}
@media print {{
  body {{ background: white !important; color: #0f172a !important; }}
  .report-header {{ background: #0f172a !important; }}
  .logo {{ color: white !important; }}
  .sbox {{ background: #f8fafc !important; border-color: #e2e8f0 !important; color: #0f172a !important; }}
  .sbox .val {{ color: #0f172a !important; }}
  .leak-item {{ background: #f8fafc !important; border-color: #e2e8f0 !important; }}
  .leak-desc {{ color: #475569 !important; }}
  .cta {{ background: #f0f9ff !important; border-color: #bae6fd !important; }}
  .cta p {{ color: #475569 !important; }}
  .no-print {{ display: none !important; }}
}}
</style>
</head>
<body>
<div class="report-header">
  <div class="logo">Leak<span>Lock</span> <span style="font-size:14px;font-weight:400;color:#475569;">Revenue Leak Analysis Report</span></div>
  <div class="date">Generated: {date_str}</div>
</div>

<div class="report-body">
  <div class="no-print" style="background:rgba(56,189,248,0.08);border:1px solid rgba(56,189,248,0.2);border-radius:10px;padding:12px 20px;display:flex;align-items:center;gap:12px;margin-bottom:28px;">
    <span style="font-size:13px;color:#7dd3fc;flex:1;">&#128438; Print this report or save as PDF</span>
    <button onclick="window.print()" style="padding:8px 18px;background:#38bdf8;color:#060d1b;border:none;border-radius:6px;font-weight:700;cursor:pointer;font-size:13px;">Print / Save PDF</button>
  </div>

  <div class="summary">
    <div class="sbox">
      <div class="val">${total_revenue:,.0f}</div>
      <div class="lbl">Revenue Scanned</div>
    </div>
    <div class="sbox">
      <div class="val leak">${total_leakage:,.0f}</div>
      <div class="lbl">Estimated Leakage</div>
    </div>
    <div class="sbox">
      <div class="val">{patterns_triggered}</div>
      <div class="lbl">Patterns Detected</div>
    </div>
  </div>

  <div class="section-title">Detected Leak Patterns</div>
  {leaks_html}

  <div class="cta">
    <h3>Recover This Revenue</h3>
    <p><strong style="color:#f1f5f9;">Self-Serve Recovery</strong> &#8212; pay 10% of what we find, keep 90%</p>
    <p><strong style="color:#f1f5f9;">Done-With-You Recovery</strong> &#8212; pay 20%, we walk you through it, keep 80%</p>
    <div class="domain">leaklock.com &#8594; Get Started</div>
  </div>
</div>

<div class="report-footer">
  LeakLock &#169; 2026 &#8212; Revenue Leak Detection. Your data is deleted after scanning. Estimates are indicative, not guaranteed.
  Scan ID: {scan_id_short}
  &bull; <a href="/privacy" style="color:#475569;">Privacy</a>
  &bull; <a href="/terms" style="color:#475569;">Terms</a>
</div>

<script>
setTimeout(function() {{ window.print(); }}, 1000);
</script>
</body>
</html>"""
