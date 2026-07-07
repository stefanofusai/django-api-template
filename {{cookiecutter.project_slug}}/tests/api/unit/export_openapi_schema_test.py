import json
from io import StringIO
from pathlib import Path

from django.core.management import call_command


def test_export_openapi_schema_writes_file_when_output_given(tmp_path: Path) -> None:
    output_path = tmp_path / "schema.json"

    call_command("export_openapi_schema", "--output", output_path)

    schema = output_path.read_text(encoding="utf-8")
    assert schema.endswith("\n")
    assert json.loads(schema)["openapi"]


def test_export_openapi_schema_writes_valid_json_to_stdout_when_no_output() -> None:
    stdout = StringIO()

    call_command("export_openapi_schema", "--api=internal", stdout=stdout)

    schema = json.loads(stdout.getvalue())
    assert schema["openapi"]
    assert "/api/health" in schema["paths"]
