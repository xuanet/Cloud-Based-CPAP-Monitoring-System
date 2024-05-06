import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cpap_analysis as ca
import logging
import requests
from PIL import Image, ImageTk
import base64
import io
import matplotlib.image as mpimg
from io import BytesIO
from datetime import datetime

image_size = 350


def convert_date_string(input_string):
    """Convert a date string from one format to another.

    This function takes a date string in the format
    '%a, %d %b %Y %H:%M:%S %Z' and converts it to the
    format '%Y-%m-%d %H:%M:%S'. If the input string is
    not in the expected format, the function returns a
    default date string.

    :param input_string: str containing the date string
                         to convert

    :return: str containing the converted date string
    """
    # Parse the input string into a datetime object
    try:
        input_datetime = datetime.strptime(
            input_string, '%a, %d %b %Y %H:%M:%S %Z')
    except ValueError:
        print("invalid datetime format")
        return '2000-01-01 12:00:00'
    # Format the datetime object into the desired output format
    output_string = input_datetime.strftime('%Y-%m-%d %H:%M:%S')

    return output_string


def save_plot(b64_str, value='lorem', mrn='ipsum', noname=True):
    """Save a plot image from a base64-encoded string.

    This function takes a base64-encoded string representing a
    plot image and saves it to a file. The filename is generated
    based on the provided value and MRN. If the noname parameter
    is set to True, a default filename is used instead.

    :param b64_str: str containing the base64-encoded plot image
    :param value: str containing the value to include in the
                  filename (default: 'lorem')
    :param mrn: str containing the MRN to include in the filename
                (default: 'ipsum')
    :param noname: bool indicating whether to use a default
                   filename (default: True)
    """
    if len(b64_str) < 10:
        print("no plot to save")
        return
    if value == '' or mrn == '':
        print("no image to save")
        return
    image_bytes = base64.b64decode(b64_str)
    if not noname:
        new_filename = f"{mrn}, {value}"
    else:
        new_filename = "nis_output.png"
    with open(new_filename, "wb") as out_file:
        out_file.write(image_bytes)
        print('save success')


def main():
    """Create and run the monitoring station GUI.

    This is the main function of the monitoring station GUI.
    It creates the main window, sets up the GUI elements, and
    initializes the necessary variables. It also sets up the
    callbacks for various events such as button clicks, dropdown
    selections, and traced variable changes.

    The function sets up periodic tasks using the after method
    to fetch room numbers and datetimes from the server at
    regular intervals.

    Finally, it starts the Tkinter event loop to display the
    GUI and handle user interactions.
    """

    occupied_rooms = ()
    valid_datetimes = ()

    def fetch_room_numbers():
        """Fetch occupied room numbers from the server.

        This function sends a GET request to the server to
        fetch the occupied room numbers. It updates the
        occupied_rooms variable with the received room
        numbers and updates the room selection dropdown
        with the new values.

        The function is set to be called repeatedly every
        1000 milliseconds (1 second) using the after
        method.
        """
        """api request to server to get rooms"""
        nonlocal occupied_rooms
        r = requests.get(f"http://{INSTANCEURL}/fetch_room_numbers")
        occupied_rooms = tuple(r.json())
        room_select_dropdown['values'] = occupied_rooms
        root.after(1000, fetch_room_numbers)

    def display_cpap_calculated_data(name, index, mode):
        """Displays the br, apnea count, and q vs t graph
           for the selected patient

        This function retrieves the calculated CPAP data
        from the server for the selected patient based on
        the room number. It updates the GUI elements with
        the retrieved data, including the MRN, patient name,
        record creation timestamp, CPAP pressure, breathing
        rate, apnea events, and the flow rate plot.

        If the number of apnea events is greater than or equal
        to 2, the apnea event text is highlighted in red.

        :param name: str containing the name of the traced
                     variable
        :param index: str containing the index of the traced
                      variable
        :param mode: str containing the mode of the traced
                     variable
        """
        url = f"http://{INSTANCEURL}/fetch_cpap_calculated_data"
        if room_select_var.get() != '':
            room_num = {"room_number": int(room_select_var.get())}
            r = requests.post(url, json=room_num)
            r = r.json()
            patient_mrn_var.set(r[0])
            cpap_metrics_var.set(
                (f"MRN: {r[0]}\n"
                 f"Name: {r[1]}\n"
                 f"Record created: {r[2]}\n"
                 f"CPAP Pressue (cmH\N{SUBSCRIPT TWO}O): {r[3]}\n"
                 f"Breathing rate: {r[4]}\n"
                 f"Apnea events: {r[5]}"))
            cpap_current_var.set(r[2])
            cpap_plot_var_b64.set(r[6])
            patient_info.delete("1.0", tk.END)
            patient_info.insert(tk.END, cpap_metrics_var.get())
            if r[5] >= 2:
                patient_info.tag_add("line", f"{6}.0", f"{6}.end")
                patient_info.tag_config("line", foreground='red')
            else:
                patient_info.tag_add("line", f"{6}.0", f"{6}.end")
                patient_info.tag_config(
                    "line", foreground=patient_info.cget("foreground"))

            # code to plot dummy images, set dt_var to ''

    def plot_cpap(name, index, mode):
        """Plot the flow rate data for the selected patient.

        This function retrieves the base64-encoded flow rate
        plot from the traced variable and decodes it into an
        image. It then resizes the image to fit the specified
        dimensions and displays it in the GUI using a Tkinter
        Label.

        If the decoded data is not a valid image, a default
        image is displayed instead.

        :param name: str containing the name of the traced
                     variable
        :param index: str containing the index of the traced
                      variable
        :param mode: str containing the mode of the traced
                     variable
        """
        image_bytes = base64.b64decode(cpap_plot_var_b64.get())
        try:
            image = Image.open(BytesIO(image_bytes))
        except BaseException:
            print("bad file format")
            image = load_and_size_image()
            photo_image = ImageTk.PhotoImage(image)
            # Create a Tkinter Label to display the image
            image_label.config(image=photo_image)
            image_label.image = photo_image
            return
        image = load_and_size_image(image)

        photo_image = ImageTk.PhotoImage(image)

        # Create a Tkinter Label to display the image
        image_label.config(image=photo_image)
        image_label.image = photo_image

    def load_and_size_image(filename=None):
        """Load an image file and resize it to fit the specified
           dimensions.

        This function loads an image file and resizes it to fit
        within the specified width and height dimensions while
        maintaining the aspect ratio. If no filename is provided,
        a default image is loaded.

        :param filename: str containing the path to the image
                         file (default: None)

        :return: PIL.Image object containing the resized image
        """
        if filename is None:
            raw_pil_image = Image.open("nis.png")
        else:
            raw_pil_image = filename
        final_width = image_size
        final_height = image_size
        alpha_x = final_width / raw_pil_image.size[0]
        alpha_y = final_height / raw_pil_image.size[1]
        alpha = min(alpha_x, alpha_y)
        new_x = round(raw_pil_image.size[0] * alpha)
        new_y = round(raw_pil_image.size[1] * alpha)
        pil_image = raw_pil_image.resize((new_x, new_y))
        return pil_image

    def fetch_datetimes():
        """Fetch valid datetimes for the selected patient from
           the server.

        This function sends a POST request to the server to
        fetch the valid datetimes for the selected patient
        based on the MRN. It updates the valid_datetimes variable
        with the received datetimes and updates the datetime
        selection dropdown with the new values.

        The function is set to be called repeatedly every
        1000 milliseconds (1 second) using the after method.
        """
        nonlocal valid_datetimes
        if patient_mrn_var.get() != 0:
            out_json = {"mrn": patient_mrn_var.get()}
            r = requests.post(
                f"http://{INSTANCEURL}/fetch_datetimes_for_patient",
                json=out_json)
            r = r.json()
            valid_datetimes = [convert_date_string(dt) for dt in r]
            valid_datetimes = tuple(valid_datetimes)
            dt_dropdown['values'] = valid_datetimes
        root.after(1000, fetch_datetimes)

    def plot_both(name, index, mode):
        """Plot the current and historical flow rate data for
           the selected patient.

        This function retrieves the current and historical
        flow rate plots from the server based on the selected
        datetime and MRN. It decodes the base64-encoded plot
        data into images, resizes the images to fit the
        specified dimensions, and displays them in the GUI
        using Tkinter Labels.

        :param name: str containing the name of the traced
                     variable
        :param index: str containing the index of the traced
                      variable
        :param mode: str containing the mode of the traced
                     variable
        """
        url = f"http://{INSTANCEURL}/fetch_plot_from_datetime_and_mrn"
        if dt_select_var.get() != '':
            out_json = {"datetime": dt_select_var.get(),
                        "mrn": patient_mrn_var.get()}
            r = requests.post(url, json=out_json)
            r = r.json()
            cpap_plot_historic_var_b64.set(r)

            image_bytes = base64.b64decode(cpap_plot_var_b64.get())
            image = Image.open(BytesIO(image_bytes))
            image = load_and_size_image(image)

            photo_image = ImageTk.PhotoImage(image)

            # Create a Tkinter Label to display the image
            image_label2.config(image=photo_image)
            image_label2.image = photo_image

            ######

            image_bytes = base64.b64decode(cpap_plot_historic_var_b64.get())
            image = Image.open(BytesIO(image_bytes))
            image = load_and_size_image(image)

            photo_image = ImageTk.PhotoImage(image)

            # Create a Tkinter Label to display the image
            image_label3.config(image=photo_image)
            image_label3.image = photo_image

    def send_cpap():
        """Send the updated CPAP pressure to the server for the
           selected patient.

        This function sends a POST request to the server to
        update the CPAP pressure for the selected patient based
        on the room number. It retrieves the updated CPAP pressure
        value from the corresponding entry field in the GUI.

        If the room number or CPAP pressure value is not
        selected/entered, or if the CPAP pressure value is outside
        the valid range (4-25), the function does not send the
        request and prints an appropriate message.
        """
        url = f"http://{INSTANCEURL}/send_cpap"
        if room_select_var.get() == '' or update_cpap_var.get() == '':
            print('no room / new value selected')
            return
        try:
            value = float(update_cpap_var.get())
        except ValueError:
            print("invalid cpap input")
            return
        if value < 4 or value > 25:
            print("CPAP value must be between 4 and 25")
            return
        out_json = {"room_number": int(room_select_var.get()), "cpap": value}
        r = requests.post(url, json=out_json)

    def reset(name, index, mode):
        """Reset the GUI elements to their default state.

        This function resets various GUI elements to their
        default state. It clears the selected datetime,
        historical flow rate plot, and CPAP pressure input field.
        It also resets the displayed images to the default image.

        :param name: str containing the name of the traced variable
        :param index: str containing the index of the traced variable
        :param mode: str containing the mode of the traced variable
        """
        dt_select_var.set('')
        cpap_plot_historic_var_b64.set('')
        update_cpap_var.set('')

        pil_image2 = load_and_size_image()
        tk_image2 = ImageTk.PhotoImage(pil_image2)
        image_label2.config(image=tk_image2)
        image_label2.image = tk_image2

        pil_image3 = load_and_size_image()
        tk_image3 = ImageTk.PhotoImage(pil_image3)
        image_label3.config(image=tk_image3)
        image_label3.image = tk_image3

    root = tk.Tk()
    root.title("Monitoring Station")
    root.geometry("900x1400")

    cpap_metrics_var = tk.StringVar()

    # select room number

    padding = 10

    room_select_label = ttk.Label(root, text='Select room')
    room_select_label.grid(row=0, column=0, sticky=tk.N,
                           padx=padding, pady=padding)
    room_select_var = tk.StringVar()
    room_select_dropdown = (
        ttk.Combobox(root,
                     textvariable=room_select_var,
                     values=occupied_rooms,
                     state="readonly"))
    room_select_dropdown.grid(
        row=0, column=1, sticky=tk.N, padx=padding, pady=padding)

    # cpap display

    # cpap_metrics_var = tk.StringVar()
    patient_info = tk.Text(root, width=50, height=6, bg=root.cget('bg'))
    # patient_info.insert(tk.END, cpap_metrics_var)
    patient_info.grid(row=1, column=0, rowspan=3, columnspan=2, sticky=tk.N,
                      padx=padding, pady=padding)

    # plot display

    cpap_plot_var_b64 = tk.StringVar()
    pil_image = load_and_size_image()
    tk_image = ImageTk.PhotoImage(pil_image)
    image_label = ttk.Label(root, image=tk_image)
    image_label.image = tk_image
    image_label.grid(row=0, column=2, padx=padding,
                     pady=padding, rowspan=3, columnspan=2)

    # plot label

    top_plot_label = ttk.Label(root, text='Most recent plot')
    top_plot_label.grid(row=4, column=2, padx=padding,
                        pady=padding, columnspan=2)

    # dt dropdown
    patient_mrn_var = tk.IntVar()
    dt_label = ttk.Label(root, text='Select previous metric')
    dt_label.grid(row=5, column=0,
                  padx=padding, pady=padding)
    dt_select_var = tk.StringVar()
    dt_dropdown = (
        ttk.Combobox(root,
                     textvariable=dt_select_var,
                     values=valid_datetimes,
                     state="readonly"))
    dt_dropdown.grid(
        row=5, column=1, padx=3*padding, pady=3*padding)

    # display historical plot
    pil_image2 = load_and_size_image()
    tk_image2 = ImageTk.PhotoImage(pil_image2)
    image_label2 = ttk.Label(root, image=tk_image2)
    image_label2.image = tk_image2
    image_label2.grid(row=6, column=0, rowspan=3, columnspan=2)

    cpap_plot_historic_var_b64 = tk.StringVar()
    pil_image3 = load_and_size_image()
    tk_image3 = ImageTk.PhotoImage(pil_image3)
    image_label3 = ttk.Label(root, image=tk_image3)
    image_label3.image = tk_image3
    image_label3.grid(row=6, column=2, rowspan=3, columnspan=2)

    # left/right labels

    left_plot_label = ttk.Label(root, text='Most recent plot')
    left_plot_label.grid(row=9, column=0, padx=padding,
                         pady=padding, columnspan=2)
    right_plot_label = ttk.Label(root, text='Historic plot')
    right_plot_label.grid(row=9, column=2, padx=padding,
                          pady=padding, columnspan=2)

    # save image

    cpap_current_var = tk.StringVar()
    save_current = ttk.Button(root, text="Save current plot",
                              command=lambda: save_plot(
                                  cpap_plot_var_b64.get(),
                                  convert_date_string(cpap_current_var.get()),
                                  patient_mrn_var.get(), noname=False))
    save_current.grid(row=10, column=0, columnspan=2, pady=10)
    save_historic = ttk.Button(root, text="Save historic plot",
                               command=lambda: save_plot(
                                   cpap_plot_historic_var_b64.get(),
                                   dt_select_var.get(),
                                   patient_mrn_var.get(), noname=False))
    save_historic.grid(row=10, column=2, columnspan=2, pady=10)

    # cpap update

    update_cpap_label = ttk.Label(root, text="New CPAP Pressure (cmH\u2082O):")
    update_cpap_label.grid(row=11, column=0, padx=padding,
                           pady=padding)
    update_cpap_var = tk.StringVar()
    update_cpap = ttk.Entry(root, textvariable=update_cpap_var)
    update_cpap.grid(row=11, column=1, padx=padding, pady=padding)
    update_cpap_button = ttk.Button(
        root, text="Update CPAP", command=send_cpap)
    update_cpap_button.grid(row=11, column=2, columnspan=2, pady=10)

    root.after(1000, fetch_room_numbers)
    # root.after(1000, fetch_datetimes)
    room_select_var.trace_add("write", display_cpap_calculated_data)
    room_select_var.trace_add("write", reset)
    cpap_plot_var_b64.trace_add("write", plot_cpap)
    # patient_mrn_var.trace_add("write", fetch_datetimes)
    root.after(1000, fetch_datetimes)
    # may need to dynamicaly call fetch_dt
    dt_select_var.trace_add("write", plot_both)

    root.mainloop()


if __name__ == "__main__":
    INSTANCEURL = input('write your url\n')
    if len(INSTANCEURL) < 3:
        INSTANCEURL = "localhost:5001"
    main()
