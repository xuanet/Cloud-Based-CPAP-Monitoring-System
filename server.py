from flask import Flask, jsonify, request
from datetime import datetime
from google.cloud.sql.connector import Connector
import base64
import json
import pytds


def convert_file_to_base64_str(filename):
    """Convert a file to a base64-encoded string.

    This function reads the contents of a file and converts
    it to a base64-encoded string. It is typically used for
    converting image files to a format that can be easily
    transmitted over the network.

    :param filename: str containing the path to the file to be
                     converted
    :return: str containing the base64-encoded string
             representation of the file
    """
    with open(filename, "rb") as image_file:
        b64_bytes = base64.b64encode(image_file.read())
    b64_string = str(b64_bytes, encoding='utf-8')
    return b64_string


def connect_to_db():
    """Connect to the SQL Server database.

    This function establishes a connection to the SQL
    Server database using the Google Cloud SQL Connector.
    It uses the specified project ID, region, instance
    name, and database credentials to create the connection.

    :return: pymssql.Connection object representing the database
             connection
    """
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
        # db='test_patients',
        db='patients',
        autocommit=True
    )
    print("connection successful")
    return conn


def validate_name(name):
    """Validate a patient name.

    This function validates a patient name by checking if it
    contains only allowed characters (letters, spaces, hyphens,
    and apostrophes). If the name is valid, it is returned as a
    stripped string. If the name is invalid or empty, an empty
    string is returned.

    :param name: str containing the patient name to validate

    :return: str containing the validated patient name, or an
             empty string if invalid
    """
    if name:
        name = name.strip()
        allowed_chars = ("abcdefghijklmnopqrstuvwxyz"
                         "ABCDEFGHIJKLMNOPQRSTUVWXYZ '-")
        for char in name:
            if char not in allowed_chars:
                return ""  # Invalid char returns empty string
        return name
    return ""


def validate_mrn(mrn):
    """Validate a Medical Record Number (MRN).

    This function validates an MRN by checking if it is a
    non-negative integer. If the MRN is valid, it is returned
    as an integer. If the MRN is invalid, None is returned.

    :param mrn: str or int containing the MRN to validate

    :return: int containing the validated MRN, or None if
             invalid
    """
    try:
        value = int(mrn)
        if value >= 0:
            return value
    except (ValueError, TypeError):
        pass
    return None


def validate_room_number(room_number):
    """Validate a room number.

    This function validates a room number by checking if it is a
    non-negative integer. If the room number is valid, it is
    returned as an integer. If the room number is invalid, None
    is returned.

    :param room_number: str or int containing the room number to
                        validate
    :return: int containing the validated room number, or None
             if invalid
    """

    try:
        value = int(room_number)
        if value >= 0:
            return value
    except (ValueError, TypeError):
        pass
    return None


def validate_cpap_pressure(cpap_pressure):
    """Validates the CPAP pressure to ensure it is within
    the operational range of 4 to 25 cmH2O. Returns a tuple
    containing a boolean indicating success, and a
    descriptive message.

    :param cpap_pressure: The CPAP pressure value to
                          validate.

    :return: Tuple (bool, str)
    """
    try:
        pressure = float(cpap_pressure)
        if 4 <= pressure <= 25:
            return pressure
    except (ValueError, TypeError):
        return None


def validate_breath_rate(breath_rate):
    """Validate a breath rate value.

    This function validates a breath rate value by checking
    if it is a non-negative float. If the breath rate is valid,
    it is returned as a float. If the breath rate is invalid,
    None is returned.

    :param breath_rate: str or float containing the breath rate
                        to validate

    :return: float containing the validated breath rate, or None
             if invalid
    """
    try:
        value = float(breath_rate)
        if value >= 0:
            return value
    except (ValueError, TypeError):
        pass
    return None


def validate_apnea_count(apnea_count):
    """Validate an apnea count value.

    This function validates an apnea count value by checking
    if it is a non-negative integer. If the apnea count is
    valid, it is returned as an integer. If the apnea count
    is invalid, None is returned.

    :param apnea_count: str or int containing the apnea count
                        to validate

    :return: int containing the validated apnea count, or None
             if invalid
    """
    try:
        value = int(apnea_count)
        if value >= 0:  # Assuming zero apneas is a valid scenario
            return value
    except (ValueError, TypeError):
        pass
    return None


def execute_function(func, *args, **kwargs):
    """Execute a function with the provided arguments and
    keyword arguments.

    This function is a utility function that allows executing
    a given function with the provided positional and keyword
    arguments. It is used to wrap the execution of functions
    in a consistent manner.

    :param func: function object to be executed

    :param *args: variable-length positional arguments to pass
                  to the function

    :param **kwargs: variable-length keyword arguments to pass
                     to the function

    :return: the result of executing the function with the
             provided arguments
    """
    return func(*args, **kwargs)


app = Flask(__name__)


@app.route('/fetch_room_numbers', methods=["GET"])
def execute_fetch_room_numbers():
    """Execute the fetch_room_numbers function.

    This is a Flask route handler that executes the
    fetch_room_numbers function when a GET request is
    made to the '/fetch_room_numbers' endpoint. It passes
    the database cursor as an argument to the function.

    :return: the result of executing the fetch_room_numbers
             function
    """
    return execute_function(fetch_room_numbers, cursor)


def fetch_room_numbers(cursor):
    """Fetch the occupied room numbers from the database.

    This function retrieves the occupied room numbers from
    the 'now' table in the database. It executes a SELECT
    query to fetch the room numbers and returns them
    as a JSON response.

    :param cursor: pymssql.Cursor object representing the
                   database cursor

    :return: Flask response object containing the occupied
             room numbers as JSON
    """
    query = "SELECT room_number FROM now"
    cursor.execute(query)
    rooms = cursor.fetchall()
    return jsonify([room[0] for room in rooms])


@app.route('/fetch_cpap_calculated_data', methods=["POST"])
def fetch_cpap_calculated_data_handler():
    """Handle the request to fetch CPAP calculated data.

    This is a Flask route handler that handles a POST
    request to the '/fetch_cpap_calculated_data' endpoint.
    It extracts the room number from the JSON payload and
    passes it to the fetch_cpap_calculated_data function.

    :return: the result of executing the
             fetch_cpap_calculated_data function
    """
    in_json = request.get_json()
    room_number = in_json["room_number"]
    return fetch_cpap_calculated_data(cursor, room_number)


def fetch_cpap_calculated_data(cursor, room_number):
    """Fetch the CPAP calculated data for a given room number.

    This function retrieves the CPAP calculated data from the
    'now' table in the database for a specific room number. It
    executes a SELECT query to fetch the data and returns it as
    a JSON response.

    :param cursor: pymssql.Cursor object representing the database
                   cursor
    :param room_number: int containing the room number to fetch data
                        for

    :return: Flask response object containing the CPAP calculated
             data as JSON
    """
    query = (f"SELECT mrn, name, datetime, currcpap, br, apnea, plot "
             f"FROM now WHERE room_number = '{room_number}'")
    cursor.execute(query)
    calculated_data = cursor.fetchall()
    """decimals are returned as strings"""
    return jsonify(calculated_data[0])


@app.route('/check_exists', methods=["POST"])
def check_exists_handler():
    """Handle the request to check if MRN or room number exists.

    This is a Flask route handler that handles a POST request to
    the '/check_exists' endpoint. It extracts the MRN and room
    number from the JSON payload and passes them to the check_exists
    function.

    :return: the result of executing the check_exists function
    """
    return execute_function(check_exists, cursor, request.files)


def check_exists(cursor, request):
    """Check if the MRN or room number already exists in the database.

    This function checks if the provided MRN or room number already
    exists in the 'now' table of the database. It executes SELECT
    COUNT queries to check the existence and returns the result as a
    JSON response.

    :param cursor: pymssql.Cursor object representing the database
                   cursor
    :param request: Flask request object containing the JSON payload

    :return: Flask response object containing the existence information
             as JSON
    """
    data = json.loads(request.get('data').read().decode('utf-8'))
    mrn = validate_mrn(data.get('mrn'))
    room_number = validate_room_number(data.get('room_number'))

    if mrn is None:
        return jsonify({"error": ("Invalid MRN: "
                                  "MRN must be an integer")}), 419
    if room_number is None:
        return jsonify({"error": ("Invalid room number: "
                                  "room number must be an integer")}), 420

    try:
        # Check if the MRN already exists in the now table
        query = "SELECT COUNT(*) FROM now WHERE mrn = %s"
        cursor.execute(query, (mrn,))
        mrn_count = cursor.fetchone()[0]

        # Check if the room number already exists in the now table
        query = "SELECT COUNT(*) FROM now WHERE room_number = %s"
        cursor.execute(query, (room_number,))
        room_count = cursor.fetchone()[0]

        exists_info = {}
        if mrn_count > 0:
            exists_info["exists"] = "mrn"
        if room_count > 0:
            exists_info["exists"] = "room"

        return jsonify(exists_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/fetch_cpap_pressure', methods=["POST"])
def fetch_cpap_pressure_handler():
    """Handle the request to fetch CPAP pressure.

    This is a Flask route handler that handles a POST
    request to the '/fetch_cpap_pressure' endpoint. It
    extracts the MRN, room number, and current CPAP pressure
    from the JSON payload and passes them to the
    fetch_cpap_pressure function.

    :return: the result of executing the fetch_cpap_pressure
             function
    """
    return execute_function(fetch_cpap_pressure, cursor, request.files)


def fetch_cpap_pressure(cursor, request):
    """Fetch the CPAP pressure for a given MRN or room number.

    This function retrieves the CPAP pressure from the 'now' table
    in the database for a specific MRN or room number. If the MRN
    or room number exists, it returns the CPAP pressure as a JSON
    response. If the MRN or room number does not exist, it returns the
    current CPAP pressure if provided and valid, or a default value
    of "0.0".

    :param cursor: pymssql.Cursor object representing the database cursor
    :param request: Flask request object containing the JSON payload

    :return: Flask response object containing the CPAP pressure as JSON
    """
    data = json.loads(request.get('data').read().decode('utf-8'))
    mrn = validate_mrn(data.get('mrn'))
    room_number = validate_room_number(data.get('room_number'))
    currcpap = validate_cpap_pressure(data.get('currcpap'))

    try:
        query = ("SELECT currcpap FROM now WHERE "
                 "mrn = {} OR room_number = {}".format(mrn, room_number))
        cursor.execute(query)
        result = cursor.fetchone()

        if result:
            cpap_pressure = result[0]
            # Validate the CPAP pressure format
            if validate_cpap_pressure(cpap_pressure) is None:
                return jsonify({"error": ("Invalid CPAP pressure: "
                                          "CPAP pressure out of range "
                                          "(4-25 cmH\u2082O) and/or must "
                                          "be a float")}), 416
            else:
                return jsonify({'cpap_pressure': cpap_pressure})
        else:
            if currcpap is not None:
                if validate_cpap_pressure(currcpap) is None:
                    return jsonify({"error": ("Invalid CPAP pressure: "
                                              "CPAP pressure out of range "
                                              "(4-25 cmH\u2082O) and/or must "
                                              "be a float")}), 416
                else:
                    return jsonify({'cpap_pressure': currcpap})
            else:
                return jsonify({'cpap_pressure': "0.0"})
    except Exception as e:
        print(f"Error occurred while fetching CPAP pressure: {str(e)}")
        return jsonify({"error": "An error occurred"}), 500
        return jsonify({"error": "An error occurred"}), 500


@app.route('/upload_data', methods=["POST"])
def execute_upload_data():
    """Handle the request to upload data.

    This is a Flask route handler that handles a POST request
    to the '/upload_data' endpoint. It extracts the data and
    plot image from the request files and passes them to the
    upload_data function.

    :return: the result of executing the upload_data function
    """
    return execute_function(upload_data, cursor, request.files)


def upload_data(cursor, request):
    """Upload patient data to the database.

    This function uploads patient data to the 'entries' and 'now'
    tables in the database. It validates the input data, inserts
    the data into the 'entries' table, and either updates an
    existing row or inserts a new row in the 'now' table based
    on the MRN or room number.

    :param cursor: pymssql.Cursor object representing the database
                   cursor
    :param request: Flask request object containing the data and
                    plot image files

    :return: Flask response object containing the upload status as
             JSON
    """

    data = json.loads(request.get('data').read().decode('utf-8'))
    plot_file = request.get('plot')

    # Validate inputs
    mrn = validate_mrn(data.get('mrn'))
    name = validate_name(data.get('name'))
    currcpap = validate_cpap_pressure(data.get('currcpap'))
    br = validate_breath_rate(data.get('br'))
    apnea = validate_apnea_count(data.get('apnea'))
    room_number = validate_room_number(data.get('room_number'))

    # Validate inputs separately to send specific error messages
    if name == "":
        return jsonify({"error": ("Invalid name: name cannot be "
                                  "empty or contain invalid "
                                  "characters")}), 415
    if currcpap is None:
        return jsonify({"error": ("Invalid CPAP pressure: "
                                  "CPAP pressure out of range "
                                  "(4-25 cmH\u2082O) and/or must "
                                  "be a float")}), 416
    if br is None:
        return jsonify({"error": "Invalid breathing rate"}), 417
    if apnea is None:
        return jsonify({"error": "Invalid apnea count"}), 418
    if mrn is None:
        return jsonify({"error": ("Invalid MRN: "
                                  "MRN must be an integer")}), 419
    if room_number is None:
        return jsonify({"error": ("Invalid room number: "
                                  "room number must be an integer")}), 420

    plot_bytes = plot_file.read()
    plot_base64 = base64.b64encode(plot_bytes).decode('utf-8')

    try:
        # Insert into entries table
        query = """
            INSERT INTO entries (mrn, datetime,
            name, currcpap, br, apnea, plot, room_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            mrn,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            name,
            currcpap,
            br,
            apnea,
            plot_base64,
            room_number
        )
        cursor.execute(query, values)

        # Update the existing row in the now table or insert a new row
        query = """
            MERGE INTO now AS target
            USING (SELECT %s AS mrn, %s AS name, %s AS datetime,
                   %s AS currcpap, %s AS br, %s AS apnea, %s AS plot,
                   %s AS room_number) AS source
            ON (target.mrn = source.mrn OR
            target.room_number = source.room_number)
            WHEN MATCHED THEN
                UPDATE SET target.mrn = source.mrn,
                target.name = source.name,
                target.datetime = source.datetime,
                target.currcpap = source.currcpap,
                target.br = source.br,
                target.apnea = source.apnea,
                target.plot = source.plot,
                target.room_number = source.room_number
            WHEN NOT MATCHED THEN
                INSERT (room_number, mrn, name,
                datetime, currcpap, br, apnea, plot)
                VALUES (source.room_number, source.mrn,
                source.name, source.datetime,
                source.currcpap, source.br, source.apnea,
                source.plot);
        """
        values = (
            mrn,
            name,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            currcpap,
            br,
            apnea,
            plot_base64,
            room_number
        )
        cursor.execute(query, values)

        return jsonify({"message": "Data uploaded successfully"})
    except pytds.tds_base.OperationalError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/update_patient_info', methods=["POST"])
def execute_update_patient_info():
    """Handle the request to update patient information.

    This is a Flask route handler that handles a POST request
    to the '/update_patient_info' endpoint. It extracts the
    data and plot image from the request files and passes them
    to the update_patient_info function.

    :return: the result of executing the update_patient_info
             function
    """
    return execute_function(update_patient_info, cursor, request.files)


def update_patient_info(cursor, request):
    """Update patient information in the database.

    This function updates patient information in the 'now' table
    of the database based on the provided MRN. It also inserts the
    updated data into the 'entries' table. It validates the input
    data before performing the update and insertion operations.

    :param cursor: pymssql.Cursor object representing the database
                   cursor
    :param request: Flask request object containing the data and plot
                    image files

    :return: Flask response object containing the update status as JSON
    """
    data = json.loads(request.get('data').read().decode('utf-8'))
    plot_file = request.get('plot')

    # Validate inputs
    mrn = validate_mrn(data.get('mrn'))
    name = validate_name(data.get('name'))
    currcpap = validate_cpap_pressure(data.get('currcpap'))
    br = validate_breath_rate(data.get('br'))
    apnea = validate_apnea_count(data.get('apnea'))

    # Validate inputs separately to send specific error messages
    if name is None or name == "":
        return jsonify({"error": ("Invalid name: name cannot be "
                                  "empty or contain invalid "
                                  "characters")}), 415
    if currcpap is None:
        return jsonify({"error": ("Invalid CPAP pressure: "
                                  "CPAP pressure out of range "
                                  "(4-25 cmH\u2082O) and/or must "
                                  "be a float")}), 416
    if br is None:
        return jsonify({"error": "Invalid breathing rate"}), 417
    if apnea is None:
        return jsonify({"error": "Invalid apnea count"}), 418

    plot_bytes = plot_file.read() if plot_file else None
    plot_base64 = (base64.b64encode(plot_bytes).decode('utf-8')
                   if plot_bytes else None)

    # Update the now table
    query = """
        UPDATE now
        SET name = %s, currcpap = %s, br = %s,
        apnea = %s, plot = %s, datetime = %s
        WHERE mrn = %s
    """
    values = (
        name,
        currcpap,
        br,
        apnea,
        plot_base64,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        mrn
    )
    cursor.execute(query, values)

    # Insert into entries table
    query = """
        INSERT INTO entries (mrn, datetime, name,
        currcpap, br, apnea, plot, room_number)
        VALUES (%s, %s, %s, %s, %s, %s, %s,
        (SELECT TOP 1 room_number FROM now WHERE mrn = %s))
    """
    values = (
        mrn,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        name,
        currcpap,
        br,
        apnea,
        plot_base64,
        mrn
    )
    cursor.execute(query, values)

    return jsonify({"message": "Patient information updated successfully"})


@app.route('/fetch_mrn_from_room_number', methods=["POST"])
def fetch_mrn_from_room_number_handler():
    """Handle the request to fetch MRN from room number.

    This is a Flask route handler that handles a POST request
    to the '/fetch_mrn_from_room_number' endpoint. It extracts
    the room number from the JSON payload and passes it to the
    fetch_mrn_from_room_number function.

    :return: the result of executing the fetch_mrn_from_room_number
             function
    """
    # in_json contains room_number
    in_json = request.get_json()
    room_number = in_json["room_number"]
    return fetch_mrn_from_room_number(cursor, room_number)


def fetch_mrn_from_room_number(cursor, room_number):
    """Fetch the MRN for a given room number.

    This function retrieves the MRN from the 'now' table in the
    database for a specific room number. It executes a SELECT
    query to fetch the MRN and returns it as a JSON response.

    :param cursor: pymssql.Cursor object representing the database
                   cursor
    :param room_number: int containing the room number to fetch
                         the MRN for

    :return: Flask response object containing the MRN as JSON
    """
    query = f"SELECT mrn FROM now WHERE room_number = {room_number}"
    cursor.execute(query)
    rn = cursor.fetchall()
    return jsonify(rn[0][0])


@app.route('/fetch_datetimes_for_patient', methods=["POST"])
def fetch_datetimes_for_patient_handler():
    """Handle the request to fetch datetimes for a patient.

    This is a Flask route handler that handles a POST request
    to the '/fetch_datetimes_for_patient' endpoint. It extracts
    the MRN from the JSON payload and passes it to the
    fetch_datetimes_for_patient function.

    :return: the result of executing the fetch_datetimes_for_patient
             function
    """
    # in_json contains the relevant selected patient mrn
    in_json = request.get_json()
    mrn = in_json["mrn"]
    return fetch_datetimes_for_patient(cursor, mrn)


def fetch_datetimes_for_patient(cursor, mrn):
    """Fetch the datetimes for a given patient MRN.

    This function retrieves the datetimes from the 'entries'
    table in the database for a specific patient MRN. It
    executes a SELECT query to fetch the datetimes and returns
    them as a JSON response.

    :param cursor: pymssql.Cursor object representing the database
                   cursor
    :param mrn: int containing the patient MRN to fetch the datetimes
                for

    :return: Flask response object containing the datetimes as JSON
    """
    query = f"SELECT datetime FROM entries WHERE mrn = {mrn}"
    cursor.execute(query)
    datetimes = cursor.fetchall()
    return jsonify([dt[0] for dt in datetimes])


@app.route('/fetch_plot_from_datetime_and_mrn', methods=["POST"])
def fetch_plot_from_datetime_and_mrn_handler():
    """Handle the request to fetch plot from datetime and MRN.

    This is a Flask route handler that handles a POST request to
    the '/fetch_plot_from_datetime_and_mrn' endpoint. It extracts
    the datetime and MRN from the JSON payload and passes them to
    the fetch_plot_from_datetime_and_mrn function.

    :return: the result of executing the
             fetch_plot_from_datetime_and_mrn function
    """
    in_json = request.get_json()
    # dt is string format
    dt = in_json["datetime"]
    mrn = in_json["mrn"]
    return fetch_plot_from_datetime_and_mrn(cursor, dt, mrn)


def fetch_plot_from_datetime_and_mrn(cursor, dt, mrn):
    """Fetch the plot for a given datetime and patient MRN.

    This function retrieves the plot from the 'entries' table
    in the database for a specific datetime and patient MRN.
    It executes a SELECT query to fetch the plot and returns
    it as a JSON response.

    :param cursor: pymssql.Cursor object representing the database
                   cursor
    :param dt: str containing the datetime to fetch the plot for
    :param mrn: int containing the patient MRN to fetch the plot for

    :return: Flask response object containing the plot as JSON
    """
    # dt in form '2022-04-18 13:45:00'
    query = f"SELECT plot FROM entries WHERE mrn = {mrn} AND datetime = '{dt}'"
    cursor.execute(query)
    datetimes = cursor.fetchall()
    return jsonify(datetimes[0][0])


@app.route('/send_cpap', methods=["POST"])
def send_cpap_handler():
    """Handle the request to send CPAP pressure.

    This is a Flask route handler that handles a POST request
    to the '/send_cpap' endpoint. It extracts the room number
    and CPAP pressure from the JSON payload, validates them
      and passes them to the send_cpap function if valid.

    :return: the result of executing the send_cpap function
             if the input is valid, or an error message if
             the input is invalid
    """
    in_json = request.get_json()
    if validate_send_cpap(in_json):
        room_number = in_json["room_number"]
        cpap = in_json["cpap"]
        return send_cpap(cursor, room_number, cpap)
    else:
        print("failed")
        return "invalid input", 400


def validate_send_cpap(in_json):
    """Validate the input JSON for sending CPAP pressure.

    This function validates the input JSON payload for sending
    CPAP pressure. It checks if the JSON is a dictionary with
    the required keys "room_number" and "cpap", and if the values
    are of the correct types (integer for room number and float
    for CPAP pressure).

    :param in_json: dict containing the input JSON payload

    :return: bool indicating whether the input is valid or not
    """
    if ((type(in_json) is not dict) or
            (list(in_json.keys()) != ["room_number", "cpap"])):
        print("doesn't have required keys")
        return False
    if len(in_json) != 2:
        print('number of keys wrong')
        return False
    if ((type(in_json["room_number"]) is not int or
         type(in_json["cpap"]) is not float)):
        print("value types wrong")
        return False
    return True


def send_cpap(cursor, room_number, cpap):
    """Send CPAP pressure to the database.

    This function updates the CPAP pressure in the 'now' table
    of the database for a specific room number. It executes an
    UPDATE query to set the CPAP pressure for the given room
    number.

    :param cursor: pymssql.Cursor object representing the
                   database cursor
    :param room_number: int containing the room number to update
                        the CPAP pressure for
    :param cpap: float containing the CPAP pressure value to set

    :return: tuple containing the update status message and HTTP
             status code
    """
    query = (f"UPDATE now SET currcpap = {cpap} "
             f"WHERE room_number = {room_number}")
    cursor.execute(query)
    return "update successful", 200


if __name__ == "__main__":
    conn = connect_to_db()
    cursor = conn.cursor()
    app.run(port=5001)
    cursor.close()
    conn.close()
    print('server is off')
