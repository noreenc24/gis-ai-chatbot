import sqlite3
import geopandas as gpd
import os
import re
import fiona

from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "gis_data.db"

SYNONYM_MAP = {
    "education": ["schools", "school", "education", "educational"],
    "pipeline": ["pipelines", "pipeline", "oil", "gas"],
    "pipelines": ["pipelines", "pipeline", "oil", "gas"],
    "roads": ["roads", "road", "street", "streets"],
    # note: as you add more datasets, add more relevant words that appear in your dataset names as keys and their corresponding lists of synonyms as needed!
}

def init_database() -> None:
    """Initialize SQLite database and load all shapefiles in the backend/data/ folder"""
    
    # create data directory if it doesn't exist
    DATA_DIR.mkdir(exist_ok=True)
    
    # create connection to sqlite database
    conn = sqlite3.connect(DB_PATH)
    conn.enable_load_extension(True)
    conn.close()
    
    # load all shapefiles in the data folder
    loaded_count = load_shapefiles()
    
    if loaded_count == 0:
        print("Error: No shapefiles found in backend/data/ directory")
    else:
        print(f"Database created at: {DB_PATH}")
        print(f"Total layers loaded: {loaded_count}")

def load_shapefiles() -> int:
    """
    Automatically find and load all .shp files in backend/data directory

    Helper function for init_database() function
    """
    
    loaded = 0
    
    # search for all .shp files recursively
    for shapefile_path in DATA_DIR.rglob("*.shp"):
        # 1. get the folder name as the table name
        folder_name = shapefile_path.parent.name
        
        # 2. skip if it's directly in data/ (no subfolder)
        if folder_name == "data":
            continue
        
        # 3. clean table name by lowercasing and replacing spaces/hyphens with underscores
        table_name = folder_name.lower().replace(" ", "_").replace("-", "_")
        
        try:
            load_shapefile(shapefile_path, table_name)
            loaded += 1
        except Exception as e:
            print(f"Failed to load {folder_name}: {e}")
    
    return loaded

def load_shapefile(shapefile_path : str, table_name : str) -> None:
    """
    Loads just ONE shapefile into SQLite as a table
    
    Helper function for load_shapefiles() function
    """
    # 1. check that shapefile exists in data directory
    if not shapefile_path.exists():
        raise FileNotFoundError(f"Shapefile not found: {shapefile_path}")
    
    # 2. if yes, read shapefile with GeoPandas
    gdf = gpd.read_file(shapefile_path)
    
    # 3. ensure it's in WGS84 (EPSG:4326) for web mapping on frontend
    if gdf.crs is None:
        print(f"{shapefile_path.stem} has no CRS, assuming EPSG:4326")
        gdf.set_crs("EPSG:4326", inplace=True)
    elif gdf.crs.to_epsg() != 4326:
        print(f"Reprojecting {shapefile_path.stem} to EPSG:4326")
        gdf = gdf.to_crs("EPSG:4326")
    
    # 4. remove existing layer if it already exists in database (just in case)
    try:
        with fiona.Env():
            if DB_PATH.exists():
                try:
                    fiona.remove(str(DB_PATH), layer=table_name, driver="SQLite")
                except:
                    pass  
    except:
        pass
    
    # 5. save shapefile to SQLite 
    gdf.to_file(DB_PATH, layer=table_name, driver="SQLite")
    
    # 6. detect geometry type
    geom_type = gdf.geometry.geom_type.iloc[0] if len(gdf) > 0 else "Unknown"
    
    print(f"Loaded '{table_name}' ({len(gdf)} features, {geom_type})")

def get_layer_data(layer_name : str) -> gpd.GeoDataFrame:
    """
    Load a layer from database as GeoDataFrame

    Helper function for perform_buffer_analysis() function in gis_processor.py
    """
    
    if not DB_PATH.exists():
        raise FileNotFoundError("Database not initialized. Run init_database() first.")
    
    try:
        gdf = gpd.read_file(DB_PATH, layer=layer_name)
        return gdf
    except Exception as e:
        available = get_dataset_catalog()
        raise ValueError(
            f"Input layer '{layer_name}' not found. "
            f"Available layers: {', '.join(available.keys())}"
        )

def tokenize_name(dataset_name: str) -> list:
    """
    Converts raw dataset name like 'a_Arctic_education_osm' into tokens like ['arctic', 'education'], 
    so that this list of tokens can be used to generate aliases (in generate_aliases() function).

    Helper function for get_dataset_catalog() function
    """
    # 1. lowercase dataset name
    cleaned = dataset_name.lower()

    # 2. remove "a" and "osm" common prefixes/suffixes
    # note: you can tailor which prefixes and suffixes you're looking to remove 
    # if you know if your dataset names have common syntax patterns you'd like to remove
    cleaned = re.sub(r"^a_", "", cleaned)
    cleaned = re.sub(r"_osm$", "", cleaned)

    # Split on underscores and non-letters
    tokens = re.split(r"[^a-z]+", cleaned)
    return [t for t in tokens if t]


def generate_aliases(tokens: list) -> set:
    """
    Create a minimal list of aliases:
    - the tokens themselves
    - any synonyms the developer (you) adds through manual hard-coding above, in SYNONYM_MAP

    Helper function for get_dataset_catalog() function
    """
    aliases = set(tokens)

    # if any of the tokens are in the SYNONYM_MAP, return them as a alias to be stored with that layer in the database
    for token in tokens:
        if token in SYNONYM_MAP:
            for synonym in SYNONYM_MAP[token]:
                aliases.add(synonym)

    return aliases

def get_dataset_catalog() -> dict:
    """
    Auto-generate catalog by reading all layers in the database
    
    Helper function for extract_user_intent() function in llm_handler.py
    """
    # check that database was created and that its path was actually retrieved
    if not DB_PATH.exists():
        return {}
    
    catalog = {} # stores all datasets
    
    try:
        # 1. list all layers in the SQLite database
        layers = fiona.listlayers(str(DB_PATH))
        
        # 2. add each layer to catalog dictionary with info about its name, description, adn geometry type
        for layer_name in layers:
            gdf = gpd.read_file(DB_PATH, layer=layer_name, rows=1)
            geom_type = gdf.geometry.geom_type.iloc[0] if len(gdf) > 0 else "Unknown"
            
            # 3. chunk up the name of the layer into a list of tokenized words
            tokens = tokenize_name(layer_name) 

            # 4. pass in that list of tokenized words to fetch relevant synonym words for each of those tokens 
            aliases = generate_aliases(tokens)

            catalog[layer_name] = {
                "name": layer_name,
                "tokens": tokens,
                "aliases": list(aliases),
                "geometry_type": geom_type,
                "description": f"{layer_name.replace('_', ' ').title()} dataset"
            }
    except Exception as e:
        print(f"Error: Could not read catalog: {e}")
    
    return catalog

# manually run this file to initialize database
if __name__ == "__main__":
    init_database()
    
    print("\nDataset Catalog:")
    for name, info in get_dataset_catalog().items():
        print(f"{name}: {info['geometry_type']} ({info['description']})")