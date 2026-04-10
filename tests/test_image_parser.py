from unittest.mock import MagicMock, patch

import pytest

from src.image_parser import parse_contract_image


class TestValidateInput:
    def test_invalid_extension(self) -> None:
        with pytest.raises(ValueError, match="Formato no soportado"):
            parse_contract_image(b"fake", "contrato.pdf")

    def test_valid_jpeg(self, contract_image_bytes: bytes) -> None:
        """Usa bytes reales de documento_1__original.jpg."""
        with (
            patch("src.image_parser._get_client"),
            patch("src.image_parser._call_vision_api") as mock_api,
        ):
            mock_api.return_value = ("texto", 100)
            text, _tokens = parse_contract_image(contract_image_bytes, "contrato.jpeg")
            assert text == "texto"

    def test_valid_png(self) -> None:
        with (
            patch("src.image_parser._get_client"),
            patch("src.image_parser._call_vision_api") as mock_api,
        ):
            mock_api.return_value = ("texto", 50)
            text, _tokens = parse_contract_image(b"fake png", "contrato.png")
            assert text == "texto"

    def test_exceeds_max_size(self) -> None:
        big_bytes = b"x" * (20 * 1024 * 1024 + 1)
        with pytest.raises(ValueError, match="excede el límite"):
            parse_contract_image(big_bytes, "contrato.jpg")


class TestParseContractImage:
    @patch("src.image_parser._get_client")
    @patch("src.image_parser._call_vision_api")
    def test_successful_parse(
        self, mock_api: MagicMock, mock_client: MagicMock, contract_image_bytes: bytes
    ) -> None:
        """Usa bytes reales de documento_1__original.jpg + mock de OpenAI."""
        mock_api.return_value = ("CLAUSULA 1 - PLAZO: 12 meses.", 150)

        text, tokens = parse_contract_image(contract_image_bytes, "contrato.jpg")

        assert text == "CLAUSULA 1 - PLAZO: 12 meses."
        assert tokens == 150
        mock_api.assert_called_once()

    @patch("src.image_parser._get_client")
    @patch("src.image_parser._call_vision_api")
    def test_api_error_raises_runtime(self, mock_api: MagicMock, mock_client: MagicMock) -> None:
        mock_api.side_effect = Exception("API timeout")

        with pytest.raises(RuntimeError, match="Error en llamada a GPT-4o Vision"):
            parse_contract_image(b"fake jpg", "contrato.jpg")
