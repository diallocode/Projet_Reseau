# AI Battle Simulator

A fully programmable real-time strategy (RTS) battle simulator inspired by Age of Empires II, designed to experiment with AI-controlled generals, tactical decision-making, and large-scale automated battle analysis.

This project focuses on AI behavior, combat mechanics, and experimental evaluation rather than game design or graphical polish.

---

## 🎯 Overview

The simulator models medieval-style battles between two opposing armies composed of units such as Knights, Pikemen, and Crossbowmen.  
Each army is commanded by a general implementing a specific AI strategy, which fully controls unit movement, target selection, formations, and engagements.

The system is designed as an experimental platform to compare AI behaviors under controlled scenarios.

---

## 🛠 Requirements

- Python 3.12
- Pygame
- matplotlib

---

## 🚀 How to Run

Make sure you are in the `src` directory and use one of the following commands:

### Run a single battle
```bash
python3 Main.py run <AI1> <AI2> [-t] [-d DATAFILE] [-p]
python3 Main.py run Smart Daft -p

```

### Load a saved battle
```bash
python3 Main.py load <SAVEFILE> --gui
python3 Main.py load save/quick_save.json --gui

```

### Run a tournament
```bash
python3 Main.py tourney [-G AI1 AI2 ...] [-S SCENARIO1 SCENARIO2 ...] [-N=10] [-na]
python3 Main.py tourney -G Daft Smart -S 1 2 6  -N 3 -na

```

### Run a programmable scenario and plot results
```bash
python3 Main.py plot <AI> <PLOTTER> <SCENARIO> "[UnitType,...]" "<RangeExpression>" [-N ROUNDS]
python3 Main.py plot Daft PlotLanchester Lanchester "[Knight, Pikeman]" "range(1,100)"

```
