import json
from unittest.mock import MagicMock, patch

import pytest

from src.agents.contextualization_agent import run as run_contextualization
from src.agents.extraction_agent import run as run_extraction
from src.models import ContractChangeOutput


class TestContextualizationAgent:
    @patch("src.agents.contextualization_agent._get_llm")
    @patch("src.agents.contextualization_agent._invoke_llm")
    def test_successful_contextualization(
        self, mock_invoke: MagicMock, mock_llm: MagicMock
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
        mock_invoke.return_value = (context_map, 200)

        result, tokens = run_contextualization("texto original", "texto enmienda")

        assert "sections" in result
        assert tokens == 200

    @patch("src.agents.contextualization_agent._get_llm")
    @patch("src.agents.contextualization_agent._invoke_llm")
    def test_api_error(self, mock_invoke: MagicMock, mock_llm: MagicMock) -> None:
        mock_invoke.side_effect = Exception("Timeout")

        with pytest.raises(RuntimeError, match="ContextualizationAgent"):
            run_contextualization("texto", "texto")


class TestExtractionAgent:
    @patch("src.agents.extraction_agent._get_llm")
    @patch("src.agents.extraction_agent._invoke_llm")
    def test_successful_extraction(self, mock_invoke: MagicMock, mock_llm: MagicMock) -> None:
        raw_output = json.dumps(
            {
                "sections_changed": ["Cláusula 3 - Plazo"],
                "topics_touched": ["Duración"],
                "summary_of_the_change": "Plazo extendido de 12 a 24 meses.",
            }
        )
        mock_invoke.return_value = (raw_output, 300)

        result, tokens = run_extraction("{}", "original", "amendment")

        assert isinstance(result, ContractChangeOutput)
        assert result.sections_changed == ["Cláusula 3 - Plazo"]
        assert tokens == 300

    @patch("src.agents.extraction_agent._get_llm")
    @patch("src.agents.extraction_agent._invoke_llm")
    def test_invalid_json_from_llm(self, mock_invoke: MagicMock, mock_llm: MagicMock) -> None:
        mock_invoke.return_value = ("esto no es json", 100)

        with pytest.raises(json.JSONDecodeError):
            run_extraction("{}", "original", "amendment")

    @patch("src.agents.extraction_agent._get_llm")
    @patch("src.agents.extraction_agent._invoke_llm")
    def test_missing_field_validation_error(
        self, mock_invoke: MagicMock, mock_llm: MagicMock
    ) -> None:
        raw_output = json.dumps(
            {
                "sections_changed": ["Sec 1"],
                "topics_touched": ["Topic 1"],
                # falta summary_of_the_change
            }
        )
        mock_invoke.return_value = (raw_output, 100)

        with pytest.raises(ValueError):
            run_extraction("{}", "original", "amendment")

    @patch("src.agents.extraction_agent._get_llm")
    @patch("src.agents.extraction_agent._invoke_llm")
    def test_api_error(self, mock_invoke: MagicMock, mock_llm: MagicMock) -> None:
        mock_invoke.side_effect = Exception("API error")

        with pytest.raises(RuntimeError, match="ExtractionAgent"):
            run_extraction("{}", "original", "amendment")


class TestAgentsWithRealisticText:
    """Tests que usan texto real de contratos (fixtures sample_original/amendment_text)."""

    @patch("src.agents.contextualization_agent._get_llm")
    @patch("src.agents.contextualization_agent._invoke_llm")
    def test_contextualization_with_real_text(
        self,
        mock_invoke: MagicMock,
        mock_llm: MagicMock,
        sample_original_text: str,
        sample_amendment_text: str,
    ) -> None:
        context_map = json.dumps({"sections": [{"id": "clausula-2", "title": "Plazo"}]})
        mock_invoke.return_value = (context_map, 500)

        result, tokens = run_contextualization(sample_original_text, sample_amendment_text)

        assert "sections" in result
        assert tokens == 500
        call_args = mock_invoke.call_args[0]
        messages = call_args[1]
        assert "TechNova" in messages[1].content
        assert "DataBridge" in messages[1].content

    @patch("src.agents.extraction_agent._get_llm")
    @patch("src.agents.extraction_agent._invoke_llm")
    def test_extraction_with_real_text(
        self,
        mock_invoke: MagicMock,
        mock_llm: MagicMock,
        sample_original_text: str,
        sample_amendment_text: str,
        expected_changes_pair1: dict,
    ) -> None:
        raw_output = json.dumps(
            {
                "sections_changed": expected_changes_pair1["sections"],
                "topics_touched": ["Duración contractual", "Condiciones económicas"],
                "summary_of_the_change": "Cambios en plazo, pago, soporte, terminación y nueva cláusula.",
            }
        )
        mock_invoke.return_value = (raw_output, 800)

        result, tokens = run_extraction("{}", sample_original_text, sample_amendment_text)

        assert isinstance(result, ContractChangeOutput)
        assert len(result.sections_changed) == 5
        assert tokens == 800

    @patch("src.agents.contextualization_agent._get_llm")
    @patch("src.agents.contextualization_agent._invoke_llm")
    def test_contextualization_invalid_json_output(
        self,
        mock_invoke: MagicMock,
        mock_llm: MagicMock,
        sample_original_text: str,
        sample_amendment_text: str,
    ) -> None:
        mock_invoke.return_value = ("esto no es json válido", 100)

        with pytest.raises(ValueError, match="JSON válido"):
            run_contextualization(sample_original_text, sample_amendment_text)
