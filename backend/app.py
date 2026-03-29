import os
from flask import Flask
from flask_cors import CORS
from api.routes import api_bp
from config import FLASK_DEBUG, UPLOADS_DIR, SESSIONS_DIR

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

app.register_blueprint(api_bp)

# Ensure storage dirs exist on startup
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(SESSIONS_DIR, exist_ok=True)


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000, debug=FLASK_DEBUG, threaded=True)
