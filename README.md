# Engineering Change Management Assistant (ECA) 🚀

ECA is a high-fidelity, AI-driven assistant designed to manage and automate the Engineering Change Request (ECR) process for complex assemblies (e.g., Industrial Valves). It bridges the gap between natural language engineering requests and parametric CAD modifications.

![ECA Dashboard](https://img.shields.io/badge/Stack-FastAPI%20%7C%20FreeCAD%20%7C%20Gemini-blue)


**Important:** If the api key exhausted ,please make sure to replace the gemini api key in F3/backend/.env
Also , Based on the parts.json database in the system, there are 4 configurable parts that you can request changes for. Here are the parts along with the dimensions that the system currently supports changing:

**Valve Body (PART-001)**

Wall Thickness (e.g., wall_thickness_mm)
Outer Diameter (e.g., outer_diameter_mm)
Inner Diameter (e.g., inner_diameter_mm)
Length (e.g., length_mm)

**End Cap (PART-002)**

Wall Thickness
Outer Diameter
Inner Diameter
Length

**Gate Stem (PART-003)**

Diameter (e.g., diameter_mm)
Length (e.g., length_mm)
Thread Pitch (e.g., thread_pitch_mm)

**Bonnet (PART-004)**

Wall Thickness
Outer Diameter
Bore Diameter (e.g., bore_diameter_mm)
Height (e.g., height_mm)
Instead of asking for a change to a "pipe", you probably want to target the Valve Body, End Cap, or Bonnet depending on exactly what you need to change.
**you could say:**

"Increase the outer diameter of the Valve Body to 100 mm."

## ✨ Core Features

- **🧠 Intelligent Interpretation**: Uses Google Gemini to parse human engineering requests into structured metadata.
- **⚙️ Parametric CAD Modification**: Headless integration with **FreeCAD** to modify `.FCStd` files and export `.step` models automatically.
- **🛡️ Impact & Validation**: 
    - Traces downstream impacts across BOM and Inspection Plans.
    - Performs mechanical validation (e.g., Barlow’s Formula for pressure boundaries).
- **📋 Documentation & Reporting**: Generates automated professional PDF engineering reports via ReportLab.
- **📦 Dual-Asset Archiving**: Automatically archives both native FreeCAD and neutral STEP files to **Supabase Storage**.
- **📜 Version Control**: Full session historization and visual change logs.

## 🛠️ Tech Stack

- **Backend**: Python (FastAPI/Flask)
- **CAD Engine**: FreeCAD (Headless)
- **AI**: Google Generative AI (Gemini 2.5 Flash)
- **Database/Storage**: Supabase (PostgreSQL + S3 Storage)
- **Frontend**: Vanilla JS + CSS (Glassmorphism design)

---

## 🚀 Getting Started (Local Development)

### 1. Prerequisites
- **Python 3.10+**
- **FreeCAD 1.0+** (Ensure `freecadcmd.exe` is in your system path or project config)
- **Supabase Account** (Create a project and a bucket named `eca-cad-models`)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/YOUR_USER/Engineering-Change-Assisstant.git
cd Engineering-Change-Assisstant

# Setup Virtual Environment
python -m venv venv
source venv/bin/activate  # venv\Scripts\activate on Windows

# Install Dependencies
pip install -r F3/backend/requirements.txt
```

### 3. Configuration
Create a `.env` file in the `F3/backend/` directory:
```env
GEMINI_API_KEY=your_key_here
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_service_role_key
```

### 4. Run
```bash
# Start the Backend
cd F3/backend
python app.py

# Open Frontend
# Open F3/frontend/index.html in your browser
```
---

## 🏗️ Repository Structure
```
.
├── F3/
│   ├── backend/          # Flask Orchestrator & AI Agents
│   │   ├── agents/       # The 5-Agent pipeline logic
│   │   ├── cad_models/   # Source .FCStd templates
│   │   └── Dockerfile    # Production Docker build
│   └── frontend/         # Dashboard UI
├── .gitignore            # Prevents committing venv/large files
└── README.md
```

---

## ⚖️ License
Internal Use Only - Industrial Hackathon 2026.
Developed by Stark-X Analytics.
