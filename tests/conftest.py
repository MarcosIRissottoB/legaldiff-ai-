from pathlib import Path

import pytest

from src.models import ContractChangeOutput

TEST_CONTRACTS_DIR = Path(__file__).parent.parent / "data" / "test_contracts"


@pytest.fixture
def contract_pairs() -> dict[int, dict[str, str]]:
    """Paths a los 3 pares de imágenes reales en data/test_contracts/."""
    return {
        1: {
            "original": str(TEST_CONTRACTS_DIR / "documento_1__original.jpg"),
            "amendment": str(TEST_CONTRACTS_DIR / "documento_1__enmienda.jpg"),
        },
        2: {
            "original": str(TEST_CONTRACTS_DIR / "documento_2__original.jpg"),
            "amendment": str(TEST_CONTRACTS_DIR / "documento_2__enmienda.jpg"),
        },
        3: {
            "original": str(TEST_CONTRACTS_DIR / "documento_3__original.jpg"),
            "amendment": str(TEST_CONTRACTS_DIR / "documento_3__enmienda.jpg"),
        },
    }


@pytest.fixture
def contract_image_bytes() -> bytes:
    """Lee bytes reales desde documento_1__original.jpg."""
    path = TEST_CONTRACTS_DIR / "documento_1__original.jpg"
    if not path.exists():
        pytest.skip("Test contracts not found in data/test_contracts/")
    return path.read_bytes()


@pytest.fixture
def valid_change_output() -> ContractChangeOutput:
    return ContractChangeOutput(
        sections_changed=["Cláusula 2 - Plazo", "Cláusula 3 - Pago"],
        topics_touched=["Duración", "Condiciones económicas"],
        summary_of_the_change=(
            "Se extiende el plazo de 12 a 24 meses y se incrementa "
            "el pago anual de USD 12.000 a USD 15.000."
        ),
    )


@pytest.fixture
def sample_original_text() -> str:
    """Texto real del contrato Par 1 original (TechNova/DataBridge)."""
    return (
        'CONTRATO DE LICENCIA DE SOFTWARE\n\n'
        'El presente Contrato de Licencia de Software ("Contrato") se celebra el 1 de marzo '
        'de 2024 entre TechNova S.A. ("Licenciante") y DataBridge Soluciones S.R.L. '
        '("Licenciatario").\n\n'
        "1. Otorgamiento de Licencia\n"
        'El Licenciante otorga al Licenciatario una licencia no exclusiva e intransferible '
        'para utilizar el software denominado "NovaAnalytics" únicamente para fines internos '
        "de la empresa.\n\n"
        "2. Plazo\n"
        "El presente contrato tendrá una duración de 12 meses a partir de la fecha de firma.\n\n"
        "3. Pago\n"
        "El Licenciatario se compromete a pagar al Licenciante una tarifa anual de licencia "
        "de USD 12.000, pagadera dentro de los 30 días posteriores a la recepción de la factura.\n\n"
        "4. Soporte\n"
        "El Licenciante brindará soporte técnico vía correo electrónico durante horario laboral.\n\n"
        "5. Terminación\n"
        "Cualquiera de las partes podrá rescindir el contrato mediante notificación escrita "
        "con 30 días de anticipación.\n\n"
        "6. Confidencialidad\n"
        "Ambas partes acuerdan mantener la confidencialidad de toda la información propietaria "
        "intercambiada durante la vigencia del contrato."
    )


@pytest.fixture
def sample_amendment_text() -> str:
    """Texto real de la enmienda Par 1 (TechNova/DataBridge)."""
    return (
        'CONTRATO DE LICENCIA DE SOFTWARE - ENMIENDA\n\n'
        'La presente enmienda modifica el Contrato de Licencia de Software celebrado el 1 de '
        'marzo de 2024 entre TechNova S.A. ("Licenciante") y DataBridge Soluciones S.R.L. '
        '("Licenciatario").\n\n'
        "1. Otorgamiento de Licencia\n"
        'El Licenciante otorga al Licenciatario una licencia no exclusiva para utilizar el '
        'software denominado "NovaAnalytics" para operaciones internas de negocio.\n\n'
        "2. Plazo\n"
        "El presente contrato tendrá una duración de 24 meses a partir de la fecha de firma.\n\n"
        "3. Pago\n"
        "El Licenciatario se compromete a pagar al Licenciante una tarifa anual de licencia "
        "de USD 15.000, pagadera dentro de los 30 días posteriores a la recepción de la factura.\n\n"
        "4. Soporte\n"
        "El Licenciante brindará soporte técnico vía correo electrónico y chat durante "
        "horario laboral.\n\n"
        "5. Terminación\n"
        "Cualquiera de las partes podrá rescindir el contrato mediante notificación escrita "
        "con 60 días de anticipación.\n\n"
        "6. Confidencialidad\n"
        "Ambas partes acuerdan mantener la confidencialidad de toda la información propietaria "
        "intercambiada durante la vigencia del contrato.\n\n"
        "7. Protección de Datos\n"
        "El Licenciante se compromete a cumplir con las normativas aplicables en materia de "
        "protección de datos en relación con la información del Licenciatario."
    )


@pytest.fixture
def expected_changes_pair1() -> dict:
    """Cambios esperados para Par 1 (Licencia Software) según ADR."""
    return {
        "sections": [
            "Plazo: 12→24 meses",
            "Pago: USD 12.000→15.000",
            "Soporte: email→email+chat",
            "Terminación: 30→60 días",
            "Nueva cláusula: Protección de Datos",
        ],
    }


@pytest.fixture
def expected_changes_pair2() -> dict:
    """Cambios esperados para Par 2 (Consultoría) según ADR."""
    return {
        "sections": [
            "Alcance: agregado análisis regulatorio",
            "Duración: 6→9 meses",
            "Honorarios: USD 8.000→9.500",
            "Entregables: mensuales→quincenales",
            "Nueva cláusula: Propiedad Intelectual",
        ],
    }


@pytest.fixture
def expected_changes_pair3() -> dict:
    """Cambios esperados para Par 3 (SaaS) según ADR."""
    return {
        "sections": [
            "Precio: USD 1.200→1.250",
            "Disponibilidad: 99,5%→99,9%",
            "Soporte: email→email+tickets",
        ],
    }


@pytest.fixture
def mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Setea variables de entorno para tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:4000")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test-pub")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test-secret")
    monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:3000")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("LEGALDIFF_API_KEY", "test-api-key")
