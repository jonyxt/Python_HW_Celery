import base64

from celery_app import celery
from upscale import upscale


@celery.task(name="tasks.upscale_image_task")
def upscale_image_task(image_base64: str, extension: str) -> dict:
    image_bytes = base64.b64decode(image_base64.encode("utf-8"))

    processed_bytes = upscale(
        image_bytes=image_bytes,
        extension=extension,
    )

    processed_base64 = base64.b64encode(processed_bytes).decode("utf-8")

    return {
        "image": processed_base64,
        "extension": extension,
    }