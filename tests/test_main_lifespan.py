import warnings

from app.main import create_app


def test_create_app_does_not_register_deprecated_on_event_handlers() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        app = create_app()

    assert app.router.lifespan_context is not None
