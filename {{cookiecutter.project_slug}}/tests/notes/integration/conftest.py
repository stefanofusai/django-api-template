from pytest_factoryboy import LazyFixture, register

from tests.factories import NoteFactory, UserFactory

register(UserFactory, "user_1")
register(NoteFactory, "note_1")
register(NoteFactory, "note_2")
register(NoteFactory, "note_owner_user_1", owner=LazyFixture("user_1"))
