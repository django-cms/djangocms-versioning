from django.dispatch import Signal

pre_version_operation = Signal(
    providing_args=[
        "operation",
        "token",
        "obj",
    ]
)

post_version_operation = Signal(
    providing_args=[
        "operation",
        "token",
        "obj",
    ]
)
