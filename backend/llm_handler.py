import google.generativeai as genai
import os
import json

from database import get_dataset_catalog
from gis_processor import perform_buffer_analysis

# configure Gemini model here
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# client = genai.Client()  # automatically gets GEMINI_API_KEY from .env file

# for this project, only define the buffer function as a tool for Gemini to use
# in the future, you could add more geoprocessing tools to this list
# Gemini API function calling documentation link: https://ai.google.dev/gemini-api/docs/function-calling?example=meeting
geoprocessing_tools = [{
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
}]
    

async def process_user_query(query: str) -> dict:
    """
    High level structure of LLM GIS query pipeline with function calling:
    1. user passes natural language query into LLM
    2. LLM parses user's input text to extract necessary input parameters
    3. check if relevant datasets exist/are available in database
    4. LLM identifies and runs the appropriate GIS geoprocessing function (for this project, only buffer)
    5. LLM interprets GIS results into a natural-language message to user 
    6. return message AND geojson for mapping
    
    In this pipeline, the LLM has 3 main tasks at steps 2, 4, and 5.
    """
    # 1. user passes natural language query into LLM
    # 2. LLM parses user's input text to extract necessary input parameters
    # 3. check if relevant datasets exist/are available in database
    # 4. LLM identifies appropriate GIS geoprocessing functions (for this project, only buffer)
    results = extract_user_intent(query)

    # check if error message is returned due to user's specified buffer and/or target layer missing from database
    if "message" in results:
        return {
            "message": results["message"],
            "features_geojson": None, 
            "buffer_geojson": None,
            "count": None,
            "params": None
        }
    # else: # user specified a target and buffer layer that actually exists in database
    #     target_layer = parsed_input["target_layer"]
    #     buffer_layer = parsed_input["buffer_layer"]
    #     distance = parsed_input["distance"]
    #     unit = parsed_input["unit"]

    
    # 5. LLM interprets GIS results into a natural-language message to user 
    results_message = generate_results_interpretation(query, results)
    
    # 6. return message AND geojson for mapping 
    return {
        "message": results_message,
        "features_geojson": results["features_geojson"], 
        "buffer_geojson": results["buffer_geojson"],
        "count": results["count"],
        "params": results["params"] # subdictionary with target_layer, buffer_layer, distance, unit
    }


def extract_user_intent(query: str) -> dict:
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

    # in the style of providing a role/persona to the LLM:
    system_prompt = f"""
        You are a world class GIS analyst that interprets natural-language proximity queries.

        Your task:
        1. Determine if the user's query indicates a proximity relationship (e.g., within, near, close to).
        2. Extract the four buffer-analysis parameters:
        - target_layer: the features being searched for
        - buffer_layer: the features to buffer around
        - distance (default 0.5 if missing)
        - unit (miles/km/meters/feet; default miles)
        3. If the query matches a proximity task, call the buffer_analysis tool with these parameters.
        4. If it does not match, do NOT call any tool. Return a normal text response instead.

        Only call tools when the query clearly describes a spatial proximity question.
        """
    
    # 3. initialize Gemini model with function calling to just buffer analysis (for this project)
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        tools=geoprocessing_tools 
    )
    
    # 4. pass in system prompt AND user's query to Gemini
    response = model.generate_content(
        contents=f"{system_prompt}\nUser query: {query}"
        )
    
    # 5. check if Gemini wants to call a geoproessing function (for this project, only perform_buffer_analysis is an option)
    function_call = None
    for part in response.candidates[0].content.parts:
        if getattr(part, "function_call", None):
            function_call = part.function_call
            break
    
    # if Gemini didn't make a function call, then just return a typical response Gemini generates
    if function_call is None:
        return {
            "message": response.text,
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
        }
    
    # 8. if neither layer is missing from database, make function call to whichever one Gemini decided on
    if function_call.name == "buffer_analysis":
        results = perform_buffer_analysis(target_layer, buffer_layer, distance, unit)
        return results
    
    # hypothetical code for scaling to include other geoprocessing tools
    # elif function_call.name == "intersection_analysis":
        # results = intersection_analysis(...)
        
        
def generate_results_interpretation(query: str, analysis_output: dict) -> str:
    """
    LLM interprets the basic info about the results of GIS geoprocessing analysis function (AKA the step right before this) to 
    return to the user in a very intuitive, natural language format.

    Helper function for process_user_query() function
    """
    model = genai.GenerativeModel("gemini-2.5-flash")

    # only pass in the basic, essential info from analysis_output to limit token usage (basically, everything except the 2 geoJSONs)
    basic_results = {
        "count": analysis_output["count"],
        "params": analysis_output["params"] # subdictionary with target_layer, buffer_layer, distance, unit
    }

    # pass in the original user query and the GIS output into the prompt to tailor model
    # in the style of providing more holistic context to the LLM:
    system_prompt = f"""
        You are a world class GIS analyst explaining spatial analysis results to a general audience.
        Use the user's query for context, and summarize the buffer analysis concisely, clearly, and intuitively.
        Avoid technical jargon.

        User query: {query}

        GIS analysis results:
        - {basic_results['count']} features found
        - Target layer: {basic_results['params']['target_layer']}
        - Buffer layer: {basic_results['params']['buffer_layer']}
        - Distance: {basic_results['params']['distance']} {basic_results['params']['unit']}
        """
    
    # pass prompt into model
    try:
        response = model.generate_content(system_prompt)
        return response.text.strip()
    except Exception as e:
        # backup/fallback response if LLM fails (like if you've reached token or call limits)
        return f"Found {basic_results['count']} {basic_results['params']['target_layer']} within {basic_results['params']['distance']} {basic_results['params']['unit']} of {basic_results['params']['buffer_layer']}."
    

# Test function with example user queries
if __name__ == "__main__":
    import asyncio
    
    # uncomment each query one at a time (or run all at once, but make sure to add commas separating each one)
    test_queries = [
        # "How many schools are within 1 mile of pipelines?" # standard prompt
        # "Which schools are near pipelines?" # user query is missing a parameter
        # "How many dogs are near pipelines?" # include one totally unrelated dataset that doesn't exist
        "What's the weather like" # non-spatial question
    ]
    
    async def test():
        for query in test_queries:
            print(f"Test query: {query}")
            try:
                result = await process_user_query(query)
                print(f"Result: {result['message']}")
                print(f"Features found: {result['count']}")
            except Exception as e:
                print(f"Error: {e}")
    
    asyncio.run(test())