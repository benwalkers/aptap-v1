"""Packaging regression checks for the lean local environment."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pr_evaluation_is_packaged():
    assert (ROOT / "scripts/benchmark_pr_curves.py").is_file()
    assert (ROOT / "scripts/workflows/14_evaluate_pr_curves.sh").is_file()


def test_three_dependency_profiles_are_self_contained():
    expected = {
        "requirements.txt",
        "requirements-minilm.txt",
        "requirements-spark.txt",
    }
    assert {p.name for p in ROOT.glob("requirements*.txt")} == expected

    local = (ROOT / "requirements.txt").read_text()
    for package in ("pytest", "numpy", "scikit-learn", "matplotlib"):
        assert package in local
    assert "-r requirements-dev.txt" not in local
    assert "-r requirements-eval.txt" not in local

    minilm = (ROOT / "requirements-minilm.txt").read_text()
    assert "sentence-transformers" in minilm

    spark = (ROOT / "requirements-spark.txt").read_text()
    assert "pyspark" in spark


def test_setup_and_optional_scripts_use_correct_profiles():
    setup = (ROOT / "scripts/workflows/00_setup_venv.sh").read_text()
    optional = (ROOT / "scripts/workflows/08_optional_install_minilm.sh").read_text()
    assert "-r requirements.txt" in setup
    assert "-r requirements-minilm.txt" in optional
