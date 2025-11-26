## 2. README_DE.md (Deutsch - ROOT-Verzeichnis)
```markdown
# Silverline Hood Integration für Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license]
[![hacs][hacsbadge]][hacs]
[![Community Forum][forum-shield]][forum]

**Diese Integration ermöglicht die Steuerung Ihrer Silverline Dunstabzugshaube über Home Assistant.**

[🇺🇸 English Version](README.md)

## Features

- 🌀 **Lüfter-Steuerung**: 4 Geschwindigkeitsstufen (Aus, Niedrig, Mittel, Hoch, Maximum)
- 💡 **RGBW-Beleuchtung**: Vollständige Farb- und Helligkeitssteuerung
- 🔄 **Bidirektionale Synchronisation**: Automatische Erkennung von Änderungen über die Fernbedienung
- ⚙️ **Konfigurierbares Abfrageintervall**: 5-300 Sekunden über die Home Assistant UI
- 🌐 **Telnet-Kommunikation**: Zuverlässige Verbindung über das lokale Netzwerk

## Installation

### HACS (empfohlen)

1. Öffnen Sie HACS in Home Assistant
2. Klicken Sie auf "Integrationen"
3. Klicken Sie auf die drei Punkte oben rechts und wählen Sie "Benutzerdefinierte Repositories"
4. Fügen Sie `https://github.com/bogenrs/silverline_hood` als Repository hinzu
5. Wählen Sie "Integration" als Kategorie
6. Suchen Sie nach "Silverline Hood" und installieren Sie es
7. Starten Sie Home Assistant neu

### Manuelle Installation

1. Laden Sie die neueste Version herunter
2. Extrahieren Sie den Inhalt nach `custom_components/silverline_hood/`
3. Starten Sie Home Assistant neu

## Konfiguration

1. Gehen Sie zu **Einstellungen** → **Geräte & Dienste**
2. Klicken Sie auf **Integration hinzufügen**
3. Suchen Sie nach "Silverline Hood"
4. Geben Sie die IP-Adresse Ihrer Dunstabzugshaube ein
5. Geben Sie den Port ein (Standard: 23)

### Optionen konfigurieren

Nach der Installation können Sie zusätzliche Optionen konfigurieren:

1. Gehen Sie zu **Einstellungen** → **Geräte & Dienste**
2. Finden Sie "Silverline Hood" und klicken Sie auf **Konfigurieren**
3. Stellen Sie das gewünschte Abfrageintervall ein (5-300 Sekunden)

## JSON-Befehlsstruktur

Die Integration verwendet folgende JSON-Struktur für die Kommunikation:

```json
{
    "M": 2,      // Motor: 0=Aus, 1-4=Geschwindigkeitsstufen
    "L": 1,      // Licht: 0=Aus, 1=An
    "R": 255,    // Rot (0-255)
    "G": 7,      // Grün (0-255)
    "B": 209,    // Blau (0-255)
    "CW": 255,   // Kaltweiß (0-255)
    "BRG": 163,  // Helligkeit (0-255)
    "T": 0,      // Unbekannt
    "TM": 0,     // Unbekannt
    "TS": 255,   // Unbekannt
    "A": 1       // Status-Abfrage mit {"A": 4}
}