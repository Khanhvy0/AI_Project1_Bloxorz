"""Flask API connecting the GUI to the game rules engine."""
from threading import Event, Lock

from flask import Flask, jsonify, render_template, request

from gui import engine_adapter as engine

_solve_events: dict[str, Event] = {}
_solve_events_lock = Lock()


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
        solve_id = d.get("solve_id")
        if not isinstance(solve_id, str) or not solve_id:
            return jsonify({"error": "solve_id is required"}), 400
        lv = engine.get_level(d["level_id"])
        with _solve_events_lock:
            cancellation_event = _solve_events.setdefault(solve_id, Event())
        try:
            return jsonify(engine.solve(lv, d["algo"], cancellation_event))
        except engine.SolveCancelled as error:
            return jsonify({"error": str(error)}), 409
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        finally:
            with _solve_events_lock:
                _solve_events.pop(solve_id, None)

    @app.post("/api/solve/cancel")
    def cancel_solve():
        d = request.get_json()
        solve_id = d.get("solve_id")
        if not isinstance(solve_id, str) or not solve_id:
            return jsonify({"error": "solve_id is required"}), 400
        with _solve_events_lock:
            cancellation_event = _solve_events.setdefault(solve_id, Event())
            cancellation_event.set()
        return jsonify({"cancelled": True})

    return app
