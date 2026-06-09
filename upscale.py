import os

import cv2
import numpy as np
from cv2 import dnn_superres


MODEL_PATH = os.getenv("MODEL_PATH", "EDSR_x2.pb")

_scaler = None


def get_scaler():
    """
    Загружает модель один раз и переиспользует её при следующих вызовах.
    """
    global _scaler

    if _scaler is None:
        scaler = dnn_superres.DnnSuperResImpl_create()
        scaler.readModel(MODEL_PATH)
        scaler.setModel("edsr", 2)
        _scaler = scaler

    return _scaler


def upscale(image_bytes: bytes, extension: str = "png") -> bytes:
    """
    Апскейлит изображение без сохранения файла на диск.

    :param image_bytes: исходное изображение в байтах
    :param extension: расширение выходного изображения
    :return: обработанное изображение в байтах
    """

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Не удалось прочитать изображение")

    scaler = get_scaler()
    result = scaler.upsample(image)

    extension = extension.lower()

    if extension == "jpg":
        extension = "jpeg"

    success, encoded_image = cv2.imencode(f".{extension}", result)

    if not success:
        raise ValueError("Не удалось закодировать обработанное изображение")

    return encoded_image.tobytes()