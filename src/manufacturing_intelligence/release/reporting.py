"""Markdown outputs for the final portfolio release."""

from __future__ import annotations

DISCLAIMER = (
    "Local-first synthetic portfolio evidence only. No Azure, Power BI, Fabric, OpenAI, "
    "or external service is deployed or called."
)


def release_docs() -> dict[str, str]:
    return {
        "final-release-notes.md": _doc("Final Release Notes", "Milestones 1-12 are complete."),
        "repository-evidence-map.md": _doc(
            "Repository Evidence Map",
            "Evidence is indexed under outputs/release/final_evidence_index.csv.",
        ),
        "local-first-boundary.md": _doc(
            "Local-First Boundary",
            "All implementation and validation run locally from tracked synthetic evidence.",
        ),
        "synthetic-data-boundary.md": _doc(
            "Synthetic Data Boundary",
            "No real customers, suppliers, employees, plants, or operations are represented.",
        ),
        "validation-and-quality-gates.md": _doc(
            "Validation And Quality Gates",
            "Quality, milestone validators, release validation, and validate-all are required.",
        ),
        "interview-guide.md": _doc(
            "Interview Guide",
            "Explain the platform as an end-to-end Azure-mapped manufacturing "
            "intelligence project.",
        ),
        "limitations.md": _doc(
            "Limitations",
            "The repository is not a production deployment and has no live service integration.",
        ),
    }


def release_reports(run_id: str) -> dict[str, str]:
    return {
        "final_portfolio_summary.md": _report(
            "Final Portfolio Summary",
            run_id,
            "End-to-end manufacturing intelligence portfolio with deterministic evidence.",
        ),
        "final_evidence_register.md": _report(
            "Final Evidence Register",
            run_id,
            "See outputs/release/final_evidence_index.csv for the machine-readable register.",
        ),
        "final_validation_report.md": _report(
            "Final Validation Report",
            run_id,
            "Quality, validators, release validation, and validate-all are local checks.",
        ),
        "final_release_readiness_report.md": _report(
            "Final Release Readiness Report",
            run_id,
            "Release readiness label: portfolio_release_ready.",
        ),
        "interview_talking_points.md": _interview_report(run_id),
        "cv_project_summary.md": _cv_report(run_id),
        "recruiter_readme_summary.md": _recruiter_report(run_id),
    }


def _doc(title: str, body: str) -> str:
    return f"# {title}\n\n{body}\n\n{DISCLAIMER}\n"


def _report(title: str, run_id: str, body: str) -> str:
    return f"# {title}\n\nRun ID: `{run_id}`\n\n{body}\n\n{DISCLAIMER}\n"


def _interview_report(run_id: str) -> str:
    return (
        f"# Interview Talking Points\n\nRun ID: `{run_id}`\n\n"
        "- What did I build: an end-to-end synthetic manufacturing intelligence platform.\n"
        "- What would deploy in Azure: Event Hubs, ADLS, ADX, Fabric/Synapse, AML, "
        "AI Foundry, AI Search, Azure OpenAI, Monitor, Purview, Key Vault, Entra ID, "
        "and Power BI as reference services.\n"
        "- How do I know it works: deterministic manifests, lineage, tests, validators, "
        "and release catalogues.\n"
        "- Production gaps: live security hardening, scale testing, real data contracts, "
        "service deployment, and operational ownership.\n\n"
        f"{DISCLAIMER}\n"
    )


def _cv_report(run_id: str) -> str:
    return (
        f"# CV Project Summary\n\nRun ID: `{run_id}`\n\n"
        "Built a local-first Azure-mapped manufacturing intelligence platform covering "
        "synthetic data generation, governed ingestion, forecasting, inventory scoring, "
        "quality analytics, predictive maintenance, monitoring, deterministic GenAI, "
        "Power BI-ready outputs, and Azure architecture blueprints.\n\n"
        "- Implemented deterministic pipelines with manifests, lineage, and CI validation.\n"
        "- Produced 12 milestone evidence packs with 145 passing tests at final baseline.\n"
        "- Created reference-only Azure architecture and release-readiness catalogues.\n\n"
        "Stack: Python, pandas, scikit-learn, PyYAML, pytest, Ruff, mypy, GitHub Actions, "
        "Mermaid, Bicep, Terraform blueprint files.\n\n"
        f"{DISCLAIMER}\n"
    )


def _recruiter_report(run_id: str) -> str:
    return (
        f"# Recruiter README Summary\n\nRun ID: `{run_id}`\n\n"
        "This project demonstrates Data Scientist, ML Engineer, Data Engineer, Analytics "
        "Engineer, Azure Data/AI Engineer, and MLOps Engineer skills through a complete "
        "manufacturing analytics portfolio.\n\n"
        f"{DISCLAIMER}\n"
    )
