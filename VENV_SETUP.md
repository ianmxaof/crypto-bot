# Virtual Environment Setup Guide

This guide will help you set up a Python virtual environment for the crypto trading bot project.

## Why Use a Virtual Environment?

- **Isolation**: Keeps project dependencies separate from system Python
- **Reproducibility**: Ensures consistent environment across different machines
- **Safety**: Prevents conflicts with other Python projects
- **Clean**: Easy to remove and recreate

## Quick Start

### Windows (PowerShell)

1. **Run the setup script:**
   ```powershell
   .\setup_venv.ps1
   ```

2. **Activate the environment:**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   
   Or use the helper:
   ```powershell
   .\activate.ps1
   ```

3. **Verify installation:**
   ```powershell
   python scripts/verify_env.py
   ```

### Linux / macOS

1. **Make script executable (first time only):**
   ```bash
   chmod +x setup_venv.sh
   chmod +x activate.sh
   ```

2. **Run the setup script:**
   ```bash
   ./setup_venv.sh
   ```

3. **Activate the environment:**
   ```bash
   source .venv/bin/activate
   ```
   
   Or use the helper:
   ```bash
   source activate.sh
   ```

4. **Verify installation:**
   ```bash
   python scripts/verify_env.py
   ```

## Manual Setup

If you prefer to set up manually:

### Step 1: Create Virtual Environment

**Windows:**
```powershell
python -m venv .venv
```

**Linux/Mac:**
```bash
python3 -m venv .venv
```

### Step 2: Activate Virtual Environment

**Windows PowerShell:**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows CMD:**
```cmd
.venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

### Step 3: Upgrade pip

```bash
python -m pip install --upgrade pip
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Verify Installation

```bash
python scripts/verify_env.py
```

## Verification

After activation, you should see:
- `(.venv)` prefix in your terminal prompt
- Python path points to `.venv` directory
- All required packages are importable

**Check if activated:**
```bash
python -c "import sys; print(sys.prefix)"
# Should show path containing .venv
```

**Check Python version:**
```bash
python --version
# Should show Python 3.9 or higher
```

## Common Issues

### Windows: Execution Policy Error

**Error:** `cannot be loaded because running scripts is disabled on this system`

**Solution:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try activating again.

### Python Not Found

**Error:** `python: command not found` or `'python' is not recognized`

**Solutions:**
1. Install Python from https://www.python.org/
2. Add Python to PATH during installation
3. Use `python3` instead of `python` on Linux/Mac
4. Verify installation: `python --version`

### Virtual Environment Already Exists

**Warning:** `Virtual environment already exists at .venv`

**Options:**
- Use existing environment (recommended)
- Recreate: Delete `.venv` folder and run setup again

### Package Installation Fails

**Error:** `Failed to install dependencies`

**Solutions:**
1. Upgrade pip: `python -m pip install --upgrade pip`
2. Install packages one by one to identify problematic package
3. Check Python version (3.9+ required)
4. On Windows, may need Visual C++ Build Tools for some packages

### Import Errors After Installation

**Error:** `ModuleNotFoundError: No module named 'X'`

**Solutions:**
1. Verify virtual environment is activated
2. Reinstall: `pip install -r requirements.txt --force-reinstall`
3. Check if package name is correct in requirements.txt

## Deactivating

When you're done working:

```bash
deactivate
```

This removes the `(.venv)` prefix and returns to system Python.

## Best Practices

1. **Always activate** the virtual environment before working on the project
2. **Commit `.venv` to git?** No! It's already in `.gitignore`
3. **Recreate if needed:** If environment gets corrupted, delete `.venv` and run setup again
4. **Keep requirements.txt updated:** After installing new packages, run:
   ```bash
   pip freeze > requirements.txt
   ```

## IDE Integration

### VS Code / Cursor

1. Open the project folder
2. VS Code/Cursor should detect `.venv` automatically
3. Select the Python interpreter: `Ctrl+Shift+P` → "Python: Select Interpreter"
4. Choose `.venv\Scripts\python.exe` (Windows) or `.venv/bin/python` (Linux/Mac)

### PyCharm

1. File → Settings → Project → Python Interpreter
2. Click gear icon → Add
3. Select "Existing environment"
4. Browse to `.venv\Scripts\python.exe` (Windows) or `.venv/bin/python` (Linux/Mac)

## Troubleshooting

### Check Virtual Environment Status

```bash
python scripts/verify_env.py
```

This will show:
- Whether venv is active
- Python version
- Installed packages
- Any missing dependencies

### Recreate Virtual Environment

If something goes wrong:

1. **Deactivate** (if active): `deactivate`
2. **Delete** `.venv` folder
3. **Run setup script again**: `.\setup_venv.ps1` or `./setup_venv.sh`

### Check Python Path

```bash
python -c "import sys; print(sys.executable)"
```

Should point to `.venv\Scripts\python.exe` (Windows) or `.venv/bin/python` (Linux/Mac)

## Next Steps

After setting up the virtual environment:

1. ✅ Verify installation: `python scripts/verify_env.py`
2. ✅ Run validation: `.\phase0_validation.ps1` (Windows) or `./phase0_validation.sh` (Linux/Mac)
3. ✅ Test imports: `python scripts/quick_test.py`
4. ✅ Start dashboard: `streamlit run dashboard/Home.py` (or `python run_dashboard.py`)

---

**Need Help?** Check the main README.md or open an issue on GitHub.

