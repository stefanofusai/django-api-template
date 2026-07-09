import factory

from apps.core.models import {% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}Token, User{% else %}User{% endif %}
{%- if cookiecutter.use_example_api == "yes" %}
from apps.notes.models import Note
{%- endif %}
{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}
TEST_TOKEN_SECRET = "test-token-secret"  # noqa: S105
{% endif %}

class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f"user-{n}")
    email = factory.Sequence(lambda n: f"user-{n}@example.com")
    is_active = True
    is_staff = False
    is_superuser = False

    class Meta:
        model = User
{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}


class TokenFactory(factory.django.DjangoModelFactory):
    expires_at = None
    last_used_at = None
    revoked_at = None
    name = factory.Faker("sentence")
    prefix = factory.Sequence(lambda n: f"{n:012x}")
    digest = factory.LazyAttribute(
        lambda token: Token.hash(f"pat_{token.prefix}_{TEST_TOKEN_SECRET}")
    )
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = Token
{%- endif %}
{%- if cookiecutter.use_example_api == "yes" %}


class NoteFactory(factory.django.DjangoModelFactory):
    owner = factory.SubFactory(UserFactory)
    title = factory.Faker("sentence")
    body = factory.Faker("paragraph")

    class Meta:
        model = Note
{%- endif %}
