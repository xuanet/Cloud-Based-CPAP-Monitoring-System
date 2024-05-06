import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cpap_analysis as ca
import logging
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
import io
import requests
from datetime import datetime
import json
import os


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def select_cpap_file():
    """Open a file dialog to select a CPAP data file.

    This function opens a file dialog window that allows
    the user to navigate their file system and select a
    CPAP data file. The selected file path is returned as
    a string. If no file is selected, the function returns
    None.

    :return: str containing the path to the selected
             file, or None if no file was selected
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    file_path = filedialog.askopenfilename(
        title="Select CPAP Data File",
        filetypes=[("Text Files", "*.txt")]
    )
    return file_path


def process_cpap_data(file_path):
    """Process the CPAP data file and calculate metrics.

    This function takes the path to a CPAP data file and
    processes the data using the cpap_analysis module. It
    calculates various metrics such as breathing rate,
    apnea events, and leakage. The calculated metrics are
    returned as a dictionary. If an error occurs during
    processing, the function returns None.

    :param file_path: str containing the path to the
                      CPAP data file

    :return: dict containing the calculated metrics,
             or None if an error occurred
    """
    if file_path is None:
        raise TypeError(("expected str, bytes or "
                         "os.PathLike object, not NoneType"))

    try:
        data = ca.data_acquisition(file_path, logger)
        flow_rate = ca.flow_vs_time(data)
        peak_times, filtered_flow_rate = ca.detect_peak_times(flow_rate)
        apneas = ca.apnea_events(peak_times)
        leakage = ca.calculate_leakage(flow_rate, logger)
        metrics = ca.calculate_metrics(flow_rate,
                                       peak_times,
                                       apneas,
                                       leakage)
        metrics['flow_rate'] = flow_rate
        metrics['filtered_flow_rate'] = filtered_flow_rate
        return metrics
    except Exception as e:
        logger.error("Failed to process CPAP data: %s", e)
        messagebox.showerror("Error",
                             "Failed to process CPAP data."
                             " Check the log for details.")
        return None


def display_metrics(root, metrics, flow_rate, breathing_rate_label,
                    apnea_count_label, plot_label):
    """Display the calculated metrics and flow rate plot in the GUI.

    This function takes the calculated metrics and flow rate data
    and updates the corresponding GUI elements to display the
    information. The breathing rate and apnea count are displayed
    in their respective labels, and the flow rate data is plotted
    and displayed in the plot label.

    :param root: tk.Tk root window
    :param metrics: dict containing the calculated metrics
    :param flow_rate: numpy array containing the flow rate data
    :param breathing_rate_label: ttk.Label to display the breathing rate
    :param apnea_count_label: ttk.Label to display the apnea count
    :param plot_label: ttk.Label to display the flow rate plot
    """
    if metrics:
        # Display the breathing rate and apnea count
        breathing_rate_label.config(
            text=f"Breathing Rate: {metrics['breath_rate_bpm']} BPM"
        )

        apnea_count = metrics['apnea_count']
        apnea_color = "red" if apnea_count >= 2 else "black"
        apnea_count_label.config(text=f"Apneas: {apnea_count}",
                                 foreground=apnea_color)

        # Create a Matplotlib figure and plot the flow rate vs. time
        fig, ax = plt.subplots(figsize=(6, 4), dpi=75)
        ax.plot(flow_rate[:, 0], flow_rate[:, 1], label='Flow Rate')
        ax.set_title("Flow Rate vs. Time")
        ax.set_xlabel("t (s)")
        ax.set_ylabel("Q (m³/sec)")
        ax.set_xlim(0, flow_rate[-1, 0])
        ax.grid(True)
        fig.tight_layout()

        # Save the plot as an image file in memory
        img_buf = io.BytesIO()
        fig.savefig(img_buf, format='png')
        img_buf.seek(0)

        # Open the image file using PIL
        plot_image = Image.open(img_buf)

        # Convert the PIL image to a PhotoImage for displaying in the GUI
        plot_photo = ImageTk.PhotoImage(plot_image)

        # Update the plot label with the new image
        plot_label.config(image=plot_photo)
        plot_label.image = plot_photo

    else:
        messagebox.showerror("Error",
                             "Failed to display CPAP data analysis results.")


def upload_data(root, patient_info, metrics, mrn_entry,
                room_number_entry, upload_button,
                update_button):
    """Upload patient data and metrics to the server.

    This function takes the patient information and calculated
    metrics and uploads them to the server. It first checks if
    the MRN or room number already exists in the database and
    prompts the user for confirmation if necessary. If the upload
    is successful, the GUI elements are updated accordingly, and
    the function returns True. If an error occurs during the upload,
    an error message is displayed, and the function returns False.

    :param root: tk.Tk root window
    :param patient_info: dict containing patient information
    :param metrics: dict containing the calculated metrics
    :param mrn_entry: ttk.Entry for the MRN input
    :param room_number_entry: ttk.Entry for the room number input
    :param upload_button: ttk.Button for uploading data
    :param update_button: ttk.Button for updating data

    :return: bool indicating whether the upload was successful
    """
    url = f"http://{INSTANCEURL}/check_exists"
    data = {
        "mrn": patient_info['mrn'].get(),
        "room_number": patient_info['room_number'].get()
    }
    files = {
            "data": ("data.json", json.dumps(data), "application/json"),
    }

    try:
        response = requests.post(url, files=files)
        response.raise_for_status()
        response_data = response.json()

        if 'exists' in response_data:
            field = response_data['exists']
            if field == 'mrn':
                confirm_mrn = messagebox.askyesno(
                    "Confirmation",
                    ("The MRN already exists. "
                     "Are you sure you want to "
                     "proceed with changing "
                     "the current MRN?")
                )
                if not confirm_mrn:
                    messagebox.showinfo("Info", "Upload canceled.")
                    return False
            elif field == 'room':
                confirm_room = messagebox.askyesno(
                    "Confirmation",
                    ("The room number is already occupied. "
                     "Are you sure you want to proceed with changing "
                     "the current room number?")
                )
                if not confirm_room:
                    messagebox.showinfo("Info", "Upload canceled.")
                    return False

            # Check CPAP pressure only if MRN or room number exists
            if not check_cpap_pressure(root, patient_info):
                return False
        else:
            # MRN and room number do not exist, skip CPAP pressure check
            pass

        # Perform the actual data upload
        url = f"http://{INSTANCEURL}/upload_data"
        data = {
            "mrn": patient_info['mrn'].get(),
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "name": patient_info['name'].get(),
            "currcpap": patient_info['cpap_pressure'].get(),
            "br": str(metrics['breath_rate_bpm']),
            "apnea": str(metrics['apnea_count']),
            "room_number": patient_info['room_number'].get()
        }
        plot_data = io.BytesIO()
        plt.savefig(plot_data, format='png')
        plot_data.seek(0)
        plot_bytes = plot_data.read()
        files = {
            "data": ("data.json", json.dumps(data), "application/json"),
            "plot": ("plot.png", plot_bytes, "image/png")
        }

        response = requests.post(url, files=files)
        response.raise_for_status()
        response_data = response.json()

        if 'error' in response_data:
            error_message = response_data['error']
            messagebox.showerror("Error", error_message)
            return False

        messagebox.showinfo("Success", "Data uploaded successfully.")

        mrn_entry.config(state="disabled")
        room_number_entry.config(state="disabled")
        patient_info['mrn_locked'] = True
        patient_info['room_number_locked'] = True
        upload_button.config(state="disabled")
        update_button.config(state="normal")

        periodic_cpap_update(root, patient_info)
        return True
    except requests.exceptions.HTTPError as e:
        error_message = response.json().get('error', "Unknown error occurred")
        messagebox.showerror("Upload Failed", error_message)
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Network error: {str(e)}")


def update_data(root, patient_info, metrics):
    """Update patient data and metrics on the server.

    This function takes the patient information and calculated metrics
    and updates them on the server. It sends a request to the server
    with the updated data. If the update is successful, a success
    message is displayed, and the function returns True. If an error
    occurs during the update, an error message is displayed, and the
    function returns False.

    :param root: tk.Tk root window
    :param patient_info: dict containing patient information
    :param metrics: dict containing the calculated metrics

    :return: bool indicating whether the update was successful
    """
    try:
        room_number = patient_info['room_number'].get()
        mrn = patient_info['mrn'].get()
        cpap_pressure = patient_info['cpap_pressure'].get()
    except tk.TclError as e:
        messagebox.showerror("Error",
                             ("Invalid input format. "
                              "Please enter valid values."))
        return False

    url = f"http://{INSTANCEURL}/update_patient_info"
    data = {
        "mrn": str(mrn),
        "name": patient_info['name'].get(),
        "currcpap": str(cpap_pressure),
        "br": str(metrics['breath_rate_bpm']),
        "apnea": str(metrics['apnea_count']),
        "mrn_locked": patient_info['mrn_locked'],
        "room_number_locked": patient_info['room_number_locked']
    }
    plot_data = io.BytesIO()
    plt.savefig(plot_data, format='png')
    plot_data.seek(0)
    plot_bytes = plot_data.read()
    files = {
        "data": ("data.json", json.dumps(data), "application/json"),
        "plot": ("plot.png", plot_bytes, "image/png")
    }

    try:
        response = requests.post(url, files=files)
        response.raise_for_status()
        try:
            response_data = response.json()
            messagebox.showinfo("Success",
                                "Patient information updated "
                                "successfully.")
        except requests.exceptions.JSONDecodeError:
            messagebox.showerror("Error", "Server encountered an error.")
        return True
    except requests.exceptions.HTTPError as e:
        try:
            error_message = response.json().get('error',
                                                ("Unknown error "
                                                 "occurred"))
        except requests.exceptions.JSONDecodeError:
            error_message = "Server encountered an error."
        messagebox.showerror("Update Failed", error_message)
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", ("Network Error: Server "
                                       "is not online. Please "
                                       "check the server connection."))
    return False


def patient_handler(root, patient_info, mrn_entry,
                    room_number_entry, upload_button,
                    update_button, file_selected_var,
                    file_name_label, breathing_rate_label,
                    apnea_count_label, plot_label,
                    file_selected_checkmark):
    """Handle the patient data and file selection.

    This function is the main handler for patient data and file
    selection. It opens a file dialog to select a CPAP data file,
    processes the data, and updates the GUI elements with the
    calculated metrics and plot. It also handles enabling and
    disabling the upload and update buttons based on the state
    of the MRN and room number fields.

    :param root: tk.Tk root window
    :param patient_info: dict containing patient information
    :param mrn_entry: ttk.Entry for the MRN input
    :param room_number_entry: ttk.Entry for the room number input
    :param upload_button: ttk.Button for uploading data
    :param update_button: ttk.Button for updating data
    :param file_selected_var: tk.BooleanVar indicating whether a
                              file is selected
    :param file_name_label: ttk.Label to display the selected file
                            name
    :param breathing_rate_label: ttk.Label to display the breathing
                                 rate
    :param apnea_count_label: ttk.Label to display the apnea count
    :param plot_label: ttk.Label to display the flow rate plot
    :param file_selected_checkmark: ttk.Label to display the file
                                    selection checkmark
    """
    cpap_file_path = select_cpap_file()
    if cpap_file_path:
        metrics = process_cpap_data(cpap_file_path)
        if metrics:
            if (not patient_info['mrn_locked'] and
               not patient_info['room_number_locked']):
                upload_button.config(state="normal")
                update_button.config(state="disabled")
            else:
                upload_button.config(state="disabled")
                update_button.config(state="normal")
            patient_info['metrics'] = metrics
            file_selected_var.set(True)
            file_selected_checkmark.config(text="✓", foreground="green")
            file_name = os.path.basename(cpap_file_path)
            file_name_label.config(text="File Selected: "+file_name)
            display_metrics(root, metrics, metrics['flow_rate'],
                            breathing_rate_label, apnea_count_label,
                            plot_label)
    else:
        logger.info("No CPAP data file selected.")
        file_selected_var.set(False)
        file_selected_checkmark.config(text="x", foreground="red")
        file_name_label.config(text="")


def check_cpap_pressure(root, patient_info):
    """Check the entered CPAP pressure against the value in the database.

    This function checks the CPAP pressure entered by the user against
    the value stored in the database for the given MRN and room number.
    If the entered value does not match the database value, the user is
    prompted to update to the database value. If the user confirms, the
    CPAP pressure entry is updated with the database value.

    :param root: tk.Tk root window
    :param patient_info: dict containing patient information

    :return: bool indicating whether the check was successful
    """
    url = f"http://{INSTANCEURL}/fetch_cpap_pressure"
    data = {
        "mrn": patient_info['mrn'].get(),
        "room_number": patient_info['room_number'].get()
    }
    files = {
            "data": ("data.json", json.dumps(data), "application/json"),
    }
    try:
        response = requests.post(url, files=files)
        response.raise_for_status()
        response_data = response.json()

        if 'error' in response_data:
            error_message = response_data['error']
            messagebox.showerror("Error", error_message)
            return False

        if 'cpap_pressure' in response_data:
            db_cpap_pressure = float(response_data['cpap_pressure'])
            entered_cpap_pressure = patient_info['cpap_pressure'].get()

            if not entered_cpap_pressure:
                # If entered CPAP pressure is an empty string => database value
                patient_info['cpap_pressure'].set(str(db_cpap_pressure))
            else:
                entered_cpap_pressure = float(entered_cpap_pressure)
                if entered_cpap_pressure != db_cpap_pressure:
                    confirm = messagebox.askyesno(
                        "CPAP Pressure Mismatch",
                        ("The entered CPAP pressure "
                         "({}) does not "
                         "match the value in the database "
                         "({}). Do you want "
                         "to update to the database's CPAP "
                         "pressure?".format(entered_cpap_pressure,
                                            db_cpap_pressure))
                    )
                    if confirm:
                        patient_info['cpap_pressure'].set(
                            str(db_cpap_pressure))

        return True
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Network error: {str(e)}")
        return False


def periodic_cpap_update(root, patient_info):
    """Periodically check for updates to the CPAP pressure from the
       monitoring station.

    This function periodically checks for updates to the CPAP pressure
    from the monitoring station. It sends a request to the server with
    the current MRN, room number, and CPAP pressure. If the server
    responds with an updated CPAP pressure, the user is prompted to
    update their local value. If the user confirms, the CPAP pressure
    entry is updated with the new value received from the server.

    :param root: tk.Tk root window
    :param patient_info: dict containing patient information
    """
    if patient_info['mrn_locked'] and patient_info['room_number_locked']:
        url = f"http://{INSTANCEURL}/fetch_cpap_pressure"
        data = {
            "mrn": patient_info['mrn'].get(),
            "room_number": patient_info['room_number'].get(),
            "currcpap": patient_info['cpap_pressure'].get(),
        }
        files = {
                "data": ("data.json", json.dumps(data), "application/json"),
        }
        try:
            response = requests.post(url, files=files)
            response.raise_for_status()
            response_data = response.json()

            if 'error' in response_data:
                error_message = response_data['error']
                messagebox.showerror("Error", error_message)
            elif 'cpap_pressure' in response_data:
                db_cpap_pressure = float(response_data['cpap_pressure'])
                entered_cpap_pressure = float(
                    patient_info['cpap_pressure'].get())

                if entered_cpap_pressure != db_cpap_pressure:
                    confirm = messagebox.askyesno(
                        "CPAP Pressure Update",
                        ("The monitoring station has set a new CPAP "
                         "pressure ({}). Do you want "
                         "to update to the monitoring station's CPAP "
                         "pressure?".format(db_cpap_pressure))
                    )
                    if confirm:
                        patient_info['cpap_pressure'].set(
                            str(db_cpap_pressure))
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Network error: {str(e)}")

    root.after(15000, periodic_cpap_update, root, patient_info)


def reset_fields(root, patient_info, mrn_entry, room_number_entry,
                 upload_button, update_button, file_selected_var,
                 file_name_label, breathing_rate_label, apnea_count_label,
                 plot_label, file_selected_checkmark):
    """Reset all input fields and clear the displayed metrics and plot.

    This function resets all the input fields to their default values
    and clears the displayed metrics and plot. It also resets the state
    of the MRN and room number fields, allowing them to be edited again.
    The upload and update buttons are disabled, and the file selection
    checkmark is reset to indicate that no file is selected.

    :param root: tk.Tk root window
    :param patient_info: dict containing patient information
    :param mrn_entry: ttk.Entry for the MRN input
    :param room_number_entry: ttk.Entry for the room number input
    :param upload_button: ttk.Button for uploading data
    :param update_button: ttk.Button for updating data
    :param file_selected_var: tk.BooleanVar indicating whether a file is
                              selected
    :param file_name_label: ttk.Label to display the selected file name
    :param breathing_rate_label: ttk.Label to display the breathing rate
    :param apnea_count_label: ttk.Label to display the apnea count
    :param plot_label: ttk.Label to display the flow rate plot
    :param file_selected_checkmark: ttk.Label to display the file
                                    selection checkmark
    """
    patient_info['name'].set("")
    patient_info['mrn'].set("0")
    patient_info['room_number'].set("0")
    patient_info['cpap_pressure'].set("0.0")
    patient_info['mrn_locked'] = False
    patient_info['room_number_locked'] = False
    mrn_entry.config(state="normal")
    room_number_entry.config(state="normal")
    upload_button.config(state="disabled")
    update_button.config(state="disabled")
    file_selected_var.set(False)
    file_name_label.config(text="")
    file_selected_checkmark.config(text="x", foreground="red")

    # Clear the breathing rate, apnea count, and plot
    breathing_rate_label.config(text="")
    apnea_count_label.config(text="")
    plot_label.config(image="")

    root.after_cancel(root.after_id)  # Cancel the periodic CPAP update


def on_closing(root):
    """Handles the window close event.

    This function is called when the user attempts to close the
    main window. It displays a confirmation dialog asking the
    user if they really want to quit. If the user confirms, the
    periodic CPAP update is canceled, and the main window is
    destroyed, effectively closing the application.

    :param root: tk.Tk root window
    """
    if messagebox.askyesno("Quit", "Do you really want to quit?"):
        root.after_cancel(root.after_id)  # Cancel the pending after call
        root.destroy()
        root.quit()  # Exit the Tkinter event loop


def main():
    """Create and run the patient-side GUI client.

    This is the main function of the patient-side GUI client. It
    creates the main window, sets up the GUI elements, and initializes
    the necessary variables. It also sets up the callbacks for button
    clicks and window close events. The main window is then displayed,
    and the Tkinter event loop is started, allowing the user to interact
    with the application.
    """
    root = tk.Tk()
    root.title("Patient-side GUI Client")

    patient_info = {
        'name': tk.StringVar(),
        'mrn': tk.StringVar(value="0"),
        'room_number': tk.StringVar(value="0"),
        'cpap_pressure': tk.StringVar(value="0.0"),
        'mrn_locked': False,
        'room_number_locked': False
    }

    ttk.Label(root, text="Patient Name:").grid(row=0,
                                               column=0,
                                               padx=5,
                                               pady=5,
                                               sticky=tk.W)
    ttk.Entry(root, textvariable=patient_info['name']).grid(row=0,
                                                            column=1,
                                                            padx=5,
                                                            pady=5)

    ttk.Label(root, text="Medical Record Number (MRN):").grid(row=1,
                                                              column=0,
                                                              padx=5,
                                                              pady=5,
                                                              sticky=tk.W)
    ttk.Entry(root, textvariable=patient_info['mrn']).grid(row=1,
                                                           column=1,
                                                           padx=5,
                                                           pady=5)

    ttk.Label(root, text="Room Number:").grid(row=2,
                                              column=0,
                                              padx=5,
                                              pady=5,
                                              sticky=tk.W)
    ttk.Entry(root, textvariable=patient_info['room_number']).grid(row=2,
                                                                   column=1,
                                                                   padx=5,
                                                                   pady=5)

    ttk.Label(root, text="CPAP Pressure (cmH\u2082O):").grid(row=3,
                                                             column=0,
                                                             padx=5,
                                                             pady=5,
                                                             sticky=tk.W)
    ttk.Entry(root, textvariable=patient_info['cpap_pressure']).grid(row=3,
                                                                     column=1,
                                                                     padx=5,
                                                                     pady=5)

    file_selected_var = tk.BooleanVar(value=False)
    file_name_label = ttk.Label(root, text="")
    file_name_label.grid(row=5, column=0, padx=5, pady=5, columnspan=2)

    select_file_button_frame = ttk.Frame(root)
    select_file_button_frame.grid(row=4, column=0, padx=5, pady=10,
                                  columnspan=2)

    mrn_entry = ttk.Entry(root, textvariable=patient_info['mrn'])
    mrn_entry.grid(row=1, column=1, padx=5, pady=5)

    room_number_entry = ttk.Entry(root,
                                  textvariable=patient_info['room_number'])
    room_number_entry.grid(row=2, column=1, padx=5, pady=5)

    breathing_rate_label = ttk.Label(root, text="")
    breathing_rate_label.grid(column=0, row=6, padx=10, pady=5, sticky=tk.W)

    apnea_count_label = ttk.Label(root, text="")
    apnea_count_label.grid(column=0, row=7, padx=10, pady=5, sticky=tk.W)

    plot_label = ttk.Label(root)
    plot_label.grid(column=0, row=8, padx=10, pady=10, columnspan=2)

    select_file_button = ttk.Button(
        select_file_button_frame,
        text="Select CPAP File",
        command=lambda: patient_handler(root, patient_info,
                                        mrn_entry, room_number_entry,
                                        upload_button, update_button,
                                        file_selected_var, file_name_label,
                                        breathing_rate_label,
                                        apnea_count_label, plot_label,
                                        file_selected_checkmark)
    )
    select_file_button.pack(side=tk.LEFT)

    file_selected_checkmark = ttk.Label(select_file_button_frame, text="✓",
                                        foreground="green")
    file_selected_checkmark.pack(side=tk.LEFT, padx=5)

    upload_button = ttk.Button(
        root,
        text="Upload Data",
        command=lambda: upload_data(root, patient_info,
                                    patient_info['metrics'], mrn_entry,
                                    room_number_entry, upload_button,
                                    update_button),
        state="disabled"
    )
    upload_button.grid(row=9, column=0, padx=5, pady=5)

    update_button = ttk.Button(
        root,
        text="Update Data",
        command=lambda: update_data(root, patient_info,
                                    patient_info['metrics']),
        state="disabled"
    )
    update_button.grid(row=9, column=1, padx=5, pady=5)

    def update_checkmark():
        """Update the file selection checkmark based on the file selection
           status.

        This function periodically checks the status of the file selection
        and updates the file selection checkmark accordingly. If a file is
        selected, the checkmark is set to a green checkmark symbol (✓). If
        no file is selected, the checkmark is set to a red cross symbol (x).

        The function uses the after method to schedule itself to be called
        repeatedly every 100 milliseconds. This allows the checkmark to be
        updated in real-time based on the file selection status.

        The function also checks if the root window still exists before
        updating the checkmark. This is to avoid potential errors that may
        occur if the window is closed while the function is still scheduled
        to be called.
        """
        if root.winfo_exists():
            if file_selected_var.get():
                file_selected_checkmark.config(text="✓", foreground="green")
            else:
                file_selected_checkmark.config(text="x", foreground="red")
            # avoiding error when closing:
            root.after_id = root.after(100, update_checkmark)

    reset_button = ttk.Button(
        root,
        text="Reset",
        command=lambda: reset_fields(root, patient_info, mrn_entry,
                                     room_number_entry, upload_button,
                                     update_button, file_selected_var,
                                     file_name_label, breathing_rate_label,
                                     apnea_count_label, plot_label,
                                     file_selected_checkmark)
    )
    reset_button.grid(row=10, column=0, padx=5, pady=5)

    close_button = ttk.Button(root, text="Close",
                              command=lambda: on_closing(root))
    close_button.grid(row=10, column=1, padx=5, pady=5)

    root.after_id = root.after(100, update_checkmark)
    root.mainloop()


if __name__ == "__main__":
    INSTANCEURL = input('write your url\n')
    if len(INSTANCEURL) < 3:
        INSTANCEURL = "localhost:5001"
    main()
