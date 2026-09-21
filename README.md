# CFM301 Portfolio Analysis Project

This project analyzes stock data in `stocks.csv` and builds a mean-variance portfolio optimization workflow in `PROJ1-CFM301.ipynb`.

## Requirements

- Windows 10 or 11
- VS Code
- Python 3.10 or newer
- Git (optional, for version control)

## 1) Install VS Code and Python

1. Install Visual Studio Code from https://code.visualstudio.com/
2. Install Python from https://www.python.org/downloads/
3. In VS Code, install the following extensions:
   - Python
   - Jupyter

## 2) Open the project in VS Code

1. Open VS Code
2. Open the folder: `C:\Users\<your-user>\CFM301`
3. Open `PROJ1-CFM301.ipynb`

## 3) Create a virtual environment

Open a terminal in VS Code and run:

```powershell
cd "C:\Users\<your-user>\CFM301"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 4) Install required packages

```powershell
python -m pip install --upgrade pip
python -m pip install pandas numpy scipy matplotlib jupyter ipykernel
```

## 5) Select the Python interpreter in VS Code

1. Press `Ctrl+Shift+P`
2. Run: `Python: Select Interpreter`
3. Choose the interpreter from `.venv` in this project

## 6) Run the notebook

1. Open `PROJ1-CFM301.ipynb`
2. Run the cells from top to bottom
3. If prompted to install the notebook kernel, allow it

## 7) If a package is missing

Run this in the terminal inside the project:

```powershell
python -m pip install <package-name>
```

Common packages for this project:

- pandas
- numpy
- scipy
- matplotlib
- jupyter
- ipykernel

## 8) Troubleshooting

- If the notebook cannot find Python, select the correct interpreter again in VS Code
- If cells fail because of a missing package, install it with `python -m pip install ...`
- If plots do not display, ensure the notebook kernel is running and the Jupyter extension is installed

## Project files

- `PROJ1-CFM301.ipynb` — main notebook with the portfolio analysis
- `stocks.csv` — stock data used in the analysis

