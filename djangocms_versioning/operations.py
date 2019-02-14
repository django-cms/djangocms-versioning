# -*- coding: utf-8 -*-
import uuid

from .models import Version
from .signals import post_version_operation, pre_version_operation


def send_pre_version_operation(operation, sender=Version, **kwargs):
    token = str(uuid.uuid4())
    pre_version_operation.send(
        sender=sender,
        operation=operation,
        token=token,
        **kwargs
    )
    return token


def send_post_version_operation(operation, token, sender=Version, **kwargs):
    post_version_operation.send(
        sender=sender,
        operation=operation,
        token=token,
        **kwargs
    )
