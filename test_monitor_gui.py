import pytest


@pytest.mark.parametrize("input, expected", [
    ('Mon, 18 Apr 2024 12:00:35 GMT', '2024-04-18 12:00:35'),
    ('Tue, 31 Jan 2013 11:45:09 GMT', '2013-01-31 11:45:09'),
    ('Sun, 21 Mar 1990 19:12:36 GMT', '1990-03-21 19:12:36')
])
def test_convert_day_string(input, expected):
    from monitor_gui import convert_date_string
    output = convert_date_string(input)
    assert output == expected


def test_b64_string_to_file():
    from monitor_gui import save_plot
    from test_monitor_gui_utils import file_to_b64_string
    import filecmp
    import os
    b64str = file_to_b64_string("nis.png")
    save_plot(b64str, noname=True)
    answer = filecmp.cmp("nis.png",
                         "nis_output.png")
    os.remove("nis_output.png")
    assert answer
