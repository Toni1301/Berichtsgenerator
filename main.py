import os
import subprocess
import tkinter as tk
from tkinter import messagebox
from PIL import ImageGrab, Image, ImageEnhance, ImageOps
import pytesseract
import re
import pyperclip
import platform
import webbrowser

# Setze den Tesseract-Pfad und das Verzeichnis für tessdata
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# URL für die Tesseract-Download-Seite
tesseract_download_url = "https://github.com/UB-Mannheim/tesseract/wiki"

# Initialisierung der globalen Variablen
info = {}


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
    else:
        messagebox.showinfo("Info", f"Bitte installieren Sie Tesseract manuell über die Website: {tesseract_download_url}")

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
        print("Bild erfolgreich aus der Zwischenablage abgerufen")  # Debugging-Ausgabe
        image = preprocess_image(image)
        text = pytesseract.image_to_string(image, lang="deu")
        print("Erkannter Text:", text)  # Debugging-Ausgabe
        return text
    else:
        print("Kein Bild in der Zwischenablage gefunden")
        return None

def parse_information(text):
    speed = re.search(r"(?i)geschwindigkeit[:\s]*([0-9]+)", text)
    license_plate = re.search(r"(?i)kennzeichen[:\s]*([A-Z0-9-]+)", text)
    return {
        "Geschwindigkeit": int(speed.group(1)) if speed else None,
        "Kennzeichen": license_plate.group(1) if license_plate else None,
    }

def calculate_exceedance(measured_speed, allowed_speed, tolerance=10):
    # Sicherstellen, dass measured_speed einen numerischen Wert hat
    measured_speed = measured_speed if measured_speed is not None else 0
    exceedance = max(0, measured_speed - allowed_speed - tolerance)
    return exceedance


def generate_report(info, allowed_speed, vehicle_type, location, direction, evidence_image, officer="E. Möhre"):
    # Überprüfen, ob 'Geschwindigkeit' und 'Kennzeichen' vorhanden sind
    geschwindigkeit = info.get("Geschwindigkeit", 0)  # Standardwert 0, falls nicht vorhanden
    kennzeichen = info.get("Kennzeichen", "Unbekannt")  # Standardwert "Unbekannt", falls nicht vorhanden

    exceedance = calculate_exceedance(geschwindigkeit, int(allowed_speed))
    geschwindigkeits_info = f"{geschwindigkeit} km/h" if geschwindigkeit > 0 else "Nicht erkannt"
    kennzeichen_info = kennzeichen if kennzeichen != "Unbekannt" else "Nicht erkannt"

    report = (f"- Ort: {location}\n"
              f"- Fahrtrichtung: {direction}\n"
              f"- Fahrzeugtyp: {vehicle_type}\n"
              f"- Kennzeichen: {kennzeichen_info}\n"
              f"- Gemessene Geschwindigkeit: {geschwindigkeits_info}\n"
              f"- Erlaubte Geschwindigkeit: {allowed_speed} km/h\n"
              f"- Geschwindigkeitsüberschreitung (nach Abzug der Toleranz von 10 km/h): {exceedance} km/h\n"
              f"- Messender Beamter: {officer}\n"
              f"- Beweisbildnummer: {evidence_image}")
    return report


def copy_text_to_clipboard(text):
    pyperclip.copy(text)
    messagebox.showinfo("Erfolg", "Bericht wurde in die Zwischenablage kopiert.")


def on_submit():
    allowed_speed = int(entry_allowed_speed.get())
    vehicle_type = entry_vehicle_type.get()
    location = entry_location.get()
    direction = entry_direction.get()
    evidence_image = entry_evidence_image.get()

    # Manuelle Eingabewerte direkt übernehmen
    try:
        gemessene_geschwindigkeit = int(entry_speed.get()) if entry_speed.get() else 0
        kennzeichen = entry_license_plate.get() if entry_license_plate.get() else "Unbekannt"
    except ValueError:
        gemessene_geschwindigkeit = 0  # Standardwert, falls die Eingabe ungültig ist
        kennzeichen = "Unbekannt"

    # info-Objekt zur Verwendung in generate_report initialisieren
    info = {"Geschwindigkeit": gemessene_geschwindigkeit, "Kennzeichen": kennzeichen}

    report = generate_report(info, allowed_speed, vehicle_type, location, direction, evidence_image)
    copy_text_to_clipboard(report)


def check_image():
    print("Bild prüfen wurde gestartet")  # Debugging-Ausgabe
    text = extract_text_from_clipboard_image()
    global info
    if text:
        info = parse_information(text)
        if info["Geschwindigkeit"] or info["Kennzeichen"]:
            status_label.config(text="Informationen aus dem Bild erkannt!", fg="green")
            # Automatisches Einfügen der erkannten Werte
            entry_speed.delete(0, tk.END)
            entry_speed.insert(0, info["Geschwindigkeit"] if info["Geschwindigkeit"] else "")
            entry_license_plate.delete(0, tk.END)
            entry_license_plate.insert(0, info["Kennzeichen"] if info["Kennzeichen"] else "")
        else:
            status_label.config(text="Keine gültigen Informationen im Bild gefunden.", fg="orange")
    else:
        status_label.config(text="Kein Bild in der Zwischenablage gefunden!", fg="red")

def select_case(case):
    if case == 1:
        entry_allowed_speed.delete(0, tk.END)
        entry_allowed_speed.insert(0, "60")
    elif case == 3:
        entry_allowed_speed.delete(0, tk.END)
        entry_allowed_speed.insert(0, "120")
    elif case == 4:
        entry_allowed_speed.delete(0, tk.END)
        entry_allowed_speed.insert(0, "180")

# GUI-Fenster erstellen
root = tk.Tk()
root.title("Verkehrsberichtsgenerator")
root.geometry("500x600")
root.configure(bg="#f5f5f5")

# Icon für das Fenster festlegen
root.iconbitmap("logo.ico")

# Überprüfen, ob Tesseract installiert ist
if not check_tesseract_installed():
    install_tesseract()

# Überschrift
header_label = tk.Label(root, text="Verkehrsberichtsgenerator", font=("Arial", 16, "bold"), bg="#f5f5f5", fg="#333")
header_label.pack(pady=10)

# Statusanzeige für Texterkennung
status_label = tk.Label(root, text="", font=("Arial", 10), bg="#f5f5f5")
status_label.pack()

# Frame für Eingabefelder
frame = tk.Frame(root, bg="#f5f5f5", padx=20, pady=10)
frame.pack()

# Eingabefelder für GUI
tk.Label(frame, text="Erlaubte Geschwindigkeit (km/h):", bg="#f5f5f5").grid(row=0, column=0, sticky="w")
entry_allowed_speed = tk.Entry(frame, width=30)
entry_allowed_speed.grid(row=0, column=1, pady=5)

tk.Label(frame, text="Fahrzeugtyp:", bg="#f5f5f5").grid(row=1, column=0, sticky="w")
entry_vehicle_type = tk.Entry(frame, width=30)
entry_vehicle_type.grid(row=1, column=1, pady=5)

tk.Label(frame, text="Ort:", bg="#f5f5f5").grid(row=2, column=0, sticky="w")
entry_location = tk.Entry(frame, width=30)
entry_location.grid(row=2, column=1, pady=5)

tk.Label(frame, text="Fahrtrichtung:", bg="#f5f5f5").grid(row=3, column=0, sticky="w")
entry_direction = tk.Entry(frame, width=30)
entry_direction.grid(row=3, column=1, pady=5)

tk.Label(frame, text="Beweisbildnummer:", bg="#f5f5f5").grid(row=4, column=0, sticky="w")
entry_evidence_image = tk.Entry(frame, width=30)
entry_evidence_image.grid(row=4, column=1, pady=5)

tk.Label(frame, text="Gemessene Geschwindigkeit (falls nicht erkannt):", bg="#f5f5f5").grid(row=5, column=0, sticky="w")
entry_speed = tk.Entry(frame, width=30)
entry_speed.grid(row=5, column=1, pady=5)

tk.Label(frame, text="Kennzeichen (falls nicht erkannt):", bg="#f5f5f5").grid(row=6, column=0, sticky="w")
entry_license_plate = tk.Entry(frame, width=30)
entry_license_plate.grid(row=6, column=1, pady=5)

# Fallauswahlknöpfe
case_frame = tk.Frame(root, bg="#f5f5f5", padx=20, pady=10)
case_frame.pack()

tk.Label(case_frame, text="Wähle einen Fall aus:", bg="#f5f5f5", font=("Arial", 12)).grid(row=0, columnspan=2)

button_case_1 = tk.Button(case_frame, text="Option 1: 60 km/h (Fraktions-HQ, Innerorts)", command=lambda: select_case(1))
button_case_1.grid(row=1, column=0, padx=10, pady=5)

button_case_3 = tk.Button(case_frame, text="Option 2: 120 km/h (Außerorts)", command=lambda: select_case(3))
button_case_3.grid(row=2, column=0, padx=10, pady=5)

button_case_4 = tk.Button(case_frame, text="Option 3: 180 km/h (Straßen mit zwei oder mehr Fahrstreifen)", command=lambda: select_case(4))
button_case_4.grid(row=3, column=0, padx=10, pady=5)

# Button zum Prüfen und automatisch Ausfüllen
check_button = tk.Button(root, text="Bild prüfen", command=check_image, bg="#4CAF50", fg="white", font=("Arial", 10))
check_button.pack(pady=10)

# Button zum Absenden
submit_button = tk.Button(root, text="Bericht generieren", command=on_submit, bg="#2196F3", fg="white", font=("Arial", 10))
submit_button.pack(pady=10)

# GUI starten
root.mainloop()
