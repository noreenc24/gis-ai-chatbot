# Arctic Data GIS Chatbot (GeoAI Spatial Analysis)
This GIS chatbot is a full-stack web application that uses AI (Google Gemini) to answer natural language questions about geospatial data. This project is specifically scoped to only perform buffer analyses on schools and oil pipelines in Alaska, but it can be scaled to handle additional types of geoprocessing functions and accomodate other topic-specific datasets.

## What is a GIS chatbot?
This project demonstrates:
- **Natural Language GIS Queries**: Ask spatial questions in plain English
- **AI Function Calling**: Gemini LLM interprets queries and calls spatial functions
- **Automated Buffer Analysis**: GeoPandas performs spatial operations
- **Interactive Visualization**: Mapbox displays results on an interactive map

**Example Query**: *"How many schools are within 1 mile of pipelines in Alaska?"*

## Architecture

```
Frontend (React + Mapbox)
    ↓ REST API
Backend (FastAPI)
    ↓ Function Calling
Google Gemini 1.5 Flash
    ↓ Structured Parameters
GIS Processor (GeoPandas)
    ↓ Spatial Query
SQLite Database with shapefiles (SpatiaLite)
    ↓ GeoJSON Results
Mapbox Visualization
```

## Tech Stack
### Backend
- **FastAPI**: Modern async web framework
- **Google Gemini 1.5 Flash**: LLM with function calling
- **SQLite + SpatiaLite**: Spatial database
- **GeoPandas**: Spatial data processing
- **Shapely**: Geometric operations

### Frontend
- **React 18**: UI framework
- **Mapbox GL JS**: Interactive maps
- **Vite**: Build tool

## Technical Prerequisites
You will need the following versions of Python and Node.js on your computer:
- Python 3.9+
- Node.js 18+
- Google Gemini API Key (free)
- Mapbox API Token (free)

To check if you have the correct 


## Quick Start for Set Up:
Open an IDE (like VSCode) or your computer's terminal application and copy and paste the following terminal commands in each step:

### 1. Clone this GitHub repository

```bash
git clone https://github.com/noreenc24/gis-ai-chatbot.git
cd gis-chatbot 
```

### 2. Backend Setup

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

# Install dependencies

### 3. Install dependencies listed in requirements.txt file (AKA all the required packages)
Dependencies are the 

```bash
pip install -r requirements.txt
```

# Create .env file
```bash
echo "GOOGLE_API_KEY=your_key_here" > .env
```

**Get your free Google Gemini API Key**
1. Visit https://aistudio.google.com/app/apikey
2. Click "Create API Key", Select
3. Copy key to `.env` file

### 3. Initialize Database

```bash
# Still in backend/ directory
python -c "from database import init_database; init_database()"
```

This creates:
- `data/gis_data.db` - SQLite database
- `data/schools.geojson` - Sample school locations
- `data/pipelines.geojson` - Sample pipeline routes

### 4. Start Backend Server

```bash
python app.py
```

Backend runs at: `http://localhost:8000`

Test it: `http://localhost:8000/health`

### 5. Frontend Setup

```bash
# Open new terminal, navigate to frontend
cd frontend

# Install dependencies
npm install

# Create .env file
echo "VITE_MAPBOX_TOKEN=your_token_here" > .env
```

**Get Mapbox Token (Free):**
1. Visit: https://account.mapbox.com/
2. Sign up (free tier: 50,000 map loads/month)
3. Copy "Default public token"
4. Paste into `frontend/.env`

### 6. Start Frontend

```bash
npm run dev
```

Frontend runs at: `http://localhost:5173`

## 🎮 Usage

1. Open `http://localhost:5173` in browser
2. Try example queries:
   - "How many schools are within 1 mile of pipelines in Alaska?"
   - "Find schools within 2 kilometers of pipelines"
   - "What schools are near pipelines?"
3. View results on the interactive map
4. Red dots = schools found within buffer
5. Blue shaded areas = buffer zones

## 📁 Project Structure

```
gis-chatbot/
├── backend/
│   ├── app.py                 # FastAPI server
│   ├── database.py            # SQLite + data loading
│   ├── gis_processor.py       # GeoPandas buffer analysis
│   ├── llm_handler.py         # Gemini function calling
│   ├── requirements.txt
│   └── data/
│       ├── gis_data.db        # Generated SQLite DB
│       ├── schools.geojson    # Generated sample data
│       └── pipelines.geojson  # Generated sample data
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Main component
│   │   ├── ChatPanel.jsx      # Chat interface
│   │   ├── MapView.jsx        # Mapbox map
│   │   ├── App.css            # Styles
│   │   └── main.jsx           # Entry point
│   ├── package.json
│   └── index.html
├── .env                       # API keys (backend)
└── README.md
```

## 🔧 How It Works

### 1. User Query Processing

```
User: "How many schools within 1 mile of pipelines?"
  ↓
Frontend sends to: POST /api/chat
```

### 2. LLM Function Calling

```python
# Gemini receives dataset catalog + query
# Returns structured JSON:
{
  "function": "buffer_analysis",
  "target_layer": "schools",
  "buffer_layer": "pipelines",
  "distance": 1,
  "unit": "miles"
}
```

### 3. Backend Validation

- Checks if datasets exist in SQLite catalog
- If missing, returns error message to user

### 4. GIS Processing

```python
# Load data from SQLite
schools = load_layer("schools")
pipelines = load_layer("pipelines")

# Create buffer (1 mile = ~0.0145 degrees)
buffered = pipelines.buffer(0.0145)

# Spatial join
results = schools[schools.within(buffered)]
```

### 5. Return Results

```json
{
  "message": "Found 3 schools within 1 mile of pipelines in Alaska.",
  "geojson": { /* GeoJSON features */ },
  "metadata": {
    "count": 3,
    "operation": "buffer"
  }
}
```

### 6. Map Visualization

- Red circles = result features (schools)
- Blue polygons = buffer zones
- Click points for details

### Future Enhancements

- Support more GIS operations (intersect, clip, union)
- Add more datasets (roads, buildings, parks)
- Multi-step queries (e.g., "schools AND hospitals near pipelines")
- Export results as CSV/Shapefile
- User upload of custom GeoJSON

## 🐛 Troubleshooting issues/bugs

### Backend won't start

```bash
# Check Python version
python --version  # Must be 3.9+

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Database errors

```bash
# Regenerate database
rm -rf data/
python -c "from database import init_database; init_database()"
```

### Gemini API errors

- Check API key in `.env`
- Verify free tier limits: 1,500 requests/day
- Check: https://console.cloud.google.com/

### Mapbox not loading

- Check token in `frontend/.env`
- Must start with `pk.`
- Verify free tier: 50,000 loads/month

### CORS errors

- Ensure backend runs on port 8000
- Check CORS settings in `app.py`

## 📚 Resources

- **Gemini API**: https://ai.google.dev/gemini-api/docs
- **Mapbox GL JS**: https://docs.mapbox.com/mapbox-gl-js/
- **GeoPandas**: https://geopandas.org/
- **FastAPI**: https://fastapi.tiangolo.com/

## 📝 License

MIT License - feel free to use for your course project!

## 👥 Credits

Created as a final project for Spatial Data Science course.

---

**Questions?** Open an issue or check the troubleshooting section above.