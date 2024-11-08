import os
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import ImageGrab, Image, ImageEnhance, ImageOps
import pytesseract
import re
import pyperclip
import platform
import webbrowser

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
tesseract_download_url = "https://github.com/UB-Mannheim/tesseract/wiki"

info = {}
last_reports = []
last_speeds = []
last_locations = []
last_directions = []
recent_location_direction = {}

def check_tesseract_installed():
    try:
        pytesseract.get_tesseract_version()
        return True
    except pytesseract.TesseractNotFoundError:
        return False


def install_tesseract():
    if platform.system() == "Windows":
        messagebox.showinfo("Tesseract Installation",
                            "Tesseract-OCR wurde nicht gefunden. Sie werden zur Download-Seite weitergeleitet.")
        webbrowser.open(tesseract_download_url)
        messagebox.showinfo("Hinweis", "Bitte installieren Sie Tesseract-OCR und starten Sie das Programm danach neu.")


def preprocess_image(image):
    image = image.convert("L")
    image = ImageOps.invert(image)
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)
    image = image.point(lambda x: 0 if x < 150 else 255, '1')
    return image


def extract_text_from_clipboard_image():
    image = ImageGrab.grabclipboard()
    if isinstance(image, Image.Image):
        image = preprocess_image(image)
        text = pytesseract.image_to_string(image, lang="deu")
        return text
    else:
        return None


def parse_information(text):
    speed = re.search(r"(?i)geschwindigkeit[:\s]*([0-9]+)", text)
    license_plate = re.search(r"(?i)kennzeichen[:\s]*([A-Z0-9-]+)", text)
    return {
        "Geschwindigkeit": int(speed.group(1)) if speed else None,
        "Kennzeichen": license_plate.group(1) if license_plate else None,
    }


def calculate_exceedance(measured_speed, allowed_speed, tolerance=10):
    measured_speed = measured_speed if measured_speed is not None else 0
    exceedance = max(0, measured_speed - allowed_speed - tolerance)
    return exceedance


def generate_report(info, allowed_speed, vehicle_type, location, direction, evidence_image, officer="E. Möhre"):
    geschwindigkeit = info.get("Geschwindigkeit", 0)
    kennzeichen = info.get("Kennzeichen", "Unbekannt")
    exceedance = calculate_exceedance(geschwindigkeit, int(allowed_speed))

    report = (f"- Ort: {location}\n"
              f"- Fahrtrichtung: {direction}\n"
              f"- Fahrzeugtyp: {vehicle_type}\n"
              f"- Kennzeichen: {kennzeichen}\n"
              f"- Gemessene Geschwindigkeit: {geschwindigkeit} km/h\n"
              f"- Erlaubte Geschwindigkeit: {allowed_speed} km/h\n"
              f"- Geschwindigkeitsüberschreitung (nach Abzug der Toleranz von 10 km/h): {exceedance} km/h\n"
              f"- Messender Beamter: {officer}\n"
              f"- Beweisbildnummer: {evidence_image}")
    return report


def copy_text_to_clipboard(text):
    pyperclip.copy(text)
    messagebox.showinfo("Erfolg", "Bericht wurde in die Zwischenablage kopiert.")

# Aktualisieren der Fahrtrichtung basierend auf dem gewählten Ort
def update_direction_from_location(event):
    selected_location = location_dropdown.get()
    if selected_location in recent_location_direction:
        # Setzt die zuletzt verwendete Richtung für den ausgewählten Ort
        direction_dropdown.set(recent_location_direction[selected_location])

def on_submit():
    allowed_speed = int(entry_allowed_speed.get())
    vehicle_type = entry_vehicle_type.get()
    location = entry_location.get()
    direction = entry_direction.get()
    evidence_image = entry_evidence_image.get()

    recent_location_direction[location] = direction

    gemessene_geschwindigkeit = int(entry_speed.get()) if entry_speed.get() else 0
    kennzeichen = entry_license_plate.get() if entry_license_plate.get() else "Unbekannt"
    info = {"Geschwindigkeit": gemessene_geschwindigkeit, "Kennzeichen": kennzeichen}

    report = generate_report(info, allowed_speed, vehicle_type, location, direction, evidence_image)
    copy_text_to_clipboard(report)

    # Aktualisiere die Beweisbildnummer um +1
    if evidence_image.isdigit():
        entry_evidence_image.delete(0, tk.END)
        entry_evidence_image.insert(0, str(int(evidence_image) + 1))

    # Lösche das Kennzeichen- und Geschwindigkeitsfeld
    entry_speed.delete(0, tk.END)
    entry_license_plate.delete(0, tk.END)

    # Bericht zum Archiv hinzufügen
    if len(last_reports) >= 5:
        last_reports.pop(0)
    last_reports.append(report)

    # Update the last 3 entries
    update_recent_entries(allowed_speed, location, direction)
    update_archive_list()


def update_recent_entries(speed, location, direction):
    # Ensure last entries are unique and only hold the last three
    def update_list(lst, value):
        if value not in lst:
            lst.append(value)
            if len(lst) > 3:
                lst.pop(0)

    update_list(last_locations, location)
    update_list(last_directions, direction)

    # Update dropdowns
    location_dropdown['values'] = last_locations
    direction_dropdown['values'] = last_directions


def update_archive_list():
    archive_listbox.delete(0, tk.END)
    for report in last_reports:
        kennzeichen = report.split("\n")[3]
        archive_listbox.insert(tk.END, kennzeichen.split(": ")[1])


def check_image():
    text = extract_text_from_clipboard_image()
    global info
    if text:
        info = parse_information(text)
        if info["Geschwindigkeit"] or info["Kennzeichen"]:
            status_label.config(text="Informationen aus dem Bild erkannt!", fg="green")
            entry_speed.delete(0, tk.END)
            entry_speed.insert(0, info["Geschwindigkeit"] if info["Geschwindigkeit"] else "")
            entry_license_plate.delete(0, tk.END)
            entry_license_plate.insert(0, info["Kennzeichen"] if info["Kennzeichen"] else "")
        else:
            status_label.config(text="Keine gültigen Informationen im Bild gefunden.", fg="orange")
    else:
        status_label.config(text="Kein Bild in der Zwischenablage gefunden!", fg="red")



def show_full_report(event):
    selected_index = archive_listbox.curselection()
    if selected_index:
        report = last_reports[selected_index[0]]
        messagebox.showinfo("Vollständiger Bericht", report)


root = tk.Tk()
root.title("Verkehrsberichtsgenerator")
root.geometry("600x570")
root.configure(bg="#f0f0f0")

header_label = tk.Label(root, text="Verkehrsberichtsgenerator", font=("Helvetica", 18, "bold"), bg="#f0f0f0", fg="#333")
header_label.pack(pady=10)

status_label = tk.Label(root, text="", font=("Arial", 10), bg="#f0f0f0")
status_label.pack()

frame = tk.Frame(root, bg="#f0f0f0", padx=20, pady=10)
frame.pack()

# Dropdowns for recent entries
tk.Label(frame, text="Erlaubte Geschwindigkeit (km/h):", bg="#f5f5f5").grid(row=0, column=0, sticky="w")
entry_allowed_speed = tk.Entry(frame, width=30)
entry_allowed_speed.grid(row=0, column=1, pady=5)

tk.Label(frame, text="Ort:", bg="#f0f0f0").grid(row=2, column=0, sticky="w")
location_dropdown = ttk.Combobox(frame, values=last_locations, width=28)
location_dropdown.grid(row=2, column=1, pady=5)
entry_location = location_dropdown

# Binden Sie die Funktion an das Dropdown-Menü für den Ort
location_dropdown.bind("<<ComboboxSelected>>", update_direction_from_location)

tk.Label(frame, text="Fahrtrichtung:", bg="#f0f0f0").grid(row=3, column=0, sticky="w")
direction_dropdown = ttk.Combobox(frame, values=last_directions, width=28)
direction_dropdown.grid(row=3, column=1, pady=5)
entry_direction = direction_dropdown

tk.Label(frame, text="Fahrzeugtyp:", bg="#f0f0f0").grid(row=1, column=0, sticky="w")
entry_vehicle_type = tk.Entry(frame, width=30)
entry_vehicle_type.grid(row=1, column=1, pady=5)

tk.Label(frame, text="Beweisbildnummer:", bg="#f0f0f0").grid(row=4, column=0, sticky="w")
entry_evidence_image = tk.Entry(frame, width=30)
entry_evidence_image.grid(row=4, column=1, pady=5)

tk.Label(frame, text="Gemessene Geschwindigkeit (falls nicht erkannt):", bg="#f0f0f0").grid(row=5, column=0, sticky="w")
entry_speed = tk.Entry(frame, width=30)
entry_speed.grid(row=5, column=1, pady=5)

tk.Label(frame, text="Kennzeichen (falls nicht erkannt):", bg="#f0f0f0").grid(row=6, column=0, sticky="w")
entry_license_plate = tk.Entry(frame, width=30)
entry_license_plate.grid(row=6, column=1, pady=5)

case_frame = tk.Frame(root, bg="#f0f0f0", padx=20, pady=10)
case_frame.pack()


# Stil für abgerundete Buttons definieren
style = ttk.Style()
style.configure("Rounded.TButton", font=("Arial", 10, "bold"), padding=10, relief="flat", borderwidth=1)
style.map("Rounded.TButton",
          background=[("active", "#0055AA"), ("!disabled", "#4CAF50")],
          foreground=[("!disabled", "black")])

# Frame für die Buttons nebeneinander
button_frame = tk.Frame(root, bg="#f0f0f0")
button_frame.pack(pady=10)

# Button für "Bild prüfen" mit abgerundetem Stil
check_button = ttk.Button(button_frame, text="Prüfen", command=check_image, style="Rounded.TButton")
check_button.pack(side="left", padx=5, pady=5)

# Button für "Bericht generieren" mit abgerundetem Stil
submit_button = ttk.Button(button_frame, text="Bericht", command=on_submit, style="Rounded.TButton")
submit_button.pack(side="left", padx=5, pady=5)


# Archiv der letzten 5 Berichte
archive_frame = tk.Frame(root, bg="#f0f0f0", padx=20, pady=10)
archive_frame.pack()

tk.Label(archive_frame, text="Letzte Abfragen:", bg="#f0f0f0", font=("Arial", 12, "bold")).pack(anchor="w")
archive_listbox = tk.Listbox(archive_frame, height=5, width=60, bg="#e8e8e8")
archive_listbox.pack(pady=5)

# Binde eine Doppelklickaktion, um den vollständigen Bericht anzuzeigen
archive_listbox.bind("<Double-1>", show_full_report)

# Progress-Bar für Animation


root.mainloop()
