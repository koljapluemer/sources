import socket
import threading
import webbrowser

from flask import Flask, jsonify, render_template, request

import bibtex_import
import store
from fields import ValidationError, schema

PORT = 8765

app = Flask(__name__)


@app.errorhandler(ValidationError)
def _invalid(e):
    return jsonify(error=str(e)), 400


@app.errorhandler(store.Conflict)
def _conflict(e):
    return jsonify(error=str(e)), 409


@app.errorhandler(store.NotFound)
def _not_found(e):
    return jsonify(error=f"'{e}' not found"), 404


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/schema")
def get_schema():
    return jsonify(schema())


@app.get("/api/settings")
def get_settings():
    p = store.get_path()
    return jsonify(path=str(p) if p else None)


@app.put("/api/settings")
def put_settings():
    path = (request.get_json().get("path") or "").strip()
    if not path:
        raise ValidationError("path required")
    return jsonify(path=str(store.set_path(path)))


@app.get("/api/sources")
def list_sources():
    return jsonify(store.list_sources())


@app.get("/api/recent")
def recent_sources():
    return jsonify(store.recent())


@app.post("/api/sources")
def create_source():
    return jsonify(store.create(request.get_json())), 201


@app.put("/api/sources/<key>")
def update_source(key):
    return jsonify(store.update(key, request.get_json()))


@app.delete("/api/sources/<key>")
def delete_source(key):
    store.delete(key)
    return "", 204


@app.post("/api/import-bibtex")
def import_bibtex():
    try:
        sources = bibtex_import.parse(request.get_json().get("text", ""))
    except ValueError as e:
        raise ValidationError(str(e)) from None
    taken = {s["key"] for s in store.list_sources()}
    created = []
    for s in sources:
        base, n = s["key"], 2
        while s["key"] in taken:
            s["key"] = f"{base}-{n}"
            n += 1
        taken.add(s["key"])
        created.append(store.create(s))
    return jsonify(created), 201


def _running() -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", PORT)) == 0


if __name__ == "__main__":
    url = f"http://127.0.0.1:{PORT}"
    if _running():
        webbrowser.open(url)
    else:
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()
        app.run(port=PORT)
