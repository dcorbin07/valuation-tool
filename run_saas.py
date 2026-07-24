"""
Run the hosted SaaS app locally (landing + accounts + gated dashboard + billing).

    python run_saas.py            # http://127.0.0.1:5000  (landing page)

In production use gunicorn:  gunicorn "valuation.saas.app_saas:app" -w 4 -b 0.0.0.0:$PORT
"""
import os
from valuation.saas.app_saas import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    print(f"SaaS app on http://127.0.0.1:{port}  (landing → register → /app)")
    app.run(host="0.0.0.0", port=port, debug=False)
