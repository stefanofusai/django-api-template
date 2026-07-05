from collections.abc import Callable


def public[View: Callable[..., object]](view: View) -> View:
    return view
