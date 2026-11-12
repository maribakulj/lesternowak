import subprocess
import sys

import pytest

from lesternowak import __version__
from lesternowak.cli import main


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_no_args_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "usage: lesternowak" in capsys.readouterr().out


def test_module_entry_point() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "lesternowak", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "lesternowak" in result.stdout
