from books import wikipedia

SAMPLE = (
    '<table class="wikitable">'
    "<tr><th>Année</th><th>Auteur</th><th>Ouvrage</th></tr>"
    '<tr><td rowspan="2">2020</td><td>Alice Martin</td>'
    '<td>Un titre<span style="display:none">x</span></td></tr>'
    "<tr><td>Bob Durand</td><td>Autre titre[1]</td></tr>"
    "<tr><td>2019</td><td>Clara Leroy</td><td>Troisième</td></tr>"
    "</table>"
)


def test_parse_handles_rowspan_hidden_and_footnote():
    grid = wikipedia._parse_table(SAMPLE)
    cols = wikipedia._detect_columns(grid[0])
    assert cols == {"year": 0, "author": 1, "title": 2}
    rows = wikipedia._extract(grid)
    assert rows == [
        (2020, "Alice Martin", "Un titre"),
        (2020, "Bob Durand", "Autre titre"),
        (2019, "Clara Leroy", "Troisième"),
    ]


def test_extract_returns_empty_when_headers_missing():
    grid = wikipedia._parse_table(
        '<table class="wikitable"><tr><th>Foo</th><th>Bar</th></tr>'
        "<tr><td>1</td><td>2</td></tr></table>"
    )
    assert wikipedia._extract(grid) == []
