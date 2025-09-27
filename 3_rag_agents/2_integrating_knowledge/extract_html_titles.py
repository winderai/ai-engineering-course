import sys
from html.parser import HTMLParser

class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.titles = []

    def handle_starttag(self, tag, attrs):
        if tag == 'span' and ('class', 'titleline') in attrs:
            self.in_title = True

    def handle_data(self, data):
        if self.in_title:
            self.titles.append(data.strip())

    def handle_endtag(self, tag):
        if tag == 'span':
            self.in_title = False

parser = LinkExtractor()
parser.feed(sys.stdin.read())
for i, title in enumerate(parser.titles[:5], 1):
    print(f'{i}. {title}')