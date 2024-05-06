# Cloud-Based CPAP Monitoring System Client/Server Final Project

## Team Members
- Kevin Xu (kevin.xu807@duke.edu)
- Jose Zarate (jose.zarate@duke.edu)

## Demo Video

https://youtu.be/D0GiXTYK_mw

## Description

This project is a cloud-based CPAP (Continuous Positive Airway Pressure) monitoring system that allows healthcare providers to remotely monitor and manage CPAP therapy for patients. The system consists of a patient-side GUI client (patient_gui.py), a monitoring station GUI (monitor_gui.py), and a server component (server.py) that handles data storage and communication between the GUIs.

## Database Structure

A SQL Server Database hosted by Google Cloud is used. Two tables were created in the following fashion:

```bash
CREATE TABLE entries (
  mrn INT,
  datetime DATETIME,
  name VARCHAR(30),
  currcpap DECIMAL(5, 2),
  br DECIMAL(5,2),
  apnea INT,
  plot VARCHAR(MAX),
  room_number INT
)
```

This table records every entry ever uploaded, including duplicate entries for a single patient.

```bash
CREATE TABLE now (
  room_number INT PRIMARY KEY,
  mrn INT,
  name VARCHAR(30)
  datetime DATETIME,
  currcpap DECIMAL(5,2),
  br DECIMAL(5, 2),
  apnea INT,
  plot VARCHAR(MAX)
)
```

This table contains the information of each patient in every occupied room.

## Key Features

* Patient-side GUI for uploading CPAP data and viewing analysis results
* Monitoring station GUI for real-time monitoring of patient CPAP data
* Server component for data storage and communication between GUIs
* Calculation of breathing rate, apnea events, and leakage from CPAP data
* Plotting of flow rate vs. time for visual analysis
* Updating and retrieving CPAP pressure settings
* Robust validation of GUI entry fields with detailed messageboxes and dialog boxes (patient_gui.py)
* Use of peak detection algorithm from a previous assignment to obtain CPAP calculated data

## Requirements

Python 3.7 or higher
Google Cloud SQL instance
Required Python packages (listed in requirements.txt)

## Setup

1. Clone the repository:

```bash
git clone git@github.com:BME547-Spring2024/final-project-jose_kevin.git
```

2. Set up a virtual environment (optional but recommended):

```bash
python3 -m venv my_venv
source my_venv/bin/activate  # For Linux/Mac
my_venv\Scripts\activate.bat  # For Windows
```

3. Install the required packages:

```bash
python3 config.py
```

```bash
pip3 install -r requirements.txt
```

4. Add the service key

Let ```service-key.json``` store the service key

For macOS

```bash
export GOOGLE_APPLICATION_CREDENTIALS="service-key.json"
```

For Windows
```bash
$env:GOOGLE_APPLICATION_CREDENTIALS="service-key.json"
```

## Usage

1. Start the server:

```bash
python3 server.py
```

2. Run the patient-side GUI:

```bash
python3 patient_gui.py
```

Before the gui displays, you will be prompted to enter the address of the server to connect to. If you are using localhost, type 0. Type vcm-39569.vm.duke.edu:5001 to connect to the server on the virtual machine currently active. You are able to add as many patient-side GUIs as you wish.

3. Run the monitoring station GUI:
```bash
python3 monitor_gui.py
```

Before the gui displays, you will be prompted to enter the address of the server to connect to. If you are using localhost, type 0. Type vcm-39569.vm.duke.edu:5001 to connect to the server on the virtual machine currently active. You are able to add as many monitoring station GUIs as you wish.

4. Use the patient-side GUI to upload CPAP data and view analysis results.

5. Use the monitoring station GUI to monitor patient CPAP data in real-time, update CPAP pressure settings, and view historical data.

## VM Access

A working server is currently deployed on a virtual machine. When starting both GUIs, type the address below under the prompt in the terminal.

vcm-39569.vm.duke.edu:5001

## Software License

MIT License

Copyright (c) [2024] [Kevin Xu] [Jose Zarate]

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.