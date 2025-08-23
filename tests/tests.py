import datetime
from decimal import Decimal

from django.test import TestCase
from django.test.utils import override_settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.template import engines

from django_tex.core import (
    run_tex,
    compile_template_to_pdf,
    render_template_with_context,
)
from django_tex.exceptions import TexError

from django_tex.shortcuts import render_to_pdf

from .models import TemplateFile


class RunningTex(TestCase):
    """
    Tests calling latex compiler
    """

    def test_run_tex(self):
        """Call different LaTex interpreters with very simple template"""
        source = "\
        \\documentclass{article}\n\
        \\begin{document}\n\
        This is a test!\n\
        \\end{document}"
        interpreters = ["pdflatex", "latexmk -pdf", "lualatex"]
        for name in interpreters:
            with self.subTest(name=name):
                with self.settings(LATEX_INTERPRETER=name):
                    pdf = run_tex(source)
                    self.assertIsNotNone(pdf)

    @override_settings(LATEX_INTERPRETER="does_not_exist")
    def test_wrong_latex_interpreter(self):
        """Using an unknown interpreter raises an Exception"""
        source = "\
        \\documentclass{article}\n\
        \\begin{document}\n\
        This is a test!\n\
        \\end{document}"

        with self.assertRaises(Exception):
            run_tex(source)  # should raise


class Exceptions(TestCase):
    """
    Tests custom exceptions
    """

    def test_exception_emergency_stop(self):
        source = "\
        \\documentclass{article}\n\
        \\begin{document}\n\
        This is a test!\n"

        with self.assertRaises(TexError) as cm:
            run_tex(source)

        self.assertRegex(cm.exception.log, r"^This is Lua")
        self.assertRegex(cm.exception.message, r"^! Emergency stop")
        self.assertRegex(
            cm.exception.message,
            r"(End of file on the terminal\!$)|(job aborted, no legal \\end found)",
        )  # First alternative applies
        # if tex source is given to
        # pdflatex via stdin.
        # Second, if tex source is
        # given as filename

    @override_settings(LATEX_INTERPRETER="pdflatex")
    def test_pdflatex_exceptions(self):
        source = "\
        \\documentclass{article}\n\
        \\begin{document}\n\
        This is a test!\n"

        with self.assertRaises(TexError) as cm:
            run_tex(source)

        self.assertRegex(cm.exception.log, r"^This is pdf")
        self.assertRegex(cm.exception.message, r"^! Emergency stop")
        self.assertRegex(
            cm.exception.message,
            r"(End of file on the terminal\!$)|(job aborted, no legal \\end found)",
        )  # First alternative applies
        # if tex source is given to
        # pdflatex via stdin.
        # Second, if tex source is
        # given as filename

    def test_exception_unknown_command(self):
        source = "\
        \\documentclass{article}\n\
        \\begin{document}\n\
        \\unknown{command}\n\
        \\end{document}\n"

        with self.assertRaises(TexError) as cm:
            run_tex(source)

        self.assertRegex(cm.exception.log, r"^This is Lua")
        self.assertRegex(cm.exception.message, r"^! Undefined control sequence")
        self.assertRegex(cm.exception.message, r"l\.3")

    def test_template_debug(self):
        source = (
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "\\unknown{command}\n"
            "\\end{document}\n"
        )

        with self.assertRaises(TexError) as cm:
            run_tex(source)

        template_debug = cm.exception.template_debug

        self.assertEqual(template_debug["during"], "\\unknown{command}")
        self.assertEqual(template_debug["line"], 3)

    def test_template_error_context(self):
        source = (
            "\\documentclass{article}\n"
            "\n"
            "\n"
            "\n"
            "\n"
            "\\begin{document}\n"
            "\\unknown{command}\n"
            "\n"
            "\n"
            "\\end{document}\n"
        )

        with self.assertRaises(TexError) as cm:
            run_tex(source)

        message = cm.exception.message

        expected_context = (
            " 2 \n"
            " 3 \n"
            " 4 \n"
            " 5 \n"
            " 6 \\begin{document}\n"
            " 7 \\unknown{command}\n"
            " 8 \n"
            " 9 \n"
            "10 \\end{document}"
        )

        self.assertIn(expected_context, message)


class RenderingTemplates(TestCase):
    """
    Tests rendering a template file with context to a string

    TODO: Add a test for custom template file locations.
    """

    def test_render_template(self):
        template_name = "tests/test.tex"
        context = {
            "test": "a simple test",
            "number": Decimal("1000.10"),
            "date": datetime.date(2017, 10, 25),
            "names": ["Arjen", "Robert", "Mats"],
        }
        output = render_template_with_context(template_name, context)
        self.assertIn("\\section{a simple test}", output)
        self.assertIn("This is a number: 1000,10.", output)
        self.assertIn("And this is a date: 25.10.2017.", output)
        self.assertIn("\\item Arjen", output)

    def test_render_template_from_custom_directory(self):
        template_name = "custom_directory_test.tex"
        context = {"foo": "bar"}
        output = render_template_with_context(template_name, context)
        self.assertIn("bar", output)


class CompilingTemplates(TestCase):
    """
    Tests compiling a template file with a context to a pdf file
    """

    def test_compile_template_to_pdf(self):
        """test compile_template_to_pdf

        - accepts template name and context
        - context may contain unicode characters
        - produces pdf file
        """
        template_name = "tests/test.tex"
        context = {
            "test": "a simple test",
            "number": Decimal("1000.10"),
            "date": datetime.date(2017, 10, 25),
            "names": ["Arjen", "Robert", "Mats", "äüößéèô♞Ⅷ"],
        }
        pdf = compile_template_to_pdf(template_name, context)
        self.assertIsNotNone(pdf)

    @override_settings(LATEX_INTERPRETER="pdflatex")
    def test_compile_template_with_graphics_pdflatex(self):
        template_name = "tests/test_graphics.tex"
        context = {}
        pdf = compile_template_to_pdf(template_name, context)
        self.assertIsNotNone(pdf)


class TemplateLanguage(TestCase):
    """
    Tests features such as whitespace control and filters
    """

    def render_template(self, template_string, context={}, using="tex"):
        engine = engines[using]
        template = engine.from_string(template_string)
        return template.render(context)

    def test_whitespace_control(self):
        context = {"foo": "bar"}
        template_string = "\\section{ {{- foo -}} }"
        output = self.render_template(template_string, context)
        self.assertEqual(output, "\\section{bar}")

    def test_localization(self):
        template_string = "{{ foo|localize }}"
        parameters = [
            ("en", Decimal("1000.10"), "1000.10"),
            ("de-de", Decimal("1000.10"), "1000,10"),
            ("de-de", datetime.date(2017, 10, 25), "25.10.2017"),
        ]
        for lang, value, expected in parameters:
            with self.subTest(lang=lang, value=value):
                with self.settings(LANGUAGE_CODE=lang):
                    output = self.render_template(template_string, {"foo": value})
                    self.assertEqual(output, expected)

    @override_settings(LANGUAGE_CODE="de-de")
    def test_format_long_date(self):
        context = {"foo": datetime.date(2017, 10, 25)}
        template_string = "{{ foo | date('d. F Y') }}"
        # template_string="{{ '{:%d. %B %Y}'.format(foo) }}"
        output = self.render_template(template_string, context)
        self.assertEqual(output, "25. Oktober 2017")

    def test_rendering_unicode(self):
        context = {"foo": "äüßéô"}
        template_string = "{{ foo }}"
        output = self.render_template(template_string, context)
        self.assertEqual(output, "äüßéô")

    def test_escape(self):
        template_string = "{{ value | latex_escape }}"
        parameters = [
            ("&", "\\&"),
            ("%", "\\%"),
            ("$", "\\$"),
            ("#", "\\#"),
            ("_", "\\_"),
            ("{", "\\{"),
            ("}", "\\}"),
            ("~", "\\textasciitilde{}"),
            ("^", "\\textasciicircum{}"),
            ("\\", "\\textbackslash{}"),
            ("\\\\", "\\textbackslash{}\\textbackslash{}"),
            ("foo", "foo"),
        ]
        for value, expected in parameters:
            with self.subTest(value):
                output = self.render_template(template_string, {"value": value})
                self.assertEqual(output, expected)

    def test_linebreaks(self):
        context = {
            "brecht": "Ich sitze am Straßenhang." + "\nDer Fahrer wechselt das Rad."
        }
        template_string = "{{ brecht | linebreaks }}"
        output = self.render_template(template_string, context)
        self.assertEqual(
            output, r"Ich sitze am Straßenhang.\\" + "\nDer Fahrer wechselt das Rad."
        )
        # Render with default django renderer
        output = self.render_template(template_string, context, using="django")
        self.assertHTMLEqual(
            output,
            "<p>Ich sitze am Straßenhang.<br>" + "Der Fahrer wechselt das Rad.</p>",
        )

    @override_settings(
        TEMPLATES=[
            {
                "NAME": "tex",
                "BACKEND": "django_tex.engine.TeXEngine",
                "OPTIONS": {"environment": "tests.environment.test_environment"},
            }
        ]
    )
    def test_custom_filters(self):
        context = {
            "duration": datetime.timedelta(minutes=90),
        }
        template_string = "{{ duration | hhmm_format }}"
        output = self.render_template(template_string, context)
        self.assertEqual("1:30", output)

    @override_settings(LATEX_GRAPHICSPATH=["c:\\foo\\bar", "c:\\bar baz\\foo"])
    def test_graphicspath(self):
        template_string = "{% graphicspath %}"
        with override_settings(LATEX_INTERPRETER="pdflatex"):
            output = self.render_template(template_string)
            self.assertEqual(
                output, '\\graphicspath{ {c:/foo/bar/} {"c:/bar baz/foo/"} }'
            )
        with override_settings(LATEX_INTERPRETER="lualatex"):
            output = self.render_template(template_string)
            self.assertEqual(
                output, "\\graphicspath{ {c:/foo/bar/} {c:/bar baz/foo/} }"
            )


class Models(TestCase):
    """
    TeXTemplateFile contains the relative path to a tex template (e.g. django_tex/test.tex)
    and validates if this template can be loaded.abs

    Since TeXTemplateFile is an abstract base class, it is used here in a subclassed version 'TemplateFile'
    """

    def test_validation(self):
        TemplateFile(title="valid", name="tests/test.tex").full_clean()

        with self.assertRaises(ValidationError):
            TemplateFile(title="invalid", name="template/doesnt.exist").full_clean()


class Views(TestCase):
    def test_render_to_pdf(self):
        request = None  # request is only needed to make the signature of render_to_pdf similar to the signature of django's render function
        template_name = "tests/test.tex"
        context = {
            "test": "a simple test",
            "number": Decimal("1000.10"),
            "date": datetime.date(2017, 10, 25),
            "names": ["Arjen", "Robert", "Mats"],
        }
        response = render_to_pdf(request, template_name, context, filename="test.pdf")
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(response["Content-Disposition"], 'inline; filename="test.pdf"')

    def test_render_to_pdf_content_dispositions(self):
        request = None  # request is only needed to make the signature of render_to_pdf similar to the signature of django's render function
        template_name = "tests/test.tex"
        context = {
            "test": "a simple test",
            "number": Decimal("1000.10"),
            "date": datetime.date(2017, 10, 25),
            "names": ["Arjen", "Robert", "Mats"],
        }
        response = render_to_pdf(request, template_name, context, filename="test.pdf")
        self.assertEqual(response["Content-Disposition"], 'inline; filename="test.pdf"')

        response = render_to_pdf(request, template_name, context, as_attachment=True, filename="test.pdf")
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="test.pdf"')

        response = render_to_pdf(request, template_name, context, as_attachment=True)
        self.assertEqual(response["Content-Disposition"], 'attachment')

        response = render_to_pdf(request, template_name, context)
        self.assertFalse("Content-Disposition" in response)
