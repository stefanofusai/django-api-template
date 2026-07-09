import json
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, cast

from django.core.management.base import BaseCommand, CommandParser
from django.core.serializers.json import DjangoJSONEncoder

from apps.api.api import internal_api, v1_api

if TYPE_CHECKING:
    from ninja import NinjaAPI


class Command(BaseCommand):
    help = "Export an API's OpenAPI schema as JSON."

    apis: ClassVar[dict[str, NinjaAPI]] = {
        "internal": internal_api,
        "v1": v1_api,
    }

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--api", choices=sorted(self.apis), default="v1")
        parser.add_argument("--output", default=None)

    def handle(self, *_args: object, **options: object) -> None:
        api_name = cast("str", options["api"])
        output = cast("str | None", options["output"])
        schema = json.dumps(
            dict(self.apis[api_name].get_openapi_schema()),
            cls=DjangoJSONEncoder,
            indent=2,
            sort_keys=True,
        )

        if output is None:
            self.stdout.write(schema)

        else:
            Path(output).write_text(schema + "\n", encoding="utf-8")
