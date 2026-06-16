from flask import Flask, jsonify, send_from_directory
import subprocess
import os

app = Flask(__name__)


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/run")
def run_script():

    try:

        print("========== RUN MAIN.PY ==========")

        result = subprocess.run(
            ["python3", "main.py"],
            capture_output=True,
            text=True
        )

        print(result.stdout)
        print(result.stderr)

        if result.returncode != 0:
            raise Exception("main.py\n" + result.stderr)

        print("========== RUN NN22.PY ==========")

        result = subprocess.run(
            ["python3", "nn22.py"],
            capture_output=True,
            text=True
        )

        print(result.stdout)
        print(result.stderr)

        if result.returncode != 0:
            raise Exception("nn22.py\n" + result.stderr)

        print("========== GIT ==========")

        subprocess.run(
            ["git", "add", "."],
            check=True
        )

        subprocess.run(
            ["git", "commit", "-m", "auto update"],
            check=False
        )

        subprocess.run(
            ["git", "push"],
            check=True
        )

        return jsonify({
            "success": True,
            "message": "Data updated and pushed"
        })

    except Exception as e:

        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        })


@app.route("/data.json")
def data_json():
    return send_from_directory(".", "data.json")


@app.route("/nn22.json")
def nn22_json():
    return send_from_directory(".", "nn22.json")


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )