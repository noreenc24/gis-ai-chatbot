import google.generativeai as genai
import os
import json

from database import get_dataset_catalog
from gis_processor import perform_buffer_analysis

# configure Gemini model here
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# define the buffer function schema for as a tool for the LLM
# Gemini API function calling documentation link: https://ai.google.dev/gemini-api/docs/function-calling?example=meeting
buffer_analysis_schema = {
    "function_declarations": [
        {
            "name": "buffer_analysis",
            "description": "Find features from one layer that are within a certain distance of features in another layer. Example: 'schools within 1 mile of pipelines'",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "target_layer": {
                        "type": "STRING",
                        "description": "The layer to search (e.g., 'schools', 'hospitals')"
                    },
                    "buffer_layer": {
                        "type": "STRING",
                        "description": "The layer to create a buffer around (e.g., 'pipelines', 'roads')"
                    },
                    "distance": {
                        "type": "NUMBER",
                        "description": "The buffer distance as a number (e.g., 1, 2.5)"
                    },
                    "unit": {
                        "type": "STRING",
                        "description": "The unit of distance",
                        "enum": ["miles", "kilometers", "meters", "feet"]
                    }
                },
                "required": ["target_layer", "buffer_layer", "distance", "unit"]
            }
        }
    ]
}

async def process_user_query(query: str) -> dict:
    """
    High level structure of LLM GIS query pipeline:
    1. user passes natural language query into LLM
    2. LLM parses user's input text to extract necessary input parameters
    3. check if relevant datasets exist/are available in database
    4. run GIS geoprocessing functions (for this project, only buffer)
    5. LLM interprets GIS results into a natural-language message to user 
    6. return message AND geojson for mapping
    
    In this pipeline, the LLM has 2 main tasks at steps 2 and 5.
    """
    # 1. user passes natural language query into LLM
    # 2. LLM parses user's input text to extract necessary input parameters
    # 3. check if relevant datasets exist/are available in database
    parsed_input = extract_user_intent(query)

    # check if error message is returned due to user's specified buffer and/or target layer missing from database
    if "message" in parsed_input:
        return {
            "message": parsed_input["message"],
            "features_geojson": None, 
            "buffer_geojson": None,
            "count": None,
            "params": None
        }
    else: # user specified a target and buffer layer that actually exists in database
        target_layer = parsed_input["target_layer"]
        buffer_layer = parsed_input["buffer_layer"]
        distance = parsed_input["distance"]
        unit = parsed_input["unit"]

    # 4. run GIS geoprocessing functions (for this project, only buffer)
    result = perform_buffer_analysis(target_layer, buffer_layer, distance, unit)
    
    # 5. LLM interprets GIS results into a natural-language message to user 
    results_message = generate_results_interpretation(query, result)
    
    # 6. return message AND geojson for mapping 
    return {
        "message": results_message,
        "features_geojson": result["features_geojson"], 
        "buffer_geojson": result["buffer_geojson"],
        "count": result["count"],
        "params": result["params"] # params is a subdictionary with target_layer, buffer_layer, distance, unit
    }


def extract_user_intent(query: str) -> str:
    """
    Parses user's input text to extract necessary input parameters for the geoprocessing tool

    Helper function for process_user_query() function
    """
    # 1. get dataset catalog (AKA all the datasets in database) to give Gemini context of which datasets are avaialle
    catalog = get_dataset_catalog()
    
    if not catalog:
        raise ValueError("There are no datasets available in database. Run init_database() first!")
    
    # 2. customize system prompt, create list of available datasets
    dataset_list = ", ".join(catalog.keys())
    system_prompt = f"""You are a world class GIS assistant. Available datasets: {dataset_list}.
        When a user asks spatial question involving proximity, call the perform_buffer_analysis function with appropriate parameters.
        Extract the target layer, buffer layer, distance, and unit from the user's input text.

        Examples:
        - "schools within 1 mile of pipelines" → target_layer: schools, buffer_layer: pipelines, distance: 1, unit: miles
        - "hospitals near roads" → Assume 0.5 miles if distance not specified
        - "find schools 2 km from pipelines" → target_layer: schools, buffer_layer: pipelines, distance: 2, unit: kilometers
        """
    
    # 3. initialize Gemini model with function calling
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        tools=[buffer_analysis_schema]
    )
    
    # 4. pass in system prompt AND user's query to Gemini
    response = model.generate_content(contents=f"{system_prompt}\nUser query: {query}")
    
    # 5. check if Gemini wants to call a geoproessing function (for this project, only perform_buffer_analysis is an option)
    function_call = None
    for part in response.candidates[0].content.parts:
        if getattr(part, "function_call", None):
            function_call = part.function_call
            break
    
    # if Gemini didn't make a function call to buffer, then just return a typical response Gemini generates
    if function_call is None:
        return {
            "message": response.text,
            "geojson": None,
        }
    
    # 6. extract parameters from Gemini's constructed arguments for the buffer analysis
    args = function_call.args
    target_layer = args.get("target_layer")
    buffer_layer = args.get("buffer_layer")
    distance = args.get("distance")
    unit = args.get("unit")
    
    # 7. validate that user-specified target and buffer layers exist in catalog (AKA the database)
    missing_datasets = [] # store user-specified datasets that don't exist in database

    if target_layer not in catalog:
        missing_datasets.append(target_layer)
    if buffer_layer not in catalog:
        missing_datasets.append(buffer_layer)
    
    # if either target or buffer layer is missing, then return error message to user
    if missing_datasets:
        return {
            "message": f"Dataset(s) not found: {missing_datasets}. Please enter a query that relates to any of the available datasets, which are: {dataset_list}.",
            "geojson": None
        }
    else: # if neither is missing from database
        return {
            "target_layer": target_layer,
            "buffer_layer": buffer_layer,
            "distance": distance,
            "unit": unit,
        }

def generate_results_interpretation(query: str, analysis_output: dict) -> str:
    """
    Interprets the results of GIS geoprocessing analysis function (AKA the step right before this) to 
    return to the user in a very intuitive, natural language format.

    Helper function for process_user_query() function
    """
    model = genai.GenerativeModel("gemini-2.5-flash")

    # pass in the original user query and the GIS output into the prompt to tailor model
    prompt = f"""
        User query:
        {query}

        GIS analysis result (structured):
        {analysis_output}

        Write a concise natural-language explanation a GIS analyst would give.
        Avoid technical jargon like 'dissolve', 'project', or 'GeoDataFrame'.
        """
    
    # pass prompt into model
    response = model.generate_content(prompt)
    return response.text.strip()


# Test function
if __name__ == "__main__":
    import asyncio
    
    # Test queries
    test_queries = [
        # "How many schools are within 1 mile of pipelines?"
        # "Find schools within 2 kilometers of pipelines",
        "What schools are near pipelines?"
    ]
    
    async def test():
        for query in test_queries:
            print(f"\n🧪 Testing: {query}")
            try:
                result = await process_user_query(query)
                print(f"✅ Result: {result['message']}")
                print(f"   Features found: {result['count']}")
            except Exception as e:
                print(f"❌ Error: {e}")
    
    asyncio.run(test())