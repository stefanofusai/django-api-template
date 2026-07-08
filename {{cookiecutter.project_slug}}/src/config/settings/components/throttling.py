from config.settings import env

API_THROTTLE_ANON_RATE = env("API_THROTTLE_ANON_RATE", default=None)
API_THROTTLE_USER_RATE = env("API_THROTTLE_USER_RATE", default=None)
NINJA_EXTRA = {
    "THROTTLE_RATES": dict(
        filter(
            lambda rate: rate[1] is not None,
            (
                ("anon", API_THROTTLE_ANON_RATE),
                ("user", API_THROTTLE_USER_RATE),
            ),
        )
    )
}
