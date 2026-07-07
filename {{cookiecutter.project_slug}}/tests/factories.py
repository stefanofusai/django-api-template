import factory

from apps.core.models import User
{%- if cookiecutter.use_example_api == "yes" %}
from apps.notes.models import Note
{%- endif %}


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f"user-{n}")
    email = factory.Sequence(lambda n: f"user-{n}@example.com")

    class Meta:
        model = User
{%- if cookiecutter.use_example_api == "yes" %}


class NoteFactory(factory.django.DjangoModelFactory):
    owner = factory.SubFactory(UserFactory)
    title = factory.Faker("sentence")
    body = factory.Faker("paragraph")

    class Meta:
        model = Note
{%- endif %}
