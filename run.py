"""
Launch the Adaptive DCF Valuation Tool web dashboard.

    python run.py

Opens http://127.0.0.1:5000 in your browser automatically.
"""
import os
import threading
import webbrowser

from valuation.web.app import app
from valuation.config import CONFIG


def _open(url):
    try:
        webbrowser.open_new(url)
    except Exception:
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    url = f"http://127.0.0.1:{port}"
    print("=" * 60)
    print("  Adaptive DCF Valuation Tool")
    print("  Open:", url)
    ai = CONFIG.resolved_ai_provider
    print(f"  AI layer: {'ON — ' + ai if CONFIG.ai_enabled else 'rule-based (no API key set)'}")
    print(f"  Monte Carlo trials: {CONFIG.montecarlo_trials}")
    print("  Press Ctrl+C to stop.")
    print("=" * 60)
    threading.Timer(1.5, _open, args=(url,)).start()
    app.run(host="127.0.0.1", port=port, debug=False)
