# Running the Grocery Shop Web App

This guide explains how to set up and run the application both on the current system and on a brand-new system.

## 1. Running on This Same System

Since the required packages and `mongomock` (local mock database) have already been installed globally on this system, you don't need to reinstall anything or activate virtual environments.

### Steps:
1. Open your terminal (Command Prompt or PowerShell).
2. Navigate to the project directory:
   ```powershell
   cd "C:\Users\Dell\AppData\Local\Packages\5319275A.WhatsAppDesktop_cv1g1gvanyjgm\LocalState\sessions\D131D41AE32EFF379019CA95D8A58DCF8A7DEF0A\transfers\2026-22\-Nearest-Grocery-Shop-main\-Nearest-Grocery-Shop-main"
   ```
3. Run the application:
   ```powershell
   python app.py
   ```
4. Open your web browser and navigate to: `http://127.0.0.1:5000`

---

## 2. Running on a Different System

If you are setting this up on a new computer, you will need to install Python and the project dependencies before running the app. 

*(Note: The application is currently configured to use `mongomock` so it will run instantly without needing to whitelist IP addresses in MongoDB Atlas.)*

### Steps:
1. **Install Python**: Ensure Python 3.9+ is installed. During installation, make sure to check the box that says **"Add Python to PATH"**.
2. **Download the project**: Copy this entire project folder to the new system.
3. **Open Terminal**: Open Command Prompt or PowerShell and `cd` into the project directory where `app.py` is located.
4. **Install Dependencies**: Run the following command to install all the required Python libraries globally:
   ```powershell
   pip install -r requirements.txt
   ```
5. **Install Mongomock**: Because we modified the app to run without Atlas, you must also install `mongomock`:
   ```powershell
   pip install mongomock
   ```
6. **Start the Application**: 
   ```powershell
   python app.py
   ```
7. **Access the Web App**: Open a web browser and go to `http://127.0.0.1:5000`.

### Reverting to the Real MongoDB Database
If you eventually want to connect back to the real MongoDB Atlas database on the new system (after whitelisting the new system's IP address):
1. Open `app.py`.
2. Find the line (around line 68) that says `client = mongomock.MongoClient()`.
3. Delete or comment out that line.
4. Uncomment the line above it so it reads:
   `client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=50000)`
