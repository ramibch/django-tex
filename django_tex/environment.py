from jinja2 import Environment

from django_tex.filters import FILTERS


def environment(**options):
    options.update(
        {
            "autoescape": None,
            "extensions": ["django_tex.extensions.GraphicspathExtension"],
        }
    )
    env = Environment(**options)
    env.filters.update(FILTERS)
    return env
