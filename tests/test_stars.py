import pytest

from clubs.templatetags.stars import stars


@pytest.mark.parametrize(
    "rating,expected",
    [
        (None, ""),
        (0, "☆☆☆☆☆"),
        (1, "½☆☆☆☆"),
        (2, "★☆☆☆☆"),
        (5, "★★½☆☆"),
        (9, "★★★★½"),
        (10, "★★★★★"),
        (15, "★★★★★"),  # clamp
        (-3, "☆☆☆☆☆"),  # clamp
    ],
)
def test_stars_filter(rating, expected):
    assert stars(rating) == expected
