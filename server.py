import warnings
warnings.filterwarnings("ignore")
from flask import Flask, jsonify, send_from_directory
import subprocess
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("SERVER =", __file__)
print("BASE_DIR =", BASE_DIR)
print("NN22 EXISTS =", os.path.exists(os.path.join(BASE_DIR, "nn22.json")))
print("23E EXISTS =", os.path.exists(os.path.join(BASE_DIR, "23e.json")))


# ================= HOME =================
@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


# ================= RUN 3 FILE SONG SONG =================
@app.route("/run")
def run_script():

    try:
        print("========== RUN PARALLEL ==========")

        # main.py
        p1 = subprocess.Popen(
            ["python3", os.path.join(BASE_DIR, "main.py")]
        )

        # nn22.py
        p2 = subprocess.Popen(
            ["python3", os.path.join(BASE_DIR, "nn22.py")]
        )

        # 23e.py
        p3 = subprocess.Popen(
            ["python3", os.path.join(BASE_DIR, "23e.py")]
        )


        # Đợi cả 3 chạy xong
        p1.wait()
        p2.wait()
        p3.wait()

        print("✅ main.py finished")
        print("✅ nn22.py finished")
        print("✅ 23e.py finished")

        return jsonify({
            "success": True,
            "message": "All scripts finished"
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


@app.route("/23e.json")
def e23_json():
    return send_from_directory(BASE_DIR, "23e.json")



# ================= START SERVER =================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )