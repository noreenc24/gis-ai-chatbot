# Increasing Accessibility to Arctic Spatial Data Analysis with LLMs (Natural Language GIS Chatbot)
This GIS chatbot is a backend application that uses an LLM (Google Gemini 2.5 Flash) to answer natural language questions about spatial data. In other words, to interact with this chatbot, you will need to start a locally-hosted server and make API calls through there, instead of typing into a standard, aesthetic chatbot-looking user interface.

This project is specifically scoped to only perform buffer analyses on schools and oil pipelines in the Arctic, but it can be scaled to handle additional types of geoprocessing functions and accomodate other topic-specific datasets.

In its full vision, this chatbot could be integrated within a full-stack web GIS application to further complement the accessibility to basic geospatial analyses that a regular, standalone web GIS app offers. Therefore, the technical architecture of this project includes also includes the framework structure for additional frontend development. 

## Project Capabilities:
This GIS chatbot backend application's capabilities include: 
- **Natural Language GIS Queries**: Users can ask spatial questions in plain English
- **AI Function Calling**: Gemini LLM interprets these user queries and calls spatial functions
- **Automated Buffer Analysis**: GeoPandas performs spatial operations
- **GeoJSON Output**: Returns results ready for interactive map visualization on the frontend, with Mapbox (not implemented in this project).

## Datasets used:
I used two datasets:
- [Oil pipeline infrastructure around the world](https://globalenergymonitor.org/projects/global-oil-infrastructure-tracker/)
- [Arctic educational institutions](https://www.openstreetmap.org/#map=4/38.03/-95.80)

## High-level workflow steps
1. API endpointreceives query from user and passes it into LLM.
2. LLM function calling: LLM identifies appropriate geoprocessing tool AND parses user's input text to extract necessary input parameters.
3. Backend checks if relevant datasets exist/are available in SQLite database. If a dataset that a user specified in their query is missing, return error message to user.
4. If no datasets are missing, call the appropriate geoprocessing function to get analysis results.
5. LLM interprets these analysis results into a natural-language message to user.
6. API endpoint returns this message AND geojson for mapping to the user.

## Project Structure

```
gis-chatbot/
├── backend/
│   ├── app.py                 # FastAPI server
│   ├── database.py            # SQLite + data loading
│   ├── gis_processor.py       # GeoPandas buffer analysis
│   ├── llm_handler.py         # Gemini LLM function calling
│   ├── requirements.txt
│   └── data/
│       ├── gis_data.db         # Generated SQLite database
│       ├── a_Arctic_Education_OSM    # Example dataset 1
│       └── oil_pipelines.geojson  # Example dataset 2
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Main component
│   │   ├── App.css            # Styles
│   │   └── main.jsx           # Entry point
│   ├── package.json
│   └── index.html
└── README.md
```

## Tech Stack
While the high-level architecture of this codebase is set up to accomodate a full stack application, only the backend processes were developed for the scope of this final project.

### Backend
- **Google Gemini 2.5 Flash**: LLM with function calling
- **FastAPI**: Backend API server
- **SQLite**: Spatial database
- **GeoPandas**: Spatial data processing

## Technical Prerequisites
You will need the following on your computer:
- Python 3.9+
- Google Gemini API Key (free)

For the frontend (optional): 
- Mapbox API Token (free)

## Quick Start for Set Up:
Open an IDE (like VSCode) or your computer's terminal application and copy and paste the following terminal commands in each step. Any steps marked with (optional) indicate that they are not within the scope of this project, but could be developed further for a full-stack application.

### 1. Clone this GitHub repository

```bash
git clone https://github.com/noreenc24/gis-ai-chatbot.git
cd gis-chatbot 
```

### 2. Backend setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate
```

### 3. Install dependencies listed in the requirements.txt file 
Dependencies are all the required packages needed to make the scripts in this application run. 

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables in a .env file
Create a .env file in the backend directory to keep your personal, unique API key safe.
```bash
echo "GEMINI_API_KEY=your_key_here" > .env
```

**Next, get your free Google Gemini API Key (which will let you connect this application to Google's Gemini models!)**
1. Visit https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key to `.env` file

### 5. Add your shapefiles
Place your shapefiles into the ```backend/data/``` folder. This can be done within your computer's local file manager through dragging and dropping these shapefile subfolders into this project's directory.

Each shapefile subfolder should contain the complete shapefile (.shp, .shx, .dbf, .prj files).

### 6. Initialize database

```bash
# Still in backend/ directory
python database.py
```

This creates ```data/gis_data.db``` and loads all shapefiles from the data subfolders.

### 7. Start backend server

```bash
python app.py
```
Backend runs at: `http://localhost:8000`
View API docs at: `http://localhost:8000/docs`

---
## Using the backend application after starting the server (2 ways)
**1. Testing via API requests**

1. Open `http://localhost:8000` in your computer's browser
2. Click on "POST /api/chat" endpoint
3. Click "Try it out"
4. Enter a query related to any of the datasets in your project's database such as: "How many schools are within 1 mile of pipelines?"
5. Click "Execute" to see the response

**2. Testing via Python scripts**
You can also test directly by running:
```bash
python llm_handler.py
```
This runs the test queries at the bottom of the file, so make sure to edit the queries as needed.
Example queries:
- "How many schools are within 1 mile of pipelines?"
- "Find schools within 2 kilometers of pipelines"
- "Which schools are near pipelines?

--- 

The following steps are for setting up the frontend portion of the app and are optional:
### 8. Frontend Setup (optional)

```bash
# Open new terminal, navigate to frontend
cd frontend

# Install dependencies
npm install

# Create .env file
echo "VITE_MAPBOX_TOKEN=your_token_here" > .env
```

**Get Mapbox token for free (optional):**
1. Visit: https://account.mapbox.com/
2. Sign up (free tier: 50,000 map loads/month)
3. Copy "Default public token"
4. Paste into `frontend/.env`

### 6. Start Frontend (optional)

```bash
npm run dev
```

Frontend runs at: `http://localhost:5173`

## Full-stack Application Version Usage (optional)

1. Open `http://localhost:5173` in browser
2. Try example queries:
   - "How many schools are within 1 mile of pipelines in Alaska?"
   - "Find schools within 2 kilometers of pipelines"
   - "What schools are near pipelines?"
3. View results on the interactive map

## Resources
- **Gemini API**: https://ai.google.dev/gemini-api/docs
- **GeoPandas**: https://geopandas.org/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Mapbox GL JS**: https://docs.mapbox.com/mapbox-gl-js/

## MIT License
Feel free to fork this repo and tailor for your own project!

## Credits
This project was created as a final course project for EEPS 1350: Spatial Data Science.