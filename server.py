from flask import Flask, jsonify, send_from_directory
import subprocess
import os
import traceback
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("SERVER =", __file__)
print("BASE_DIR =", BASE_DIR)


def run_script_file(script):

    print(f"========== RUN {script} ==========")

    result = subprocess.run(
        ["python3", os.path.join(BASE_DIR, script)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True
    )

    print(result.stdout)
    print(result.stderr)

    if result.returncode != 0:
        raise Exception(f"{script}\n{result.stderr}")


@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/run")
def run():

    try:

        # ==========================
        # main.py + nn22.py chạy song song
        # ==========================

        with ThreadPoolExecutor(max_workers=2) as executor:

            future1 = executor.submit(run_script_file, "main.py")
            future2 = executor.submit(run_script_file, "nn22.py")

            future1.result()
            future2.result()

        print("========== GIT ==========")

        subprocess.run(
            ["git", "add", "."],
            cwd=BASE_DIR,
            check=True
        )

        subprocess.run(
            ["git", "commit", "-m", "auto update"],
            cwd=BASE_DIR,
            check=False
        )

        subprocess.run(
            ["git", "push"],
            cwd=BASE_DIR,
            check=True
        )

        return jsonify({
            "success": True,
            "message": "Data updated successfully"
        })

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        })


@app.route("/data.json")
def data_json():
    return send_from_directory(BASE_DIR, "data.json")


@app.route("/nn22.json")
def nn22_json():
    return send_from_directory(BASE_DIR, "nn22.json")


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )