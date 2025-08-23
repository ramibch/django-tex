# django-tex

django-tex is a simple Django app to render LaTeX templates and compile
them into PDF files.

Django-tex requires a local LaTeX installation and uses the jinja2 
templating engine for template rendering.

## Installation

`django-tex` is available on [pypi.org](https://pypi.org/project/django-tex/). It can be installed by:

```pip install django_tex```

## Quick start

1. Add "django_tex" to your `INSTALLED_APPS` setting:

```python
INSTALLED_APPS = [
    ...
    'django_tex',
]
```

2. Configure a template engine named `tex` in settings.py:

```python
TEMPLATES = [
    {
        'NAME': 'tex',
        'BACKEND': 'django_tex.engine.TeXEngine', 
        'APP_DIRS': True,
    },
]
```

3. Create a LaTeX template in your template directory:

```tex
# test.tex
\documentclass{article}

\begin{document}

\section{ {{- foo -}} }

\end{document}
```

4. Use "compile_template_to_pdf" in your code to get the PDF file as a bytes object:

```python
from django_tex.core import compile_template_to_pdf

template_name = 'test.tex'
context = {'foo': 'Bar'}
PDF = compile_template_to_pdf(template_name, context)
```

Or use `render_to_pdf` to generate a HTTPResponse containing the PDF file:

```python
from django_tex.shortcuts import render_to_pdf

def view(request):
    template_name = 'test.tex'
    context = {'foo': 'Bar'}
    return render_to_pdf(request, template_name, context, as_attachment=True, filename='test.pdf')
```

## Some notes on usage

### Latex binary

The default LaTeX interpreter is set to `lualatex`. This can be changed by the setting
`LATEX_INTERPRETER`, for instance: `LATEX_INTERPRETER = 'pdflatex'`. Of course, the interpreter needs
to be installed on your system for `django-tex` to work properly.

### Interpreter arguments

You can pass additional arguments to the latex interpreter by using the `LATEX_INTERPRETER_OPTIONS` setting.

### Whitespace control

Since django-tex uses jinja, you can use jinja's whitespace control in 
LaTeX templates. For example, `\section{ {{ foo }} }` would be rendered as 
`\section{ Bar }` with the above context; `\section{ {{- foo -}} }`, however, 
gets rendered nicely as `\section{Bar}`.

### Built-in filters

Django's built-in filters are available. So you can use `{{ foo|date('d. F Y') }}` 
to get `1. Januar 2018`, for instance.

Further, django-tex adds the custom filter `localize` to the jinja environment.
This runs its input through `django.utils.formats.localize_input` to
create a localized representation. The output depends on the `USE_L10N` and `LANGUAGE_CODE`
settings. Use the filter like this: `{{ foo|localize }}`.

If you want to convert linebreaks into LaTeX linebreaks (`\\`), use the `linebreaks` filter (`{{ foo | linebreaks }}`).
### Escaping LaTeX special characters

To escape LaTeX special characters, use the `latex_escape` filter, i.e. `{{ foo | latex_escape }}`s. 
This escapes the following characters: `&$%#_{}\^~` 
([see also this SO question](https://tex.stackexchange.com/questions/34580/escape-character-in-latex))
Using this filter all printable character should lead to a successful LaTeX build.
Spacing for the characters `\^~` is automatically adopted as an end user would expect it.

Please note Jinja's autoescaping is turned off in the default `django-tex` environment.

### Custom filters

Custom filters can be defined as explained in  the jinja documentation [here](http://jinja.pocoo.org/docs/2.10/api/#custom-filters). For example, the following filter formats a
`datetime.timedelta` object as a hh:mm string:

```python
def hhmm_format(value):
    total_seconds = value.total_seconds()
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return '{:n}:{:02n}'.format(hours, minutes)
```

The filter has to be added to a custom environment and the `django-tex` templating engine has to be made aware
of the environment. This can be achieved, for example, by defining a custom environment callable in an `environment.py` module in your app:

```python
# environment.py
from django_tex.environment import environment

def hhmm_format(value):
    pass # as above

def my_environment(**options):
    env = environment(**options)
    env.filters.update({
        'hhmm_format': hhmm_format
    })
    return env
```

... and passing the dotted path to `my_environment` to the `TEMPLATES` settings:

```python
# settings.py

TEMPLATES = [
    {
        'NAME': 'tex',
        'BACKEND': 'django_tex.engine.TeXEngine', 
        'APP_DIRS': True,
        'OPTIONS': {
            'environment': 'myapp.environment.my_environment',
        }
    },
]
```

### Including graphics files

Graphics can be included in LaTeX documents using the `\includegraphics{<filename>}` command provided
by the `graphicx` package. Normally, LaTeX looks for graphics files in the current working directory, i.e. the 
directory including the source `.tex` file. The problem here is that `django-tex` creates a temporary directory to
store the source file so that the LaTeX compiler does not see any graphics files provided by the Django application.
This problem can be solved by specifying the absolute path to one or more directories including the graphics files 
using the `\graphicspath` command.

`Django-tex` allows the user to specify the absolute paths to one or more directories in the `LATEX_GRAPHICSPATH` 
setting. This setting should contain a list of one or more paths:

```python
# settings.py

LATEX_GRAPHICSPATH = ['c:\foo\bar', 'c:\bar\foo']
```

Of course, a good way of constructing those paths is to use `os.path.join(BASE_DIR, <path>)`.

Using the template tag `{% graphicspath %}`, the correct `\graphicspath` command can be inserted into the `.tex` 
template. In the above case, `{% graphicspath %}` turns into `\graphicspath{ {"c:/foo/bar/"} {"c:/bar/foo/"} }`. Use  
`{% graphicspath %}` like this:

```
\documentclass{article}
\usepackage{graphicx}

{% graphicspath %}

\begin{document}

\includegraphics{foo}

\end{document}
```

If `LATEX_GRAPHICSPATH` is not specified, `django-tex` takes the `BASE_DIR` instead.

Note: There might be a problem if the path to the graphics directory contains whitespaces. To my knowledge, `lualatex` cannot handle whitespaces in the `\graphicspath` command, but `pdflatex` can.
