"""CLI tests."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from modelbridge_cli.config import CONFIG_FILE, clear_config, load_config, save_config, show_config
from modelbridge_cli.main import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.json"
    monkeypatch.setattr("modelbridge_cli.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("modelbridge_cli.config.CONFIG_FILE", cfg_file)
    yield
    if cfg_file.exists():
        cfg_file.unlink()


def test_config_set_and_show():
    result = runner.invoke(app, ["config", "set", "url", "http://example:8000"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["config", "show"])
    assert "http://example:8000" in result.stdout


def test_config_mask_secrets():
    save_config({"api_key": "mb_super_secret_key_12345"})
    shown = show_config()
    assert "super_secret" not in shown["api_key"]
    assert "..." in shown["api_key"]


def test_config_clear():
    save_config({"url": "http://test"})
    runner.invoke(app, ["config", "clear"])
    assert load_config()["url"] == "http://localhost:8000"


def test_version():
    from modelbridge_cli import __version__
    assert __version__ == "1.0.0"


def test_governance_help():
    result = runner.invoke(app, ["governance", "--help"])
    assert result.exit_code == 0
    assert "policies" in result.stdout
