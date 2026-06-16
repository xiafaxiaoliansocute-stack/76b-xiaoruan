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

        # Chạy lấy dữ liệu 76b
        subprocess.run(
            ["python3", "main.py"],
            check=True
        )
        # Chạy lấy dữ liệu nn22
        subprocess.run(
            ["python3", "nn22.py"],
            check=True
        )

        # Git add
        subprocess.run(
            ["git", "add", "."],
            check=True
        )

        # Git commit
        subprocess.run(
            ["git", "commit", "-m", "auto update"],
            check=False
        )

        # Git push
        subprocess.run(
            ["git", "push"],
            check=True
        )

        return jsonify({
            "success": True,
            "message": "Data updated and pushed to GitHub"
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        })


@app.route("/data.json")
def data_file():
    return send_from_directory(".", "data.json")


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )