"""Path helpers that resolve repository locations independent of cwd."""

from pathlib import Path


def project_root() -> Path:
    """Return the repository root by walking up from this file."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "configs").is_dir():
            return parent
    message = "Unable to locate project root containing pyproject.toml and configs/"
    raise RuntimeError(message)


def resolve_project_path(path: str | Path) -> Path:
    """Resolve a relative project path against the repository root."""
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate.resolve()
    return (project_root() / candidate).resolve()
