import geopandas as gpd
from database import get_layer_data
import json

def perform_buffer_analysis(target_layer: str, buffer_layer: str, distance: float, unit: str):
    """
    Perform buffer analysis to find features from target_layer within distance of buffer_layer
    
    Args:
        target_layer: Layer to search (e.g., "schools")
        buffer_layer: Layer to buffer around (e.g., "pipelines")
        distance: Buffer distance (e.g., 1)
        unit: Distance unit ("miles", "kilometers", "meters", "feet")
    
    Returns:
        dictionary with:
            count: number of features found
            features_geojson: the target-layer features inside the buffer (GeoJSON)
            buffer_geojson: the dissolved buffer polygon (GeoJSON)
            params: info needed by the LLM or frontend
    """
    # 1. load relevant datasets from database
    target_gdf = get_layer_data(target_layer)
    buffer_gdf = get_layer_data(buffer_layer)
    
    # check if either dataset is empty
    if target_gdf is None or len(target_gdf) == 0:
        raise ValueError(f"No data found in '{target_layer}' layer")
    
    if buffer_gdf is None or len(buffer_gdf) == 0:
        raise ValueError(f"No data found in '{buffer_layer}' layer")
    
    # 2. convert input user distance to meters to prepare for buffer tool
    distance_meters = convert_to_meters(distance, unit)

    # 3. create copies of buffer and target gdf, then reproject both to arctic polar stereographic, which is in meters
    buffer_copy = buffer_gdf.copy()
    target_copy = target_gdf.copy()

    reprojected_buffer = buffer_copy.to_crs(epsg=3995) 
    reprojected_target = target_copy.to_crs(epsg=3995) 

    # 4. run buffer function to add buffers around buffer layer's features
    # buffered_geometry = reprojected_buffer.geometry.buffer(distance_meters)
    buffered_geometry = reprojected_buffer.buffer(distance_meters)

    # 5. dissolve all buffers into a single polygon using union
    dissolved_buffer = gpd.GeoSeries(buffered_geometry).union_all()
    
    # 6. find and count number of target features that intersect with the buffer
    # results = reprojected_target[reprojected_target.geometry.intersects(dissolved_buffer)]
    results = reprojected_target[reprojected_target.intersects(dissolved_buffer)]
    count = len(results)

    # 7. reproject intersection results AND dissolved buffer back to wgs84 for web mapping
    final_geometry = gpd.GeoDataFrame(geometry=[dissolved_buffer], crs=reprojected_buffer.crs).to_crs(epsg=4326)
    final_results = results.to_crs(epsg=4326)

    # 8. convert both buffer geometry and selected features to geoJSONs
    buffer_geojson = json.loads(final_geometry.to_json())
    
    if count > 0:
        features_geojson = json.loads(final_results.to_json())
    else: 
        features_geojson = None
    
    # 9. return response with buffer results
    return {
        "count": count,
        "features_geojson": features_geojson, # target features inside buffer
        "buffer_geojson": buffer_geojson, # the one dissolved buffer polygon
        "params": {
            "target_layer": target_layer,
            "buffer_layer": buffer_layer,
            "distance": distance,
            "unit": unit,
        }
    }

def convert_to_meters(distance: float, unit: str) -> float:
    """
    Convert any input distance to meters

    Helper function for perform_buffer_analysis() function
    """
    
    # 1. dictionary of common distance units -> convert to meters
    units_to_meters = {
        "meters": 1,
        "kilometers": 1000,
        "miles": 1609.34,
        "feet": 0.3048
    }
    
    if unit not in units_to_meters:
        raise ValueError(f"Unsupported unit: {unit}. Use: miles, kilometers, meters, or feet")
    
    # 2. calculate conversion to meters
    distance_meters = distance * units_to_meters[unit]
    
    return distance_meters


# Test function
if __name__ == "__main__":
    # Test buffer analysis
    try:
        print("🧪 Testing buffer analysis...")
        result = perform_buffer_analysis(
            target_layer="a_arctic_education_osm",
            buffer_layer="oil_pipelines",
            distance=0.5,
            unit="miles"
        )
        
        print(f"   Features found: {result['count']}")
    
    except Exception as e:
        print(f"❌ Error: {e}")