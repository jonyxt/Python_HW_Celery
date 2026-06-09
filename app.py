import base64
from io import BytesIO

from celery.result import AsyncResult
from flask import Flask, request, jsonify, send_file

from celery_app import celery


app = Flask(__name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_mimetype(extension: str) -> str:
    extension = extension.lower()

    if extension in {"jpg", "jpeg"}:
        return "image/jpeg"

    if extension == "png":
        return "image/png"

    if extension == "webp":
        return "image/webp"

    return "application/octet-stream"


@app.post("/upscale")
def create_upscale_task():
    if "file" not in request.files:
        return jsonify({"error": "Файл не передан"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "Имя файла пустое"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Недопустимый формат файла"}), 400

    extension = file.filename.rsplit(".", 1)[1].lower()

    image_bytes = file.read()

    if not image_bytes:
        return jsonify({"error": "Файл пустой"}), 400

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    task = celery.send_task(
        "tasks.upscale_image_task",
        args=[image_base64, extension],
    )

    return jsonify({
        "task_id": task.id,
    }), 202


@app.get("/tasks/<task_id>")
def get_task_status(task_id: str):
    task = AsyncResult(task_id, app=celery)

    response = {
        "task_id": task_id,
        "status": task.status,
    }

    if task.successful():
        result = task.result
        extension = result["extension"]

        filename = f"{task_id}.{extension}"

        response["file"] = filename
        response["url"] = f"/processed/{filename}"

    elif task.failed():
        response["error"] = str(task.result)

    return jsonify(response)


@app.get("/processed/<filename>")
def get_processed_file(filename: str):
    if "." not in filename:
        return jsonify({"error": "Некорректное имя файла"}), 400

    task_id, extension = filename.rsplit(".", 1)

    task = AsyncResult(task_id, app=celery)

    if not task.successful():
        return jsonify({
            "task_id": task_id,
            "status": task.status,
            "error": "Файл ещё не готов",
        }), 404

    result = task.result

    image_base64 = result["image"]
    image_bytes = base64.b64decode(image_base64.encode("utf-8"))

    return send_file(
        BytesIO(image_bytes),
        mimetype=get_mimetype(extension),
        as_attachment=False,
        download_name=filename,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)