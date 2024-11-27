import pandas as pd
from azure.storage.blob import BlobServiceClient
from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from models.prediction import PredictionRequest,PredictionResponse
import asyncio
import aiohttp
import time
import httpx
 
# Azure Blob Storage connection details
AZURE_STORAGE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=stmoliaihub774999322363;AccountKey=5zbHRn/VU9x4BlIz9ZH9ngZvGTyXjp0jB6pOXaLldGAMy1P4QTyRNP8g6/bC1gmN2xiCOQe+2Unm+AStUVApoA==;EndpointSuffix=core.windows.net"
CONTAINER_NAME = "excel"
BLOB_NAME = "NewData.xlsx"
 
# Define the FastAPI app
router = APIRouter()

 
# Azure Machine Learning endpoint URL and key
AZURE_ENDPOINT_URL = "https://moli-ai-dev-ws3-ml-uzabg.westus3.inference.ml.azure.com/score"
AZURE_API_KEY = "hbhEYHNEd1n5ArUJMRgnhtXmvzD7BZu6"
 
# Cache the data to avoid fetching it every time
cached_df = None
 
def fetch_data_from_blob():
    """Fetches and caches data from Azure Blob Storage."""
    global cached_df
    if cached_df is None:
        try:
            blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
            container_client = blob_service_client.get_container_client(CONTAINER_NAME)
            blob_client = container_client.get_blob_client(BLOB_NAME)
            blob_data = blob_client.download_blob().readall()
            cached_df = pd.read_excel(pd.io.common.BytesIO(blob_data))
        except Exception as e:
            print(f"Error fetching data from blob: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve data from Blob Storage.")
    return cached_df

async def make_request(session, azure_input_data):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AZURE_API_KEY}"
    }
    async with session.post(AZURE_ENDPOINT_URL, json=azure_input_data, headers=headers) as response:
        if response.status != 200:
            print(f"Error in Azure ML response: {response.status}")
            raise HTTPException(status_code=500, detail="Azure ML request failed.")
        return await response.json()

def round_to_nearest_five(value):
    """Round the given value to the nearest higher multiple of 5."""
    return int((value + 4) // 5) * 5

@router.post("/price", response_model=List[PredictionResponse])
async def predict(request: PredictionRequest):
    # Fetch data from Azure Blob Storage
    try:
        df = fetch_data_from_blob()
    except HTTPException as e:
        raise e

    # Extract columns and data from the request
    columns = request.input_data.columns
    input_data = request.input_data.data
    input_df = pd.DataFrame(data=input_data, columns=columns)

    # Prepare and send requests to the Azure ML endpoint
    results = []
    certifications = df[['certificate', 'certificate_name']]
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for _, row in certifications.iterrows():
            cert = row['certificate']
            cert_name = row['certificate_name']
            input_df['certificate'] = cert
            
            # Prepare the data in the updated AzureML input format
            azure_input_data = {
                "input_data": {
                    "columns": ["certificate", "lang_id"],
                    "data": input_df[["certificate", "lang_id"]].values.tolist(),
                    "index": request.input_data.index
                }
            }
            tasks.append(make_request(session, azure_input_data))

        # Execute the requests concurrently and collect responses
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                print(f"Error processing certification {certifications.iloc[i]['certificate']}: {response}")
                continue
            cert = certifications.iloc[i]['certificate']
            cert_name = certifications.iloc[i]['certificate_name']
            for pred in response:
                rounded_pred = round_to_nearest_five(pred)
                results.append(PredictionResponse(certificate=cert, certificate_name=cert_name, predicted_rate=rounded_pred))

    return results

# Replace with your actual Azure endpoint and bearer token
AZURE_ENDPOINT_Time = "https://moli-ai-dev-ws3-ml-izgzg.westus3.inference.ml.azure.com/score"
BEARER_TOKEN_Time = "WPqNLpF7kRu3QMoT0Sg5c7Jm3GpbElIl"
 
@router.post("/time")
async def predict(request: PredictionRequest):
   
    start_time = time.time()
    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN_Time}",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(AZURE_ENDPOINT_Time, json=request.dict(), headers=headers)
        response.raise_for_status()
        prediction = response.json()
           
        # Assuming the prediction result is a list with a single value
        prediction_value = prediction[0]
        end_time = time.time()
        print(f"Total time taken: {end_time - start_time} seconds")
        if prediction_value == 1:
            return {"Time": "Above 12 hours"}
        else:
            return {"Time": "Below 12 hours"}