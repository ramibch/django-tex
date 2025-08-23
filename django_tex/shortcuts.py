from django_tex.core import compile_template_to_pdf
from django_tex.response import PDFResponse


def render_to_pdf(request, template_name, context=None, filename=None, run_times=1):
    # Request is not needed and only included to make the signature conform to django's render function
    pdf = compile_template_to_pdf(template_name, context, run_times=run_times)
    return PDFResponse(pdf, filename=filename)
