import re

error_patterns = [
    r"^\!.*?l\.(?P<lineno>\d+).*?$",
    r"^\! Emergency stop.*?\*{3}.*?$",
    r"^\!.*?$",
]


ERROR = re.compile(r"|".join(error_patterns), re.DOTALL + re.MULTILINE)


class TexError(Exception):
    def __init__(self, log, source, template_name=None):
        self.log = log
        self.source = source
        self.source_lines = source.splitlines()

        mo = ERROR.search(self.log)

        self.message = mo.group() or "No error message found."

        if mo and mo.group("lineno"):
            try:
                lineno = int(mo.group("lineno")) - 1
                total = len(self.source_lines)

                # Ensure `lineno` is within bounds
                if 0 <= lineno < total:
                    top = max(0, lineno - 5)
                    bottom = min(lineno + 5, total)

                    # Ensure `top` does not exceed total lines
                    if top >= total:
                        top = max(0, total - 10)  # Shift back
                        bottom = total

                    source_lines = list(
                        enumerate(self.source_lines[top:bottom], top + 1)
                    )

                    # Check if `source_lines` is empty
                    if source_lines and 0 <= (lineno - top) < len(source_lines):
                        line, during = source_lines[lineno - top]
                    else:
                        line, during = lineno + 1, "[No source available]"

                    self.template_debug = {
                        "name": template_name,
                        "message": self.message,
                        "source_lines": source_lines,
                        "line": line,
                        "before": "",
                        "during": during,
                        "after": "",
                        "total": total,
                        "top": top,
                        "bottom": bottom,
                    }

                    width = len(str(bottom + 1))
                    template_context = "\n".join(
                        "{lineno:>{width}} {line}".format(
                            lineno=lineno, width=width, line=line
                        )
                        for lineno, line in source_lines
                    )

                    self.message += "\n\n" + template_context
            except ValueError:
                self.message += "\n\n[Error: Invalid line number extracted]"

    def __str__(self):
        return self.message
