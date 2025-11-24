# ChatWithYourData – Text2SQL Projekt 📌

## Übersicht

Dieses Projekt wurde im Rahmen des Moduls "Projekt" an der DHBW Stuttgart entwickelt. Ziel ist es, eine Anwendung zu erstellen, die es Nutzer:innen ermöglicht, natürliche Sprache zu verwenden, um SQL-Abfragen automatisch zu generieren und eine Datenbank abzufragen. Dazu wird ein Large Language Model (LLM) eingebunden, das Text → SQL übersetzt.

Das Projekt basiert auf dem Benchmark-Datensatz **BIRD-INTERACT (mini-interact)**. Die Hauptaufgabe besteht darin, die bereitgestellten Fragen korrekt zu beantworten, indem die Anwendung dynamisch SQL-Abfragen erzeugt und ausführt.

## 🎯 Projektziele

- Entwicklung eines funktionierenden Text2SQL-Prototyps
- Nutzung moderner LLM-Technologien zur automatischen SQL-Generierung
- Erstellung einer Architektur, die Frontend, Backend, LLM und Datenbank verbindet
- Umsetzung der im Modul geforderten Methoden des Software Engineerings, Projektmanagements und Teamarbeit

## 🧠 Motivation

Daten sind das Gold des 21. Jahrhunderts – jedoch ist SQL für viele Mitarbeitende eine Hürde. Moderne KI-Modelle ermöglichen es, natürliche Sprache effizient zu interpretieren.

Mit diesem Projekt helfen wir Unternehmen dabei, **data-driven** zu werden, indem wir die Distanz zwischen Mensch und Datenbank reduzieren.

## 🛠️ Technologie-Stack

### Backend

- **Node.js / Express**
- Anbindung eines LLM (z. B. GPT-4.1, GPT-4o-mini, o3-mini, Claude 3.5 Sonnet)
- **SQLite** für den mini-interact Datensatz
- SQL Execution Layer

### Frontend

- Einfaches Chat-Interface (z. B. **React**)
- Anfrage → Backend → Antwortfluss

### Weitere Tools

- **GitHub** (Versionierung, Projektmanagement)
- ggf. **n8n** für explorative Low-Code-Prototypen
