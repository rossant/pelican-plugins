import json
import re
from functools import partial

from pelican import signals
from pelican.readers import MarkdownReader, HTMLReader, BaseReader

try:
    import markdown
    from markdown import Markdown

    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import HtmlFormatter
except:
    Markdown = False

def hl(code):
    return highlight(code, PythonLexer(), HtmlFormatter())

def get_metadata(filepath):

    with open(filepath, "r") as f:
        nb = json.load(f)

    cells = nb['worksheets'][0]['cells']

    cell = cells[0]
    assert cell.get('cell_type', None) == 'markdown'
    metadata = ''.join(cell.get('source', [])) + '\n\n'
    return metadata

def _indent_line(level=1, line=''):
    return ' ' * (4*level) + line

def process_cell_markdown(cell):
    return ''.join(cell.get('source', [])) + '\n\n'

def process_cell_heading(cell):
    return cell.get('level', 0) * '#' + ' ' + ''.join(cell.get('source', [])) + '\n\n'

def process_cell_input(cell):
    input_lines = cell.get('input', [])
    input_lines = map(partial(_indent_line, 0), input_lines)
    code = ''.join(input_lines)
    input_html = hl(code)
    input_html = '\n\n<div class="ipynb-input">%s</div>\n\n' % input_html
    return input_html

def process_cell_output_png(output):
    png = output.get('png', [])
    if png:
        return '\n\n<img src="data:image/png;base64,%s" />\n\n' % png.strip()

def process_cell_output_html(output):
    html = output.get('html', [])
    html = ''.join(html).strip()
    html = '\n\n<div class="ipynb-html">%s</div>\n\n' % html
    return html

def process_cell_output_text(output):
    text = output.get('text', [])
    text = ''.join(text).strip()
    if not text:
        return ''
    html = '\n\n<pre class="ipynb-output">%s</pre>\n\n' % text
    return html

def process_cell_output(output):
    return (process_cell_output_html(output) or
            process_cell_output_png(output) or
            process_cell_output_text(output))

def process_cell_outputs(cell):
    outputs = cell.get('outputs', [])
    return '\n\n'.join(map(process_cell_output, outputs))

def process_cell(cell, options=None):
    if options is None:
        options = {}
    cell_type = cell.get('cell_type', None)
    keep_input = options.get('keep_input', True)

    if cell_type == 'markdown':
        return process_cell_markdown(cell)
    elif cell_type == 'heading':
        return process_cell_heading(cell)
    elif cell_type == 'code':
        if keep_input:
            return process_cell_input(cell) + process_cell_outputs(cell)
        else:
            return process_cell_outputs(cell)

def nb_to_markdown(filepath, options=None):
    with open(filepath, "r") as f:
        nb = json.load(f)

    cells = nb['worksheets'][0]['cells']
    md = '\n'.join([process_cell(_, options) for _ in cells])

    return md

def get_keep_input(filename):
    metadata = get_metadata(filename)
    r = re.search(r'keep_input[ ]*\:[ ]*([true|false]+)', metadata, flags=re.IGNORECASE)
    if r:
        return r.group(1).lower() == 'true'
    else:
        return True


class IPyNbReader(BaseReader):
    enabled = bool(Markdown)

    file_extensions = ['ipynb']

    def read(self, filename):
        keep_input = get_keep_input(filename)

        # ipynb ==> md
        mdcontents = '\n' + nb_to_markdown(filename, options={'keep_input': keep_input})
        mdcontents = re.sub(r'(?<=\n)# ([^\n]+)\n', r'title: \1\n', mdcontents).strip()

        # md ==> html
        md_reader = MarkdownReader(self.settings)
        md = Markdown(extensions=md_reader.extensions)
        html = md.convert(mdcontents)
        metadata = md_reader._parse_metadata(md.Meta)

        return html, metadata

def add_reader(readers):
    readers.reader_classes['ipynb'] = IPyNbReader

def register():
    signals.readers_init.connect(add_reader)
