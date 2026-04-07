import json
from unittest.mock import MagicMock, patch

import pytest

from src.agents.contextualization_agent import run as run_contextualization
from src.agents.extraction_agent import run as run_extraction
from src.models import ContractChangeOutput


class TestContextualizationAgent:
    @patch("src.agents.contextualization_agent._get_client")
    @patch("src.agents.contextualization_agent._call_llm")
    def test_successful_contextualization(
        self, mock_llm: MagicMock, mock_client: MagicMock
    ) -> None:
        context_map = json.dumps(
            {
                "sections": [
                    {
                        "id": "clausula-3",
                        "title": "Plazo",
                        "purpose": "Duración del contrato",
                        "in_original": True,
                        "in_amendment": True,
                    },
                ]
            }
        )
        mock_llm.return_value = (context_map, 200)

        result, tokens = run_contextualization("texto original", "texto enmienda")

        assert "sections" in result
        assert tokens == 200

    @patch("src.agents.contextualization_agent._get_client")
    @patch("src.agents.contextualization_agent._call_llm")
    def test_api_error(self, mock_llm: MagicMock, mock_client: MagicMock) -> None:
        mock_llm.side_effect = Exception("Timeout")

        with pytest.raises(RuntimeError, match="ContextualizationAgent"):
            run_contextualization("texto", "texto")


class TestExtractionAgent:
    @patch("src.agents.extraction_agent._get_client")
    @patch("src.agents.extraction_agent._call_llm")
    def test_successful_extraction(
        self, mock_llm: MagicMock, mock_client: MagicMock
    ) -> None:
        raw_output = json.dumps(
            {
                "sections_changed": ["Cláusula 3 - Plazo"],
                "topics_touched": ["Duración"],
                "summary_of_the_change": "Plazo extendido de 12 a 24 meses.",
            }
        )
        mock_llm.return_value = (raw_output, 300)

        result, tokens = run_extraction("{}", "original", "amendment")

        assert isinstance(result, ContractChangeOutput)
        assert result.sections_changed == ["Cláusula 3 - Plazo"]
        assert tokens == 300

    @patch("src.agents.extraction_agent._get_client")
    @patch("src.agents.extraction_agent._call_llm")
    def test_invalid_json_from_llm(
        self, mock_llm: MagicMock, mock_client: MagicMock
    ) -> None:
        mock_llm.return_value = ("esto no es json", 100)

        with pytest.raises(json.JSONDecodeError):
            run_extraction("{}", "original", "amendment")

    @patch("src.agents.extraction_agent._get_client")
    @patch("src.agents.extraction_agent._call_llm")
    def test_missing_field_validation_error(
        self, mock_llm: MagicMock, mock_client: MagicMock
    ) -> None:
        raw_output = json.dumps(
            {
                "sections_changed": ["Sec 1"],
                "topics_touched": ["Topic 1"],
                # falta summary_of_the_change
            }
        )
        mock_llm.return_value = (raw_output, 100)

        with pytest.raises(ValueError):
            run_extraction("{}", "original", "amendment")

    @patch("src.agents.extraction_agent._get_client")
    @patch("src.agents.extraction_agent._call_llm")
    def test_api_error(self, mock_llm: MagicMock, mock_client: MagicMock) -> None:
        mock_llm.side_effect = Exception("API error")

        with pytest.raises(RuntimeError, match="ExtractionAgent"):
            run_extraction("{}", "original", "amendment")
