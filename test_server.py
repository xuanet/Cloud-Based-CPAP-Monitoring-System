import pytest
from google.cloud.sql.connector import Connector
from flask import Flask, jsonify, request
import matplotlib.pyplot as plt
import json
import io
from datetime import datetime
from unittest.mock import Mock


def connect_to_db():
    project_id = 'the-dock-420320'
    region = 'us-east1'
    instance_name = 'cpap'
    INSTANCE_CONNECTION_NAME = f"{project_id}:{region}:{instance_name}"
    connector = Connector()
    conn = connector.connect(
        INSTANCE_CONNECTION_NAME,
        "pytds",
        user='kevin',
        password='password',
        db='test_patients',
        autocommit=True
    )
    return conn


app = Flask(__name__)


def test_fetch_room_numbers():
    from server import fetch_room_numbers

    conn = connect_to_db()
    cursor = conn.cursor()

    with app.app_context():
        output = fetch_room_numbers(cursor).get_json()
    expected = [1, 2]

    cursor.close()
    conn.close()

    assert output == expected


def test_fetch_cpap_calculated_data():
    from server import fetch_cpap_calculated_data

    conn = connect_to_db()
    cursor = conn.cursor()

    with app.app_context():
        output = fetch_cpap_calculated_data(cursor, 2).get_json()
    expected_mrn = 9
    expected_name = 'Melanie'
    expected_dt = 'Tue, 23 Apr 2024 05:30:35 GMT'
    expected_currcpap = 16.5
    expected_br = 18.0
    expected_apnea = 1
    expected_plot = 'plot_data'

    cursor.close()
    conn.close()

    assert output[0] == expected_mrn
    assert output[1] == expected_name
    assert output[2] == expected_dt
    assert float(output[3]) == expected_currcpap
    assert float(output[4]) == expected_br
    assert output[5] == expected_apnea
    assert output[6][:30] == expected_plot


def test_fetch_mrn_from_room_number():
    from server import fetch_mrn_from_room_number

    conn = connect_to_db()
    cursor = conn.cursor()

    with app.app_context():
        output = fetch_mrn_from_room_number(cursor, 1).get_json()

    expected = 7

    cursor.close()
    conn.close()

    assert output == expected


def test_fetch_datetimes_for_patient():
    from server import fetch_datetimes_for_patient

    conn = connect_to_db()
    cursor = conn.cursor()

    with app.app_context():
        output = fetch_datetimes_for_patient(cursor, 1).get_json()

    expected = (['Fri, 18 Jun 2004 14:00:00 GMT',
                 'Mon, 18 Apr 2022 13:45:00 GMT'])

    cursor.close()
    conn.close()

    assert output == expected


def test_fetch_mrn_from_room_number():
    from server import fetch_mrn_from_room_number

    conn = connect_to_db()
    cursor = conn.cursor()

    with app.app_context():
        output = fetch_mrn_from_room_number(cursor, 1).get_json()

    expected = 7

    cursor.close()
    conn.close()

    assert output == expected


def test_fetch_datetimes_for_patient():
    from server import fetch_datetimes_for_patient

    conn = connect_to_db()
    cursor = conn.cursor()

    with app.app_context():
        output = fetch_datetimes_for_patient(cursor, 1).get_json()

    expected = (['Fri, 18 Jun 2004 14:00:00 GMT',
                 'Mon, 18 Apr 2022 13:45:00 GMT'])

    cursor.close()
    conn.close()

    assert output == expected


def test_fetch_plot_from_datetime_and_mrn():
    from server import fetch_plot_from_datetime_and_mrn

    conn = connect_to_db()
    cursor = conn.cursor()

    with app.app_context():
        output = fetch_plot_from_datetime_and_mrn(
            cursor,
            '2022-04-18 13:45:00',
            1
        ).get_json()

    expected = 'iVBORw0KGgoAAAANSUhEUgAAAoAAAA'

    cursor.close()
    conn.close()

    assert output[:30] == expected


@pytest.mark.parametrize("input, expected", [
                         ({"room_number": 3, "cpap": 12.0}, True),
                         ({"room_number": 3.2, "cpap": 12}, False),
                         ({"room_number": 3, "cpap": 12}, False),
                         ({"room_umber": 5, "cpap": 12}, False),
                         ({"room_number": 3, "cpap": 12, "asdf": 1234}, False),
                         ])
def test_validate_send_cpap(input, expected):
    from server import validate_send_cpap
    output = validate_send_cpap(input)
    assert output is expected


def test_send_cpap():
    from server import send_cpap

    conn = connect_to_db()
    cursor = conn.cursor()

    with app.app_context():
        send_cpap(cursor, 1, 10.00)
        query = "SELECT COUNT(*) FROM now WHERE currcpap = 10.00"
        cursor.execute(query)
        assert cursor.fetchall()[0][0] == 1
        query = f"UPDATE now SET currcpap = 15.50 WHERE room_number = 1"
        cursor.execute(query)

    cursor.close()
    conn.close()


@pytest.fixture
def client():
    from server import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_check_exists(client):
    from server import check_exists

    # Connect to the test database
    conn = connect_to_db()
    cursor = conn.cursor()

    try:
        # Set up test data
        test_data = [
            (754, 'John Doe',
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             10.0, 15.0, 0, 'plot_data', '999'),
            (845, 'Jane Smith',
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             12.0, 18.0, 1, 'plot_data', '234'),
        ]

        # Merge test data into the 'now' table
        merge_query = """
        MERGE INTO now AS target
        USING (
            SELECT %s AS mrn, %s AS name, %s AS datetime, %s AS currcpap,
                   %s AS br, %s AS apnea, %s AS plot, %s AS room_number
        ) AS source
        ON (target.mrn = source.mrn OR target.room_number = source.room_number)
        WHEN MATCHED THEN
            UPDATE SET target.name = source.name,
                       target.datetime = source.datetime,
                       target.currcpap = source.currcpap,
                       target.br = source.br,
                       target.apnea = source.apnea,
                       target.plot = source.plot,
                       target.room_number = source.room_number
        WHEN NOT MATCHED THEN
            INSERT (mrn, name, datetime, currcpap, br, apnea,
            plot, room_number)
            VALUES (source.mrn, source.name, source.datetime, source.currcpap,
                    source.br, source.apnea, source.plot, source.room_number);
        """
        cursor.executemany(merge_query, test_data)

        # Test case: MRN exists
        data = {
            'mrn': '754',
            'room_number': '845'
        }
        json_data = json.dumps(data)
        data_file = io.BytesIO(json_data.encode('utf-8'))

        files = {
            'data': (data_file, 'application/json'),
        }

        with app.test_request_context(data=files):
            response = check_exists(cursor, request.files)
        assert response.status_code == 200
        assert response.json == {'exists': 'mrn'}

        # Test case: Room number exists
        data = {
            'mrn': '999',
            'room_number': '234'
        }
        json_data = json.dumps(data)
        data_file = io.BytesIO(json_data.encode('utf-8'))

        files = {
            'data': (data_file, 'application/json'),
        }

        with app.test_request_context(data=files):
            response = check_exists(cursor, request.files)
        assert response.status_code == 200
        assert response.json == {'exists': 'room'}

        # Test case: Neither MRN nor room number exists
        data = {
            'mrn': '1111',
            'room_number': '1111'
        }
        json_data = json.dumps(data)
        data_file = io.BytesIO(json_data.encode('utf-8'))

        files = {
            'data': (data_file, 'application/json'),
        }

        with app.test_request_context(data=files):
            response = check_exists(cursor, request.files)
        assert response.status_code == 200
        assert response.json == {}
    finally:
        # Clean up test data
        delete_query = "DELETE FROM now WHERE mrn IN (754, 845)"
        cursor.execute(delete_query)
        cursor.close()
        conn.close()


def test_fetch_cpap_pressure(client):
    from server import fetch_cpap_pressure

    mock_cursor = Mock()

    expected_query = ("SELECT currcpap FROM now WHERE "
                      "mrn = 123 OR room_number = 456")
    expected_result = None  # No record found in the database

    mock_cursor.execute.return_value = None
    mock_cursor.fetchone.return_value = expected_result

    mock_request = Mock()
    test_data = {
        'mrn': '123',
        'room_number': '456',
        'currcpap': 10.5
    }
    mock_request.get.return_value.read.return_value.decode.return_value = (
        json.dumps(test_data))

    with app.app_context():
        response = fetch_cpap_pressure(mock_cursor, mock_request)

    mock_cursor.execute.assert_called_once_with(expected_query)

    assert response.status_code == 200
    assert response.get_json() == {'cpap_pressure': 10.5}


def test_upload_data(client):
    from server import upload_data

    conn = connect_to_db()
    cursor = conn.cursor()

    # Create a sample plot image
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 2, 3])
    plot_data = io.BytesIO()
    fig.savefig(plot_data, format='png')
    plot_data.seek(0)

    # Prepare the request data
    data = {
        'mrn': '12345',
        'name': 'John Doe',
        'currcpap': '10',
        'br': '20.5',
        'apnea': '3',
        'room_number': '102'
    }
    json_data = json.dumps(data)
    data_file = io.BytesIO(json_data.encode('utf-8'))

    files = {
        'data': (data_file, 'application/json'),
        'plot': (plot_data, 'image/png')
    }

    # Send the POST request with the cursor object
    with app.app_context():
        with app.test_request_context(data=files,
                                      content_type='multipart/form-data'):
            response = upload_data(cursor, request.files)

    # Assert the response
    assert response.status_code == 200
    assert response.json == {'message': 'Data uploaded successfully'}

    query = "DELETE FROM now WHERE room_number = 102"
    cursor.execute(query)

    cursor.close()
    conn.close()


def test_update_patient_info(monkeypatch):
    from server import update_patient_info

    conn = connect_to_db()
    cursor = conn.cursor()

    # Create a sample plot image
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 2, 3])
    plot_data = io.BytesIO()
    fig.savefig(plot_data, format='png')
    plot_data.seek(0)

    # Prepare the request data
    data = {
        'mrn': '12345',
        'name': 'John Doe',
        'currcpap': '10.5',
        'br': '20.5',
        'apnea': '3'
    }
    json_data = json.dumps(data)
    data_file = io.BytesIO(json_data.encode('utf-8'))

    # Mock the request.files attribute
    mock_request_files = {
        'data': (data_file, 'application/json'),
        'plot': (plot_data, 'image/png')
    }

    # Create a fake request context and patch the request.files attribute
    with app.test_request_context(data=mock_request_files,
                                  content_type='multipart/form-data'):
        # Call the update_patient_info function
        response = update_patient_info(cursor, request.files)

    # Assert the response
    assert response.status_code == 200
    assert response.json == {'message': ('Patient information '
                                         'updated successfully')}

    cursor.close()
    conn.close()


# Validation Tests:
@pytest.mark.parametrize("name, expected", [
    ("John Doe", "John Doe"),
    ("John123", ""),
    ("", ""),
    ("John-Doe", "John-Doe"),
    ("  John Doe  ", "John Doe"),
    ("Anne-Marie", "Anne-Marie"),
    ("O'Connor", "O'Connor")
])
def test_validate_name(name, expected):
    from server import validate_name
    assert validate_name(name) == expected


@pytest.mark.parametrize("mrn, expected", [
    ("12345", 12345),
    ("abcde", None),
    ("", None),
    ("12345.67", None),
    ("001234", 1234)  # Leading zeros
])
def test_validate_mrn(mrn, expected):
    from server import validate_mrn
    assert validate_mrn(mrn) == expected


@pytest.mark.parametrize("cpap_pressure, expected", [
    ("10.5", 10.5),
    ("30", None),
    ("2", None),
    ("not a number", None),
    ("25", 25),
    ("4", 4)
])
def test_validate_cpap_pressure(cpap_pressure, expected):
    from server import validate_cpap_pressure
    assert validate_cpap_pressure(cpap_pressure) == expected


@pytest.mark.parametrize("breath_rate, expected", [
    ("20.5", 20.5),
    ("invalid", None),
    ("0", 0.0),
    ("-10", None)
])
def test_validate_breath_rate(breath_rate, expected):
    from server import validate_breath_rate
    assert validate_breath_rate(breath_rate) == expected


@pytest.mark.parametrize("apnea_count, expected", [
    ("3", 3),
    ("-1", None),
    ("10.5", None),
    ("100", 100)
])
def test_validate_apnea_count(apnea_count, expected):
    from server import validate_apnea_count
    assert validate_apnea_count(apnea_count) == expected
