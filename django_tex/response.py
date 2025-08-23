from django.http import HttpResponse


class PDFResponse(HttpResponse):
    def __init__(self, content, as_attachment=False, filename=None):
        super(PDFResponse, self).__init__(content_type="application/pdf")
        if filename:
            disposition = "attachment" if as_attachment else "inline"
            file_expr = 'filename="{}"'.format(filename)
            self["Content-Disposition"] = "{}; {}".format(disposition, file_expr)
        elif as_attachment:
            self["Content-Disposition"] = "attachment"
        self.write(content)
