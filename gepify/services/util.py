import string
import random


def get_random_str(length):
    """Return random string with desired length."""

    return ''.join(
        random.choice(string.ascii_lowercase) for i in range(length))
