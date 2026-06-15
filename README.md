# ⚙️ Swello Backend API

The backend engine for **Swello**, a culturally adapted nutritional mobile application designed for Cameroon. Built using **FastAPI**, **Supabase (PostgreSQL)**, and **Google Gemini (Interactions API)**.

This server manages recipe lookups, meal planning logic, user metadata, database transactions, custom nutrient calculations, and AI-powered meal adjustments.

---

## ⚡ Core Highlights

*   **Proprietary Balanced Level Score (BLS)**: Computes a 0–100 score indicating how closely a meal's macros match the ideal Cameroonian profile (25% Protein, 50% Carbs, 25% Fat), weighted by micro-nutrient variety.
*   **Structured Gemini AI Integration**: Utilizes the modern `google-genai` Interactions SDK for structured JSON generation. The AI updates ingredients, instructions, and cookware while strictly enforcing ingredient constraints (refusing to allow structural ingredients to be removed).
*   **Offloaded Calculation Load**: Daily and weekly nutrient aggregations are compiled server-side to optimize battery usage and speed up rendering on mobile webviews.
*   **Container-Optimized Logging**: A custom logging pipeline streams clean text directly to stdout, facilitating seamless log aggregation on services like Render.

---

## 🏗️ Directory Architecture

The backend implements a modular structure to isolate routing, business logic, validation, and core configuration:

```
swello-backend/
├── api/             # FastAPI HTTP endpoint routers
├── core/            # Application settings, DB, and Auth initialization
├── models/          # Pydantic schemas enforcing request/response structures
├── services/        # Pure business logic (Scoring engines, Gemini Prompt service)
├── utils/           # Loggers and helper scripts
├── main.py          # Entry point of the FastAPI application
├── requirements.txt # Python dependency file
└── render.yaml      # Render infrastructure-as-code blueprint
```

### 📂 Codebase Breakdown

#### 📁 `api/` (Routers)
Defines REST routes, handles HTTP exceptions, and communicates with the service layers:
*   **`ai.py`**: Invokes AI meal customizations (`POST /ai/recipe-edit`) and custom recipe calculations (`POST /ai/nutrition/calculate`).
*   **`ingredients.py`**: Exposes `/ingredients` for debounced autocomplete searches in the search view.
*   **`meal_plans.py`**: Handles Monday-to-Sunday planner schedules, with automatic weekly plan setup.
*   **`recipes.py`**: Serves recipe discovery feeds, AND-logic ingredient searches, bookmarking, and custom recipe creations.
*   **`users.py`**: Manages personal profile data using RLS checks.

#### 📁 `core/` (Configurations)
*   **`auth.py`**: Validates incoming Bearer JWTs via Supabase and provides the `get_authed_client` dependency, ensuring all user writes respect Row Level Security.
*   **`config.py`**: Loads and validates variables from `.env` or system environment configurations using Pydantic Settings.
*   **`supabase.py`**: Exposes the generic public database client.

#### 📁 `models/` (Data Schemas)
Houses the strict interface contracts for all endpoints:
*   **`ai.py`**: Contains strict output schemas (`GeminiEditResult`, `MacroShift`) that force Gemini responses to match frontend typescript interfaces.
*   **`meal_plans.py`**: Validates planning operations and maps weekly nutritional balances.
*   **`meals.py`**: Models raw meal entities, tags, and macronutrients.
*   **`recipes.py`**: Enforces strict payload parameters for editing and creating custom recipes.

#### 📁 `services/` (Business Logic)
*   **`ai_editor.py`**: Pre-validates ingredient removal lists against essential items. Manages prompts, formats models, and executes the Gemini query with fallback routines (automatically retrying multiple Gemini model versions on failure).
*   **`nutrition.py`**: Contains the formula for the Balanced Level Score (BLS).

---

## 🚀 Getting Started (Local Development)

### Prerequisites
*   [Python 3.10+](https://www.python.org/)
*   A running Supabase instance (configured using the migration files inside `swello-sql/`)
*   A Google Gemini API key

### 1. Installation
1.  Clone the repository and enter the directory:
    ```bash
    cd swello-app/swello-backend
    ```
2.  Create and activate a virtual environment:
    ```bash
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # macOS/Linux:
    source .venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### 2. Environment Setup
Copy `.env.example` to a new file named `.env`:
```bash
cp .env.example .env
```
Fill out the variables:
```env
SUPABASE_URL="https://your-supabase-url.supabase.co"
SUPABASE_KEY="your-supabase-anon-key"
GEMINI_API_KEY="your-google-gemini-key"
NGROK_AUTHTOKEN="optional-ngrok-token-for-tunneling"
CORS_ORIGINS="http://localhost:3000,http://localhost:5173"
```

### 3. Start the Dev Server
Run the application wrapper:
```bash
python main.py
```
Or launch Uvicorn directly:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
API docs will be available locally at `http://localhost:8000/docs`.

---

## ☁️ Deployment (Render Blueprint)

This project contains a [render.yaml](file:///c:/Users/gwe/Documents/MY%20WORK/PROJECTS/plan-and-diet-app-defense-project/swello-app/swello-backend/render.yaml) file, enabling zero-config deployment on **Render**:

1.  Push your backend repository to GitHub or GitLab.
2.  On the Render Dashboard, click **New** > **Blueprint**.
3.  Connect your repository.
4.  Provide values for the requested variables (`SUPABASE_URL`, `SUPABASE_KEY`, `GEMINI_API_KEY`, and `CORS_ORIGINS`).
5.  Click **Approve**. Render will automatically orchestrate the build and spin up the FastAPI service.
