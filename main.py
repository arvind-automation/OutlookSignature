import os
import sys

import init_db
from app import create_app

# Must pass [] so argparse does not consume gunicorn/CLI args from sys.argv.
rc = init_db.main([])
if rc != 0:
    sys.exit(rc)

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_ENV", "development") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
