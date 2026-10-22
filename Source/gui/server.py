"""Flask API connecting the GUI to the game rules engine."""
from flask import Flask, jsonify, render_template, request

from gui import engine_adapter as engine


def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/levels")
    def levels():
        return jsonify(engine.list_levels())

    @app.get("/api/level/<level_id>")
    def level(level_id):
        lv = engine.get_level(level_id)
        return jsonify({"level": lv, "state": engine.initial_state(lv)})

    @app.post("/api/move")
    def move():
        d = request.get_json()
        lv = engine.get_level(d["level_id"])
        return jsonify({"state": engine.apply_move(lv, d["state"], d["action"])})

    @app.post("/api/solve")
    def solve():
        d = request.get_json()
        if d["algo"] != "bfs":
            return jsonify({"error": f"{d['algo']} is not implemented; only BFS is available"}), 400
        lv = engine.get_level(d["level_id"])
        return jsonify(engine.solve(lv, "bfs"))

    return app
