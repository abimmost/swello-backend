# Swello Backend API

The backend for **Swello**, a culturally adapted nutritional mobile application designed for Cameroon. It powers the recipe discovery, meal planning, custom nutritional scoring, and Gemini-based AI meal editing features.

Built with **FastAPI** and **Supabase (PostgreSQL)**, this backend acts as the data layer and business logic hub, serving the Swello React/Capacitor frontend.

---

## ⚡ Core Features

- **Nutritional Intelligence**: Computes the proprietary **Balanced Level Score (BLS)**, a 0–100 metric evaluating macronutrient distribution (25% protein, 50% carbs, 25% fat) and micronutrient diversity.
- **AI Meal Editor**: Integrates with the **Gemini Interactions API** to allow users to customize meals (e.g., "remove chicken"). The AI recalculates macros, adjusts cooking steps, and importantly, prevents the removal of essential/structural ingredients.
- **Cultural Measurement Support**: Fully supports "Estimates" (Anatomical, Volumetric, Natural, Localized units) tailored for Cameroonian cooking practices.
- **Dynamic Aggregation**: Offloads heavy data aggregation (like Weekly Nutrition Summaries) from the frontend client to the backend for performance.

---

## 🏗️ Architecture & Documentation

To keep the codebase maintainable, business logic is isolated from HTTP route handlers.

- **`api/`**: FastAPI routers defining REST endpoints.
- **`core/`**: Initialization (Supabase, Auth, settings).
- **`models/`**: Pydantic schemas validating all incoming/outgoing data.
- **`services/`**: Pure business logic (e.g., `nutrition.py`, `ai_editor.py`).

**Deep-Dive Documentation:**
For a complete breakdown of the architecture, data models, and API contracts, see the `swello-docs` folder:
- [API Endpoints Guide](../../swello-docs/api-endpoints.md)
- [Backend Architecture Guide](../../swello-docs/backend-architecture.md)

---

## 🚀 Getting Started (Local Development)

### Prerequisites
- Python 3.10+
- A Supabase project instance
- A Gemini API Key

### 1. Installation
Clone the repo and navigate to the backend directory:
```bash
cd swello-app/swello-backend
```

Install the required Python dependencies:
```bash
pip install -r requirements.txt
```

### 2. Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in the credentials:
- `SUPABASE_URL` and `SUPABASE_KEY`
- `GEMINI_API_KEY`

### 3. Run the Server
Start the FastAPI development server using Uvicorn (configured to use standard output for logs, optimized for platforms like Render):
```bash
python main.py
# or directly:
uvicorn main:app --reload
```

The server will be available at `http://localhost:8000`.

### 4. Interactive API Docs
FastAPI automatically generates interactive Swagger documentation. Once the server is running, visit:
[http://localhost:8000/docs](http://localhost:8000/docs)

---

## ☁️ Deployment (Render Blueprint)

This project is pre-configured for one-click deployment on **Render** using a Blueprint configuration file (`render.yaml`).

### Deploying to Render
1. Push this backend repository (`swello-app/swello-backend/` is its own Git repo) to your GitHub/GitLab account.
2. In the Render Dashboard, go to **Blueprints** and click **New Blueprint Instance**.
3. Select your repository. Render will auto-detect the `render.yaml` configuration.
4. Render will prompt you to fill in the following environment variables:
   * `SUPABASE_URL`: Your Supabase project URL.
   * `SUPABASE_KEY`: Your Supabase project anonymous public/anon key (or service_role key if needed).
   * `GEMINI_API_KEY`: Your Google Gemini API Key.
   * `CORS_ORIGINS`: Comma-separated list of allowed origins (e.g., your Vercel deployment URL and local ports: `https://your-app.vercel.app,http://localhost:3000,http://localhost:5173`).
5. Click **Approve** to deploy.

