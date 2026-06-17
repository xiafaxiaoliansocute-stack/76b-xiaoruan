from flask import Flask, jsonify, send_from_directory
import subprocess
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("SERVER =", __file__)
print("BASE_DIR =", BASE_DIR)
print("NN22 EXISTS =", os.path.exists(os.path.join(BASE_DIR, "nn22.json")))


# ================= HOME =================
@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


# ================= RUN 2 FILE SONG SONG =================
@app.route("/run")
def run_script():

    try:
        print("========== RUN PARALLEL ==========")

        # CHẠY SONG SONG 2 FILE
        subprocess.Popen(
            ["python3", os.path.join(BASE_DIR, "main.py")]
        )

        subprocess.Popen(
            ["python3", os.path.join(BASE_DIR, "nn22.py")]
        )

        print("🚀 main.py + nn22.py started")

        return jsonify({
            "success": True,
            "message": "Both scripts started in parallel"
        })

    except Exception as e:
        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        })


# ================= DATA FILE =================
@app.route("/data.json")
def data_json():
    return send_from_directory(BASE_DIR, "data.json")


@app.route("/nn22.json")
def nn22_json():
    return send_from_directory(BASE_DIR, "nn22.json")


# ================= START SERVER =================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )