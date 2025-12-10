# 📌 Event Scheduling & Resource Allocation System

A professional web application to schedule events (seminars, workshops, training sessions) and allocate shared resources like rooms, instructors, and equipment.  
The system automatically detects double booking conflicts and generates a resource utilisation report based on selected date ranges.

---

## 🚀 Features

### 🗓 Event Management
- Create, edit, view, and manage events
- Add event time, description, and required resources

### 🧩 Resource Management
- Add rooms, instructors, equipment
- Edit and manage allocation types

### 🔗 Smart Resource Allocation
- Assign multiple resources to a single event

### ⚠ Conflict Detection
- Detects clashes when the same resource is booked for overlapping time slots

### 📊 Utilisation Reports
- Displays total hours a resource is used
- Lists upcoming bookings within a selected date range

### 🎨 Modern UI
- Dashboard-style home page
- Bootstrap themed pages (Events, Resources, Conflicts, Reports)

---

## 🛠 Tech Stack

| Component | Technology |
|----------|------------|
| Language | Python |
| Framework | Flask |
| ORM | SQLAlchemy |
| Database | SQLite |
| Frontend | HTML, CSS, Bootstrap |
| Template Engine | Jinja2 |

---

## 🧠 Logic Used

### 🔹 Conflict Detection Logic

new_start < existing_end AND new_end > existing_start

### 📊 Resource Utilisation Logic
Total Hours = (min(event_end, selected_range_end) - max(event_start, selected_range_start))

## 📂 Project Structure

```text
event-scheduling-system/
│ app.py
│ requirements.txt
│ README.md
│
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── events.html
│   ├── resources.html
│   ├── conflicts.html
│   └── report.html
│
├── static/
└── screenshots/
    ├── home.png
    ├── events.png
    ├── resources.png
    ├── conflicts.png
    └── report.png



### 💻 How to Run
###  1️⃣ Install dependencies
pip install -r requirements.txt

###  2️⃣ Run the application
python app.py

###  3️⃣ Open in browser
http://127.0.0.1:5000/




