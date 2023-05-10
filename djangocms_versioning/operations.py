import uuid

from .signals import post_version_operation, pre_version_operation


def send_pre_version_operation(operation, version, **kwargs):
    """
    Signal emitter for before a version operation occurs.
    A token is emitted that will allow the pre and post emitted signals to be tied together.

    :param operation: Operation constants
    :param version: Version instance
    :param kwargs:
    :return: A unique token for the transaction
    """
    token = str(uuid.uuid4())
    pre_version_operation.send(
        sender=version.content_type.model_class(),
        operation=operation,
        token=token,
        obj=version,
        **kwargs
    )
    return token


def send_post_version_operation(operation, version, token, **kwargs):
    """
    Signal emitter for after a version operation occurs

    :param operation: Operation constants
    :param version: Version instance
    :param token: A unique token for the transaction
    :param kwargs:
    """
    post_version_operation.send(
        sender=version.content_type.model_class(),
        operation=operation,
        token=token,
        obj=version,
        **kwargs
    )
