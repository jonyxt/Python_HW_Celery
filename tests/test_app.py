import base64
from io import BytesIO
from unittest.mock import Mock


def test_upscale_without_file(client):
    response = client.post("/upscale")

    assert response.status_code == 400
    assert response.json == {"error": "Файл не передан"}


def test_upscale_with_empty_filename(client):
    data = {
        "file": (BytesIO(b"test image content"), "")
    }

    response = client.post(
        "/upscale",
        data=data,
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.json == {"error": "Имя файла пустое"}


def test_upscale_with_invalid_extension(client):
    data = {
        "file": (BytesIO(b"test content"), "test.txt")
    }

    response = client.post(
        "/upscale",
        data=data,
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.json == {"error": "Недопустимый формат файла"}


def test_upscale_success(client, mocker):
    mocked_task = Mock()
    mocked_task.id = "test-task-id"

    mocked_send_task = mocker.patch("app.celery.send_task")
    mocked_send_task.return_value = mocked_task

    data = {
        "file": (BytesIO(b"fake image bytes"), "image.png")
    }

    response = client.post(
        "/upscale",
        data=data,
        content_type="multipart/form-data",
    )

    assert response.status_code == 202
    assert response.json == {
        "task_id": "test-task-id"
    }

    mocked_send_task.assert_called_once()

    task_name = mocked_send_task.call_args.args[0]
    task_args = mocked_send_task.call_args.kwargs["args"]

    assert task_name == "tasks.upscale_image_task"
    assert task_args[1] == "png"

    decoded_image = base64.b64decode(task_args[0].encode("utf-8"))
    assert decoded_image == b"fake image bytes"


def test_task_status_pending(client, mocker):
    mocked_task = Mock()
    mocked_task.status = "PENDING"
    mocked_task.successful.return_value = False
    mocked_task.failed.return_value = False

    mocker.patch("app.AsyncResult", return_value=mocked_task)

    response = client.get("/tasks/test-task-id")

    assert response.status_code == 200
    assert response.json == {
        "task_id": "test-task-id",
        "status": "PENDING",
    }


def test_task_status_success(client, mocker):
    mocked_task = Mock()
    mocked_task.status = "SUCCESS"
    mocked_task.successful.return_value = True
    mocked_task.failed.return_value = False
    mocked_task.result = {
        "image": "base64-image-content",
        "extension": "png",
    }

    mocker.patch("app.AsyncResult", return_value=mocked_task)

    response = client.get("/tasks/test-task-id")

    assert response.status_code == 200
    assert response.json == {
        "task_id": "test-task-id",
        "status": "SUCCESS",
        "file": "test-task-id.png",
        "url": "/processed/test-task-id.png",
    }


def test_task_status_failed(client, mocker):
    mocked_task = Mock()
    mocked_task.status = "FAILURE"
    mocked_task.successful.return_value = False
    mocked_task.failed.return_value = True
    mocked_task.result = Exception("Ошибка обработки")

    mocker.patch("app.AsyncResult", return_value=mocked_task)

    response = client.get("/tasks/test-task-id")

    assert response.status_code == 200
    assert response.json == {
        "task_id": "test-task-id",
        "status": "FAILURE",
        "error": "Ошибка обработки",
    }


def test_get_processed_file_when_task_not_ready(client, mocker):
    mocked_task = Mock()
    mocked_task.status = "PENDING"
    mocked_task.successful.return_value = False

    mocker.patch("app.AsyncResult", return_value=mocked_task)

    response = client.get("/processed/test-task-id.png")

    assert response.status_code == 404
    assert response.json == {
        "task_id": "test-task-id",
        "status": "PENDING",
        "error": "Файл ещё не готов",
    }


def test_get_processed_file_success(client, mocker):
    image_bytes = b"processed image bytes"
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    mocked_task = Mock()
    mocked_task.successful.return_value = True
    mocked_task.result = {
        "image": image_base64,
        "extension": "png",
    }

    mocker.patch("app.AsyncResult", return_value=mocked_task)

    response = client.get("/processed/test-task-id.png")

    assert response.status_code == 200
    assert response.data == image_bytes
    assert response.content_type == "image/png"