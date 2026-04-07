import pytest
from pydantic import ValidationError

from src.models import ContractChangeOutput


class TestContractChangeOutput:
    def test_valid_output(self, valid_change_output: ContractChangeOutput) -> None:
        assert len(valid_change_output.sections_changed) == 2
        assert isinstance(valid_change_output.summary_of_the_change, str)

    def test_missing_sections_changed(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ContractChangeOutput(
                topics_touched=["Duración"],
                summary_of_the_change="Cambio de plazo.",
            )
        assert "sections_changed" in str(exc_info.value)

    def test_missing_topics_touched(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ContractChangeOutput(
                sections_changed=["Cláusula 3"],
                summary_of_the_change="Cambio.",
            )
        assert "topics_touched" in str(exc_info.value)

    def test_missing_summary(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ContractChangeOutput(
                sections_changed=["Cláusula 3"],
                topics_touched=["Duración"],
            )
        assert "summary_of_the_change" in str(exc_info.value)

    def test_empty_lists_are_valid(self) -> None:
        output = ContractChangeOutput(
            sections_changed=[],
            topics_touched=[],
            summary_of_the_change="Sin cambios detectados.",
        )
        assert output.sections_changed == []
        assert output.topics_touched == []

    def test_serialization_roundtrip(
        self, valid_change_output: ContractChangeOutput
    ) -> None:
        data = valid_change_output.model_dump()
        reconstructed = ContractChangeOutput.model_validate(data)
        assert reconstructed == valid_change_output

    def test_model_validate_from_dict(self) -> None:
        raw = {
            "sections_changed": ["Sec 1"],
            "topics_touched": ["Topic 1"],
            "summary_of_the_change": "Detalle.",
        }
        output = ContractChangeOutput.model_validate(raw)
        assert output.sections_changed == ["Sec 1"]
