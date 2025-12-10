import sqlite3
import geopandas as gpd
import os
from pathlib import Path

# Database paths
DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "gis_data.db"

def init_database():
    """Initialize SQLite database and auto-load all shapefiles in data/ folder"""
    
    # create data directory if it doesn't exist
    DATA_DIR.mkdir(exist_ok=True)
    
    # create connection to sqlite database
    conn = sqlite3.connect(DB_PATH)
    conn.enable_load_extension(True)
    conn.close()
    
    # auto-discover and load all shapefiles
    loaded_count = auto_load_shapefiles()
    
    if loaded_count == 0:
        print("⚠️ No shapefiles found in data/ directory")
    else:
        print(f"✅ Database created at: {DB_PATH}")
        print(f"✅ Total layers loaded: {loaded_count}")

def auto_load_shapefiles():
    """Automatically find and load all .shp files in backend/data directory"""
    
    loaded = 0
    
    # Search for all .shp files recursively
    for shapefile_path in DATA_DIR.rglob("*.shp"):
        # 1. Get the folder name as the table name
        folder_name = shapefile_path.parent.name
        
        # 2. Skip if it's directly in data/ (no subfolder)
        if folder_name == "data":
            continue
        
        # 3. Clean table name: lowercase, replace spaces/hyphens with underscores
        table_name = folder_name.lower().replace(" ", "_").replace("-", "_")
        
        try:
            load_shapefile(shapefile_path, table_name)
            loaded += 1
        except Exception as e:
            print(f"❌ Failed to load {folder_name}: {e}")
    
    return loaded

def load_shapefile(shapefile_path, table_name):
    """Load a shapefile into SQLite as a table"""
    
    if not shapefile_path.exists():
        raise FileNotFoundError(f"Shapefile not found: {shapefile_path}")
    
    # Read shapefile with GeoPandas
    gdf = gpd.read_file(shapefile_path)
    
    # Ensure it's in WGS84 (EPSG:4326) for web mapping
    if gdf.crs is None:
        print(f"⚠️ {shapefile_path.stem} has no CRS, assuming EPSG:4326")
        gdf.set_crs("EPSG:4326", inplace=True)
    elif gdf.crs.to_epsg() != 4326:
        print(f"🔄 Reprojecting {shapefile_path.stem} to EPSG:4326")
        gdf = gdf.to_crs("EPSG:4326")
    
    # Save to SQLite (delete existing layer first if it exists)
    try:
        import fiona
        # Remove existing layer if it exists
        with fiona.Env():
            if DB_PATH.exists():
                try:
                    fiona.remove(str(DB_PATH), layer=table_name, driver="SQLite")
                except:
                    pass  # Layer doesn't exist yet, that's fine
    except:
        pass
    
    # Save to SQLite
    gdf.to_file(DB_PATH, layer=table_name, driver="SQLite")
    
    # Detect geometry type
    geom_type = gdf.geometry.geom_type.iloc[0] if len(gdf) > 0 else "Unknown"
    
    print(f"✅ Loaded '{table_name}' ({len(gdf)} features, {geom_type})")

def get_layer_data(layer_name):
    """Load a layer from database as GeoDataFrame"""
    
    if not DB_PATH.exists():
        raise FileNotFoundError("Database not initialized. Run init_database() first.")
    
    try:
        gdf = gpd.read_file(DB_PATH, layer=layer_name)
        return gdf
    except Exception as e:
        available = get_dataset_catalog()
        raise ValueError(
            f"Layer '{layer_name}' not found. "
            f"Available layers: {', '.join(available.keys())}"
        )

def get_dataset_catalog():
    """Auto-generate catalog by reading all layers in the database"""
    
    if not DB_PATH.exists():
        return {}
    
    import fiona
    catalog = {}
    
    try:
        # List all layers in the SQLite database
        layers = fiona.listlayers(str(DB_PATH))
        
        for layer_name in layers:
            # Read a sample to get geometry type
            gdf = gpd.read_file(DB_PATH, layer=layer_name, rows=1)
            geom_type = gdf.geometry.geom_type.iloc[0] if len(gdf) > 0 else "Unknown"
            
            catalog[layer_name] = {
                "name": layer_name,
                "description": f"{layer_name.replace('_', ' ').title()} dataset",
                "geometry_type": geom_type
            }
    except Exception as e:
        print(f"⚠️ Could not read catalog: {e}")
    
    return catalog

# Run this manually to initialize database
if __name__ == "__main__":
    init_database()
    
    # Show what was loaded
    print("\n📚 Dataset Catalog:")
    for name, info in get_dataset_catalog().items():
        print(f"  - {name}: {info['geometry_type']} ({info['description']})")