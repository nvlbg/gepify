import string
import random


def get_random_str(length):
    return ''.join(
        random.choice(string.ascii_lowercase) for i in range(length))
