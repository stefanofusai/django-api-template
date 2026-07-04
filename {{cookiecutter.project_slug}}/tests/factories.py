import factory

from apps.core.models import User


class UserFactory(factory.django.DjangoModelFactory):
    email = factory.Faker("email")
    username = factory.Sequence(lambda n: f"user-{n}")

    class Meta:
        model = User
