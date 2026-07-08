import factory

from apps.core.models import {% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}Token, User{% else %}User{% endif %}
{%- if cookiecutter.use_example_api == "yes" %}
from apps.notes.models import Note
{%- endif %}


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
    user = factory.SubFactory(UserFactory)
    digest = factory.Sequence(lambda n: Token.hash(f"test-token-{n}"))
    name = factory.Sequence(lambda n: f"token-{n}")
    prefix = factory.Sequence(lambda n: f"{n:012x}")

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
