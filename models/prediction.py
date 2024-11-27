from pydantic import BaseModel
from typing import List

# Define the input data model
class InputData(BaseModel):
    columns: List[str]
    data: List[List[float]]
    index: List[int]
 
class PredictionRequest(BaseModel):
    input_data: InputData
 
class PredictionResponse(BaseModel):
    certificate: int
    certificate_name: str
    predicted_rate: float