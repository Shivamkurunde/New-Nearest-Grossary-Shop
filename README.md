# Nearest Grocery Shop

A comprehensive Flask-based web application for managing local Kirana (grocery) stores, allowing customers to easily find nearby shops, place orders, and even upload custom shopping lists (via Image OCR, PDF, CSV, Excel, or TXT). It also provides an owner dashboard for store owners to manage their shop status and orders.

---

## 📂 Project Structure & File Use Cases

This section provides a detailed breakdown of all the files and directories in this project, explaining their purpose, how they are used, and where they fit into the application's architecture.

### 1. Root Directory Files

*   **`app.py`**
    *   **Purpose:** The central entry point of the Flask application.
    *   **Use Case:** Initializes the Flask app, configures MongoDB connections, handles user authentication (login/register), profile management, shopping logic (home, items, shops), and processes file uploads for grocery lists using OCR and file parsing. It also contains the owner dashboard logic.
*   **`config.py`**
    *   **Purpose:** Application configuration file.
    *   **Use Case:** Stores environment variables and configurations such as database URIs (MongoDB and SQLite) and the Flask secret key. It is used to keep sensitive information and settings separate from the main application code.
*   **`requirements.txt`**
    *   **Purpose:** Dependency management.
    *   **Use Case:** Lists all the required Python packages (e.g., Flask, pymongo, werkzeug, pdfplumber, openpyxl, etc.) needed to run the application. Used during setup via `pip install -r requirements.txt`.
*   **`.env`**
    *   **Purpose:** Environment variables file.
    *   **Use Case:** Securely stores secrets like `MONGO_URI` and `GEMINI_API_KEY` (for OCR). Loaded by `app.py` at runtime.
*   **`.gitignore`**
    *   **Purpose:** Git version control configuration.
    *   **Use Case:** Specifies intentionally untracked files (like virtual environments `__pycache__`, local `.env` files) that Git should ignore.
*   **`README.md`**
    *   **Purpose:** Project documentation.
    *   **Use Case:** Provides an overview of the project, file structure, and setup instructions. (This is the file you are currently reading!)

### 2. Testing & Verification Scripts

*   **`test_place_order.py`**
    *   **Purpose:** API testing script for the order placement feature.
    *   **Use Case:** An automated script that tests the `/api/place_order` endpoint. It verifies empty cart guards, successful order placements, database saves, notifications, and updates to the "My Orders" and "Track Order" pages.
*   **`test_upload.py`**
    *   **Purpose:** End-to-End (E2E) testing script for the shopping list upload feature.
    *   **Use Case:** Generates mock files (PNG, JPG, PDF, CSV, Excel, TXT) and tests the `/api/upload_grocery_list` route to ensure the app correctly parses different formats, extracts items, creates orders, and triggers notifications.
*   **`verify.py`**
    *   **Purpose:** Full project environment verification.
    *   **Use Case:** Run before starting the app to ensure MongoDB Atlas is reachable, Tesseract OCR (if applicable) is installed, Flask routes are correctly registered, and there are no import errors.

### 3. Application Directories

#### `routes/`
Contains Flask Blueprints to modularize the application routing, keeping `app.py` from becoming too monolithic.
*   **`product_routes.py`**: Handles API endpoints and views related to product catalogs, searching, and filtering.
*   **`shop_routes.py`**: Manages shop-specific logic, such as retrieving shops by location or distance, and shop owner functionalities.
*   **`user_routes.py`**: Manages user-specific logic separate from the main app, handling operations related to user data.

#### `utils/`
Contains helper modules and utility functions.
*   **`db_connection.py`**: A dedicated utility to establish and share the MongoDB connection client across different routes and modules, ensuring efficient database connection pooling.

#### `templates/`
Contains all the Jinja2 HTML templates used to render the frontend of the web application.
*   **`index.html`**: The landing/home page of the application.
*   **`header.html` & `footer.html`**: Reusable navigation and footer components included in other pages.
*   **`login.html` & `register.html`**: Authentication pages for customers and owners.
*   **`profile.html`**: Allows users to update their personal and delivery details.
*   **`location.html` & `shops.html` & `all_shops.html`**: Pages for users to select their area and view available local Kirana shops.
*   **`items.html` & `products.html`**: Displays the product catalog for a selected shop.
*   **`my_orders.html` & `track_order.html`**: Customer-facing pages to view order history and current order status.
*   **`owner_dashboard.html`**: The dedicated portal for shop owners to view incoming orders and toggle their shop's Open/Closed status.

#### `static/`
Contains all static assets served directly to the client's browser.
*   **`css/`**: Cascading Style Sheets for styling the application UI.
*   **`js/`**: Client-side JavaScript for interactivity (e.g., dynamic cart updates, location fetching).
*   **`images/`**: Static images used across the application (e.g., logos, placeholders).
*   **`uploads/`**: A dynamically used folder where user-uploaded shopping lists (images, PDFs) are temporarily stored for processing.

---

## 🚀 How to Run the Project

1. **Set up a Virtual Environment (Optional but recommended):**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify the Environment:**
   Run the verification script to ensure the database and dependencies are correctly configured.
   ```bash
   python verify.py
   ```

4. **Start the Application:**
   ```bash
   python app.py
   ```
   The application will be available at `http://localhost:5000`.

---
*Note: If there are specific features or architectural details you would like me to expand upon based on your guide questions, please let me know!*
