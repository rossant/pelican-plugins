import json
import re

from pelican import signals
from pelican.readers import MarkdownReader, HTMLReader, BaseReader

try:
    import markdown
    from markdown import Markdown
except:
    Markdown = False

def get_metadata(filepath):

    with open(filepath, "r") as f:
        nb = json.load(f)

    cells = nb['worksheets'][0]['cells']

    cell = cells[0]
    assert cell.get('cell_type', None) == 'markdown'
    metadata = ''.join(cell.get('source', [])) + '\n\n'
    return metadata

def process_cell(cell, options=None):
    if options is None:
        options = {}
    cell_type = cell.get('cell_type', None)
    keep_input = options.get('keep_input', False)
    res = ''
    if cell_type == 'markdown':
        res += ''.join(cell.get('source', [])) + '\n\n'
    elif cell_type == 'heading':
        res += cell.get('level', 0) * '#' + ' ' + ''.join(cell.get('source', [])) + '\n\n'
    elif cell_type == 'code':
        if options.get('keep_input', True):
            c = cell.get('input', [])
            c = ''.join(('    ' + l) for l in c)
            res += c
            res += '\n\n'
        outputs = cell.get('outputs', [])
        for output in outputs:
            html = output.get('html', None)
            png = output.get('png', None)
            text = output.get('text', None)
            if html:
                res += '\n\n' + (''.join(html)).strip() + '\n\n'
            elif png:
                res += '<img src="data:image/png;base64,%s" />\n\n' % png.strip()
            elif text:
                res += ''.join(text) + '\n\n'
    return res

def nb_to_markdown(filepath, options=None):

    with open(filepath, "r") as f:
        nb = json.load(f)

    cells = nb['worksheets'][0]['cells']
    md = '\n'.join([process_cell(_, options) for _ in cells])

    return md


class IPyNbReader(BaseReader):
    enabled = bool(Markdown)

    file_extensions = ['ipynb']

    def read(self, filename):

        metadata = get_metadata(filename)
        r = re.search(r'keep_input[ ]*\:[ ]*([true|false]+)', metadata, flags=re.IGNORECASE)
        if r:
            keep_input = bool(r.group(1).title())

        # ipynb ==> md
        mdcontents = nb_to_markdown(filename, options={'keep_input': keep_input})

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
