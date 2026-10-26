"""Punto de entrada.

- Desarrollo:   flask --app run.py run
- Producción:   gunicorn run:app            (Linux / Render)
                waitress-serve --port=5000 run:app   (Windows)
"""
import os

from app import create_app, db
from app.models import Usuario

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {"db": db, "Usuario": Usuario}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    # El modo debug permite ejecutar código desde el navegador: solo en tu equipo.
    app.run(host="127.0.0.1" if debug else "0.0.0.0", port=port, debug=debug)
