import sqlite3
import geopandas as gpd
import os
import fiona

from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "gis_data.db"

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
    """Automatically find and load all .shp files in backend/data directory"""
    
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
    """Load a shapefile into SQLite as a table"""
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
    """Load a layer from database as GeoDataFrame"""
    
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

def get_dataset_catalog() -> dict:
    """
    Auto-generate catalog by reading all layers in the database
    
    Helper function for extract_user_intent() function in llm_handler.py
    """
    
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
            
            catalog[layer_name] = {
                "name": layer_name,
                "description": f"{layer_name.replace('_', ' ').title()} dataset",
                "geometry_type": geom_type
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