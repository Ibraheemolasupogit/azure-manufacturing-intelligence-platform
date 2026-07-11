"""Architecture mapping table builders."""

from __future__ import annotations

from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.architecture import artefacts


def table_specs() -> dict[str, list[dict[str, Any]]]:
    return {
        "azure_service_mapping": artefacts.SERVICE_MAPPING_ROWS,
        "security_controls_matrix": artefacts.SECURITY_ROWS,
        "data_architecture_layers": artefacts.DATA_LAYER_ROWS,
        "mlops_mapping": artefacts.MLOPS_ROWS,
        "genai_architecture_mapping": artefacts.GENAI_ROWS,
        "operations_mapping": artefacts.OPERATIONS_ROWS,
        "cost_considerations": artefacts.COST_ROWS,
    }


def build_tables() -> dict[str, pd.DataFrame]:
    return {name: pd.DataFrame(rows) for name, rows in table_specs().items()}


def architecture_spec_payload() -> dict[str, Any]:
    return {
        "tables": table_specs(),
        "adrs": artefacts.ADR_ROWS,
        "docs": artefacts.architecture_docs(),
        "diagrams": artefacts.diagrams(),
        "infra": artefacts.infra_files(),
    }
