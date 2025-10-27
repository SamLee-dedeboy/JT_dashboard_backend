from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import os
import json

router = APIRouter()

dirname = os.path.dirname(__file__)
server_path = lambda filename: os.path.join(dirname, "..", filename)


class CodeRequest(BaseModel):
    code_name: str


@router.get("/test/")
def test():
    return "Hello Sunburst"


@router.get("/data/")
async def get_all_sunburst_data():
    """
    Get all sunburst data files at once.

    Returns:
        Dictionary with filename as key and data as value
    """
    try:
        sunburst_dir = server_path(os.path.join("sunburst_data", "sunburst"))

        if not os.path.exists(sunburst_dir):
            raise HTTPException(
                status_code=404, detail="Sunburst data directory not found"
            )

        # Get all JSON files in the directory
        files = [f for f in os.listdir(sunburst_dir) if f.endswith(".json")]

        all_data = {}
        for filename in files:
            file_path = os.path.join(sunburst_dir, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    all_data[filename] = json.load(file)
            except json.JSONDecodeError:
                all_data[filename] = {"error": f"Invalid JSON in file '{filename}'"}
            except Exception as e:
                all_data[filename] = {
                    "error": f"Error reading file '{filename}': {str(e)}"
                }

        return all_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading data: {str(e)}")


@router.post("/code/")
async def get_code_definition(request: CodeRequest):
    """
    Get a specific code definition from all_codes.json.

    Args:
        request: CodeRequest containing the code_name to retrieve

    Returns:
        Dictionary containing the code definition
    """
    try:
        code_name = request.code_name.replace("(general)", "").strip()

        # Path to all_codes.json in mm_data directory
        all_codes_path = server_path(
            os.path.join("sunburst_data", "sunburst", "all_codes.json")
        )

        if not os.path.exists(all_codes_path):
            raise HTTPException(status_code=404, detail="all_codes.json file not found")

        # Load the codes data
        with open(all_codes_path, "r", encoding="utf-8") as file:
            codes_data = json.load(file)

        # Find the code by name
        for code in codes_data:
            if code.get("name") == code_name:
                return code

        # If code not found
        raise HTTPException(status_code=404, detail=f"Code '{code_name}' not found")

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500, detail="Invalid JSON in all_codes.json file"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error loading code data: {str(e)}"
        )
