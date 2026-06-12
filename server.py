from flask import Flask, jsonify, send_from_directory
import subprocess

app = Flask(__name__)

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/run")
def run_script():

    try:

        subprocess.run(
            ["python3", "main.py"],
            check=True
        )

        return jsonify({
            "success": True
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
        port=5000,
        debug=True
    )
