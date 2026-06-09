import numpy as np
import pytest

import upscale as upscale_module


class FakeScaler:
    def __init__(self):
        self.calls_count = 0

    def upsample(self, image):
        self.calls_count += 1
        return image


def test_upscale_success(mocker):
    fake_image = np.zeros((10, 10, 3), dtype=np.uint8)
    fake_encoded = np.array([1, 2, 3, 4, 5], dtype=np.uint8)
    fake_scaler = FakeScaler()

    mocker.patch("upscale.cv2.imdecode", return_value=fake_image)
    mocker.patch("upscale.cv2.imencode", return_value=(True, fake_encoded))
    mocker.patch("upscale.get_scaler", return_value=fake_scaler)

    result = upscale_module.upscale(
        image_bytes=b"fake image bytes",
        extension="png",
    )

    assert result == b"\x01\x02\x03\x04\x05"
    assert fake_scaler.calls_count == 1


def test_upscale_invalid_image(mocker):
    mocker.patch("upscale.cv2.imdecode", return_value=None)

    with pytest.raises(ValueError, match="Не удалось прочитать изображение"):
        upscale_module.upscale(
            image_bytes=b"not image",
            extension="png",
        )


def test_upscale_encode_error(mocker):
    fake_image = np.zeros((10, 10, 3), dtype=np.uint8)
    fake_scaler = FakeScaler()

    mocker.patch("upscale.cv2.imdecode", return_value=fake_image)
    mocker.patch("upscale.cv2.imencode", return_value=(False, None))
    mocker.patch("upscale.get_scaler", return_value=fake_scaler)

    with pytest.raises(ValueError, match="Не удалось закодировать обработанное изображение"):
        upscale_module.upscale(
            image_bytes=b"fake image bytes",
            extension="png",
        )


def test_get_scaler_loads_model_only_once(mocker):
    upscale_module._scaler = None

    fake_scaler = mocker.Mock()

    create_scaler = mocker.patch(
        "upscale.dnn_superres.DnnSuperResImpl_create",
        return_value=fake_scaler,
    )

    first_scaler = upscale_module.get_scaler()
    second_scaler = upscale_module.get_scaler()

    assert first_scaler is second_scaler
    assert create_scaler.call_count == 1

    fake_scaler.readModel.assert_called_once()
    fake_scaler.setModel.assert_called_once_with("edsr", 2)