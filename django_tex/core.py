import os
import tempfile
from subprocess import PIPE, CalledProcessError, run

from django.conf import settings
from django.template.loader import get_template

from django_tex.exceptions import TexError

DEFAULT_INTERPRETER = "lualatex"


def run_tex(source, template_name=None, run_times=1):
    with tempfile.TemporaryDirectory() as tempdir:
        return run_tex_in_directory(
            source,
            tempdir,
            template_name=template_name,
            run_times=run_times,
        )


def run_tex_in_directory(source, directory, template_name=None, run_times=1):
    filename = "texput.tex"
    command = getattr(settings, "LATEX_INTERPRETER", DEFAULT_INTERPRETER)
    latex_interpreter_options = getattr(settings, "LATEX_INTERPRETER_OPTIONS", "")
    with open(os.path.join(directory, filename), "x", encoding="utf-8") as f:
        f.write(source)
    args = f"{command} -interaction=batchmode {latex_interpreter_options} {filename}"
    try:
        for _ in range(run_times):
            run(
                args,
                shell=True,
                stdout=PIPE,
                stderr=PIPE,
                check=True,
                cwd=directory,
            )
    except CalledProcessError as called_process_error:
        try:
            with open(
                os.path.join(directory, "texput.log"), "r", encoding="utf-8"
            ) as f:
                log = f.read()
        except FileNotFoundError:
            raise called_process_error
        else:
            raise TexError(log=log, source=source, template_name=template_name)
    with open(os.path.join(directory, "texput.pdf"), "rb") as f:
        pdf = f.read()
    return pdf


def compile_template_to_pdf(template_name, context, run_times=1):
    source = render_template_with_context(template_name, context)
    return run_tex(source, template_name=template_name, run_times=run_times)


def render_template_with_context(template_name, context):
    template = get_template(template_name, using="tex")
    return template.render(context)
