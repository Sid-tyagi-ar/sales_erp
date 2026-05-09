# Manufacturing ERP API

This project scaffolds a multi-tenant manufacturing inventory and order fulfillment engine using FastAPI and Firebase.

## Tech Stack
- Python 3.11+
- FastAPI
- Pydantic v2
- Firebase Admin SDK (Firestore)
- Uvicorn
- python-dotenv for environment management

## Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd manufacturing_erp
    ```

2.  **Create a Python Virtual Environment (optional but recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Firebase Project Setup:**
    *   Go to the Firebase Console (console.firebase.google.com).
    *   Create a new Firebase project.
    *   Navigate to Project settings -> Service accounts.
    *   Generate a new private key and download the `serviceAccountKey.json` file.
    *   Place this file in a secure location (e.g., outside the project directory or in a `.firebase` folder).

5.  **Environment Variables:**
    *   Create a `.env` file in the root of the project based on `.env.example`:
        ```
        cp .env.example .env
        ```
    *   Edit the `.env` file and update the following:
        ```
        FIREBASE_CREDENTIALS_PATH=/path/to/your/serviceAccountKey.json
        FIREBASE_PROJECT_ID=your-firebase-project-id
        APP_ENV=development
        ```
        Replace `/path/to/your/serviceAccountKey.json` with the actual path to your downloaded Firebase service account key.
        Replace `your-firebase-project-id` with your Firebase project ID.

## How to Run

1.  **Start the FastAPI application:**
    ```bash
    uvicorn app.main:app --reload
    ```
    The API will be accessible at `http://localhost:8000`.

2.  **Access API Documentation:**
    *   Swagger UI: `http://localhost:8000/docs`
    *   ReDoc: `http://localhost:8000/redoc`

3.  **Run the Seed Script:**
    After the API is running, you can populate initial data using the seed script:
    ```bash
    python seed/seed.py
    ```

## Project Structure

```
manufacturing_erp/
├── app/
│   ├── init.py
│   ├── main.py
│   ├── config.py
│   ├── enums.py
│   ├── middleware/
│   │   ├── init.py
│   │   └── tenant.py
│   ├── models/
│   │   ├── init.py
│   │   ├── base.py
│   │   ├── product.py
│   │   ├── warehouse.py
│   │   ├── customer.py
│   │   ├── bom.py
│   │   ├── inventory.py
│   │   ├── ledger.py
│   │   ├── purchase_receipt.py
│   │   ├── manufacturing_order.py
│   │   └── sales_order.py
│   ├── schemas/
│   │   ├── init.py
│   │   ├── tenant.py
│   │   ├── product.py
│   │   ├── warehouse.py
│   │   ├── customer.py
│   │   ├── bom.py
│   │   ├── inventory.py
│   │   ├── ledger.py
│   │   ├── purchase_receipt.py
│   │   ├── manufacturing_order.py
│   │   ├── sales_order.py
│   │   └── error.py
│   ├── services/
│   │   ├── init.py
│   │   ├── tenant_service.py
│   │   ├── product_service.py
│   │   ├── warehouse_service.py
│   │   ├── customer_service.py
│   │   ├── bom_service.py
│   │   ├── ledger_service.py
│   │   ├── inventory_service.py
│   │   ├── purchase_receipt_service.py
│   │   ├── manufacturing_service.py
│   │   └── sales_order_service.py
│   ├── routes/
│   │   ├── init.py
│   │   ├── tenant.py
│   │   ├── product.py
│   │   ├── warehouse.py
│   │   ├── customer.py
│   │   ├── bom.py
│   │   ├── inventory.py
│   │   ├── ledger.py
│   │   ├── purchase_receipt.py
│   │   ├── manufacturing_order.py
│   │   └── sales_order.py
│   └── db/
│       ├── init.py
│       └── firebase.py
├── seed/
│   └── seed.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```