import csv
import numpy as np
import scipy
import matplotlib.pyplot as plt
import scipy
import json
import logging
from scipy import signal


# Constants:
moist_air_density = 1.199  # kg/m^3

# Diameter of larger venturi tube:
d1 = 15/1000  # m

# Diameter of constriction:
d2 = 12/1000  # m

# Upstream cross-sectional area:
A1 = np.pi*((d1/2)**2)  # m^2

# Cross-sectional area at the constriction:
A2 = np.pi*((d2/2)**2)  # m^2


def data_acquisition(filename, logger):
    """Reads patient data from a txt as a CSV and returns
    it as a NumPy array.

    This function opens a specified CSV file containing
    patient data, skips the header line, and processes
    each subsequent line to convert each value from string
    to float. It constructs a list of lists where each inner
    list represents a line from the CSV file with valid float
    values. Lines with any values that cannot be converted to
    float or contain NaN values are logged as errors and
    skipped. The resulting list of lists is then converted to
    a 2D NumPy array and returned.

    Args:
        filename (str): The path to the CSV file containing
        patient data.

    Returns:
        numpy.ndarray: A 2D NumPy array where each row represents
        a line from the CSV file, excluding the header and any
        lines with invalid inputs.
    """

    with open(filename, 'r') as patient_data:
        result = []
        csv_file = csv.reader(patient_data)
        next(csv_file)  # Skip the first line (header)

        for line in csv_file:
            try:
                time_point_lst = [float(x) for x in line]
                time_point_arr = np.array(time_point_lst)

                # Checking for NaN values
                if np.isnan(time_point_arr).any():
                    logger.error("Invalid Input")
                    continue

                result.append(time_point_lst)

            except ValueError:
                logger.error("Invalid Input")
                continue

    return np.array(result)


def flow_vs_time(data):
    """Processes raw patient data to calculate flow rate
    versus time from pressure measurements.

    This function takes raw data from a txt file represented
    as a 2D NumPy array and calculates the flow rate over time
    using the Venturi effect principles. The raw data array is
    expected to contain seven channels, including time,
    pressures at the patient-side during inspiration and expiration
    (p1_ins and p1_exp), and pressure at the constriction (p2).
    The analog-to-digital converter (ADC) values for these pressures
    are first converted to centimeters of water (cm-H2O) and then to
    Pascals (Pa) using known conversion factors. The flow rate is
    calculated based on the differential pressures across the Venturi
    tube, taking into account the cross-sectional areas at the ends
    (A1) and at the constriction (A2), and the density of moist air.
    The function handles the direction of flow by adjusting the sign
    of the flow rate based on whether the pressure during expiration
    exceeds that during inspiration.

    Args:
        data (ndarray): 2D ndarray containing 7 raw data channels
        with each row representing a time point. The expected order
        of channels is time, p2_ADC (constriction pressure), p1_ins_ADC
        (inspiration pressure), p1_exp_ADC (expiration pressure), and
        three additional channels (not used in this calculation) that
        represent data for the CPAP-side venturi tube.

    Returns:
        ndarray: A 2D ndarray where each row contains two elements:
        the timestamp and the corresponding calculated flow rate in
        units determined by the upstream and downstream pressures'
        conversion to Pascals and the Venturi equation application.

    The calculation of flow rate follows the Venturi formula,
    which relates the differential pressure to the flow rate through
    a constriction in a tube, considering the air density and the
    cross-sectional area ratio between the tube's main section and the
    constriction. If the expiration pressure is greater than the
    inspiration pressure, the flow rate is considered negative,
    indicating expiration flow.

    Note:
        The conversion factors used for ADC to cm-H2O and cm-H2O to
        Pa are specific to the sensor and conditions under which the
        data was collected.
    """
    result = []

    for row in data:
        time = row[0]
        p1_ins_ADC = row[2]
        p1_exp_ADC = row[3]
        p2_ADC = row[1]

        # adc-to-pressure conversions:
        # Venturi 1 Pressure (patient-side during inspiration):
        p1_ins_cmH2O = (25.4 / (14745 - 1638)) * (p1_ins_ADC - 1638)
        p1_ins_Pa = p1_ins_cmH2O * 98.0665  # Converted to Pa

        # Venturi 1 Pressure (patient-side during expiration):
        p1_exp_cmH2O = (25.4 / (14745 - 1638)) * (p1_exp_ADC - 1638)
        p1_exp_Pa = p1_exp_cmH2O * 98.0665  # Converted to Pa

        # Venturi 1 Pressure (patient-side) at the constriction:
        p2_cmH2O = (25.4 / (14745 - 1638)) * (p2_ADC - 1638)
        p2_Pa = p2_cmH2O * 98.0665  # Converted to Pa

        # flow_rate calculation:
        p1_Pa = max(p1_ins_Pa, p1_exp_Pa)  # Upstream pressure
        numerator = 2 * (p1_Pa - p2_Pa)
        denominator = moist_air_density * ((A1 / A2) ** 2 - 1)
        flow_rate = A1 * np.sqrt(numerator / denominator)
        if p1_exp_Pa > p1_ins_Pa:
            flow_rate *= -1

        result.append([time, flow_rate])

    return np.array(result)


def detect_peak_times(flow_rate_data):
    """Analyzes flow rate data to identify significant peaks after
    applying a lowpass filter, indicating moments of high flow rate
    activity. The function calculates the internal sampling rate
    based on the provided data's time intervals to tailor the filter
    to the specific dataset. A lowpass filter smoothens the flow rate
    signal by removing high-frequency noise, making the peak detection
    process more robust against minor fluctuations. Peak detection parameters
    such as minimum height, minimum number of samples between peaks
    (distance), and prominence are adjustable to fine-tune peak identification.

    Adapted from:
    https://www.samproell.io/posts/signal/peak-finding-python-js/

    Args:
        flow_rate_data (ndarray): A 2D ndarray with the first column
        representing time and the second column representing flow rate
        measurements.

    Returns:
        peak_times (ndarray): A 1D array of times at which significant peaks
        in flow rate occur, corresponding to events in the flow rate data.

        filtered_flow_rate (ndarray): The flow rate data after applying the
        lowpass filter, which smoothens the signal for more effective peak
        detection.

    Note:
        The effectiveness of peak detection depends on the choice of parameters
        like the cutoff frequency for the lowpass filter and the prominence of
        detected peaks. These should be chosen based on the characteristics of
        the datasets.
    """
    time = flow_rate_data[:, 0]
    flow_rate = flow_rate_data[:, 1]

    # sampling rate calculated based on time intervals between samples:
    time_diffs = np.diff(time)
    avg_time_diff = np.mean(time_diffs)
    sampling_rate = 1.0 / avg_time_diff
    cutoff_freq = 2

    # Creation of bandpass filter to smooth out noisy flow rate data:
    sos = scipy.signal.iirfilter(2, Wn=cutoff_freq, fs=sampling_rate,
                                 btype="lowpass", ftype="butter", output="sos")

    # Applying the bandpass filter using sosfilt
    filtered_flow_rate = scipy.signal.sosfilt(sos, flow_rate)

    # Parameters to adjust the sensitivity of peak detection:
    height = 0.00009  # Minimum height of peaks.
    distance = 80  # Minimum number of samples between peaks.
    prominence = np.std(filtered_flow_rate) * 0.5  # Frequency of peaks
    width = None  # Minimum width of peaks in samples.

    # Detecting peaks in the filtered signal:
    peaks, _ = scipy.signal.find_peaks(filtered_flow_rate,
                                       height=height,
                                       distance=distance,
                                       prominence=prominence,
                                       width=width)

    # Getting the times at which these peaks occur:
    peak_times = time[peaks]

    return peak_times, filtered_flow_rate


def plot_filtered_flow_rate_and_peaks(flow_rate_data,
                                      peak_times,
                                      filtered_flow_rate):
    """Creates three separate plots for raw and filtered
    flow rate data, and marks the detected peak times with
    vertical lines.

    Plot 1: Overlay of raw and filtered data for the first
    quarter of time.
    Plot 2: Raw flow rate data with vertical lines for peak
    times.
    Plot 3: Filtered flow rate data with vertical lines for
    peak times.

    Args:
        flow_rate_data (ndarray): 2D ndarray containing time
        in the first column and flow rate in the second.
    """
    time = flow_rate_data[:, 0]
    flow_rate = flow_rate_data[:, 1]

    # Un-comment if you wish to plot over a certain x-range:
    # first_quarter_end_time = time[len(time) // 4]

    # Plot 1: Overlayed plots
    plt.figure(figsize=(12, 6))
    plt.plot(time, flow_rate, label='Raw Flow Rate', alpha=0.5)
    plt.plot(time, filtered_flow_rate, label='Filtered Flow Rate', linewidth=2)
    for peak_time in peak_times:
        plt.axvline(x=peak_time, color='r', linestyle='--')
    # plt.xlim(left=time[0], right=first_quarter_end_time)
    plt.xlabel('Time (s)')
    plt.ylabel('Flow Rate')
    plt.title('First Quarter: Raw vs. Filtered Flow Rate')
    plt.legend()
    plt.show()

    # Plot 2: Raw flow rate with peaks
    plt.figure(figsize=(12, 6))
    plt.plot(time, flow_rate, label='Raw Flow Rate', alpha=0.7)
    for peak_time in peak_times:
        plt.axvline(x=peak_time, color='r', linestyle='--')
    # plt.xlim(left=time[0], right=first_quarter_end_time)
    plt.xlabel('Time (s)')
    plt.ylabel('Flow Rate')
    plt.title('Raw Flow Rate with Detected Peaks')
    plt.show()

    # Plot 3: Filtered flow rate with peaks
    plt.figure(figsize=(12, 6))
    plt.plot(time, filtered_flow_rate, label='Filtered Flow Rate',
             linewidth=2)
    for peak_time in peak_times:
        plt.axvline(x=peak_time, color='r', linestyle='--')
    # plt.xlim(left=time[0], right=first_quarter_end_time)
    plt.xlabel('Time (s)')
    plt.ylabel('Flow Rate')
    plt.title('Filtered Flow Rate with Detected Peaks')
    plt.show()


def apnea_events(peak_times):
    """Calculates the number of apnea events from the
    detected peak times. An apnea event is identified
    when the time interval between consecutive
    breaths exceeds 10 seconds.

    Args:
        peak_times (ndarray): 1D array containing the
        times at which significant peaks in flow rate
        occur.

    Returns:
        int: The number of apnea events detected in
        the data.
    """
    intervals = np.diff(peak_times)
    apnea_count = np.sum(intervals > 10)
    return int(apnea_count)


def calculate_leakage(flow_rate_data, logger):
    """This function calculates the total
    leakage of the CPAP mask by integrating the flow
    rate over time. This is done because leakage is calculated
    by determining the total net flow through Venturi 1 Positive
    leakage indicates air loss due to leaks in the system.

    Args:
        flow_rate_data (ndarray): A 2D ndarray where each
        row contains two elements: the timestamp and the
        corresponding calculated flow rate.

    Returns:
        float: The total volume of air leaked in L. Negative
        values indicate measurement or calculation errors.
    """
    time = flow_rate_data[:, 0]
    q = flow_rate_data[:, 1]
    leakage_m3 = np.trapz(q, x=time)  # Integral of q over t gives V in m^3
    leakage_liters = leakage_m3 * 1000  # Convert m^3 to liters

    if leakage_liters < 0:
        logger.warning("Negative leakage detected.")

    return leakage_liters


def calculate_metrics(flow_rate_data, peak_times, apneas, leakage):
    """This function consolidates duration of data acquisition,
    number of breaths, breath rate, breath times, apnea count,
    and leakage into a single metrics dictionary.

    Args:
        flow_rate_data (ndarray): A 2D NumPy array with time in the
        first column and flow rate in the second.

        peak_times (ndarray): A 1D array of times at which significant
        flow rate peaks were detected.

        apneas (int): The count of apnea events detected in the data.

        leakage (float): The total volume of air leakage detected,
        adjusted for direction.

    Returns:
        dict: A dictionary of calculated metrics including total
        duration, number of breaths, breath rate per minute, times
        of breaths, apnea count, and total leakage.
    """
    time = flow_rate_data[:, 0]
    duration = time[-1] - time[0]

    metrics = {
        "duration": round(duration, 3),
        "breaths": len(peak_times),
        "breath_rate_bpm": (
            round(len(peak_times) / (duration / 60) if duration > 0 else 0,
                  3)),
        "breath_times": list(peak_times),
        "apnea_count": apneas,
        "leakage": round(leakage, 3)
    }
    return metrics


def json_dump(filename, metrics):
    """Saves calculated metrics to a JSON file.

    This function takes a filename and a dictionary of metrics,
    then creates a JSON file with the same base filename but with
    a .json extension. The metrics are written to this file in a
    human-readable format with an indentation of 4 spaces, making
    it easy to view the data structure.

    Args:
        filename (str): The base name for the output file, without an
        extension. The function will add '.json' to this base name to
        create the full filename for the JSON output.

        metrics (dict): A dictionary containing key-value pairs of metrics
        calculated from the patient's flow rate data. These metrics include
        the duration of the data, number of breaths, breathing rate, times
        of each breath, number of apnea events, and total leakage.

    Example of `metrics` dictionary:
        {
            "duration": 300.5,
            "breaths": 120,
            "breath_rate_bpm": 24.0,
            "breath_times": [0.5, 1.2, 1.9, ...],
            "apnea_count": 2,
            "leakage": 50.0
        }
    """
    filename += '.json'
    with open(filename, 'w') as file:
        json.dump(metrics, file, indent=4)


def main(filename):
    """Main function to process CPAP data from a text file,
    calculate metrics, and save the results to a JSON file.

    This function orchestrates the flow of data from
    acquisition through processing, analysis, and finally
    saving the results. It checks the file extension, reads
    patient data, calculates the flow rate over time, identifies
    significant peaks in the flow rate data, calculates the number
    of apnea events and the total leakage, compiles all relevant
    metrics, and saves these metrics to a JSON file named after
    the patient. The process is logged for monitoring and debugging
    purposes.

    Args:
        filename (str): The path to the text file containing raw patient
        data. The file must have a '.txt' extension. The filename
        (excluding the path and extension) is used to name the output JSON
        file, thus it should be descriptive of the patient or session being
        analyzed.

    The analysis includes the following steps:
    - Checking the file extension for validity.

    - Logging the start of data analysis.

    - Reading patient data from the specified file.

    - Calculating the flow rate over time from the pressure measurements.

    - Detecting significant peaks in the flow rate data, which correspond
    to breaths.

    - Calculating the number of apnea events, based on the timing of the peaks.

    - Calculating the total leakage from the CPAP mask.

    - Compiling the duration of the dataset, the number of breaths, the average
    breath rate, the times of each breath, the number of apnea events,
    and the total leakage into a dictionary of metrics.

    - Saving the metrics dictionary to a JSON file for later analysis or
    reporting.
    """
    if filename[-4:] != '.txt':
        print("FileError: File must have the '.txt' extension")
    patient_name = filename[12:-4]

    patient_log = f'{patient_name}.log'

    # Creating a logger for the current patient:
    logger = logging.getLogger(patient_name)
    logger.setLevel(logging.INFO)

    # Prevent logger warning from appearing in terminal window:
    file_handler = logging.FileHandler(patient_log, 'w')
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info(f"Data analysis for {patient_name} is beginning...")

    # Analysis begins below:
    data = data_acquisition(filename, logger)
    flow_rate = flow_vs_time(data)
    peak_times, filtered_flow_rate = detect_peak_times(flow_rate)

    # Un-comment the following line if you wish to plot:
    # plot_filtered_flow_rate_and_peaks(flow_rate, peaks, filtered_flow_rate)

    apneas = apnea_events(peak_times)
    leakage = calculate_leakage(flow_rate, logger)
    metrics = calculate_metrics(flow_rate, peak_times, apneas, leakage)
    json_dump(patient_name, metrics)

    logger.info(f"Data analysis for {patient_name} has ended.")


if __name__ == "__main__":
    target_folder = 'sample_data/'
    for i in range(1, 9):
        patient_filename = f'patient_{i:02}.txt'
        path = target_folder + patient_filename
        main(path)
