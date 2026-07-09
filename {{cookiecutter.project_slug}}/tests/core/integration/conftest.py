{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" -%}
from pytest_factoryboy import LazyFixture, register

from tests.factories import TokenFactory, UserFactory

register(UserFactory, "user_1")
register(TokenFactory, "token_1", user=LazyFixture("user_1"))
{%- endif %}
