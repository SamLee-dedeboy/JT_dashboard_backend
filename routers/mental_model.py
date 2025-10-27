from fastapi import APIRouter
import os
import json
import glob
from collections import defaultdict
from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Any

router = APIRouter()

dirname = os.path.dirname(__file__)
server_path = lambda filename: os.path.join(dirname, "..", filename)


@router.get("/codebook/")
def get_codebook():
    codebook = json.load(
        open(server_path("mm_data/all_codes.json"), "r", encoding="utf-8")
    )
    return codebook


@router.get("/codebook/parent_tsne/")
def get_codebook_parent_tsne():
    parent_code_tsne = json.load(
        open(server_path("mm_data/code_tsne_1d.json"), "r", encoding="utf-8")
    )
    return parent_code_tsne


@router.get("/mental_model/exhibition_individual/")
def get_exhibition_individual():
    exhibition_MMs = []
    codes = json.load(
        open(server_path("mm_data/all_codes.json"), "r", encoding="utf-8")
    )
    parent_code_dict = {code["name"]: code["parent"] for code in codes}
    code_type_dict = {code["name"]: code["type"] for code in codes}
    all_codes = [code["name"] for code in codes]
    participants = []
    for participant_MM_file in glob.glob(server_path("mm_data/MMs/*.json")):
        with open(participant_MM_file, "r") as f:
            participant_MM = json.load(f)
            participant_MM = list(
                filter(lambda x: x["code_name"] in all_codes, participant_MM)
            )
            participant_MM = list(filter(lambda x: x["mentioned"], participant_MM))
            participant_MM = list(filter(lambda x: x["impact"], participant_MM))
            participant_MM = list(
                filter(
                    lambda x: x["logical_connection"] == "Good"
                    and x["significance"] == "Good"
                    and x["relevance"] == "Good"
                    and x["inference"] == "Good"
                    and x["interpretation"] == "Good"
                    and x["preciseness"] == "Good",
                    participant_MM,
                )
            )
            participant_MM = [
                {
                    "node": mm["code_name"],
                    "parent": (
                        parent_code_dict[mm["code_name"]]
                        if parent_code_dict[mm["code_name"]] != "N/A"
                        else mm["code_name"]
                    ),
                    "classification": code_type_dict.get(mm["code_name"], "Unknown"),
                }
                for mm in participant_MM
            ]
        exhibition_MMs.append(participant_MM)
        participants.append(participant_MM_file.split("/")[-1].split(".")[0])

    return {"participants": participants, "mental_models": exhibition_MMs}


# Aggregated mental model results from all exhibitions
@router.get("/mental_model/exhibition/")
def get_exhibition_MM():
    all_MMs = defaultdict(list)
    code_book = json.load(open(server_path("mm_data/all_codes.json")))
    all_codes = [code["name"] for code in code_book]
    parent_code_dict = {}  # from code to parent code
    for code in code_book:
        code_name = code["name"]
        parent_code = code["parent"]
        if parent_code != "N/A":
            parent_code_dict[code_name] = parent_code
        else:
            parent_code_dict[code_name] = code_name
    for participant_MM_file in glob.glob(server_path("mm_data/exhibition/*.json")):
        participant_id = participant_MM_file.split("/")[-1].split(".")[0]
        participant_MM = json.load(open(participant_MM_file))
        participant_MM = list(
            filter(lambda x: x["code_name"] in all_codes, participant_MM)
        )
        code_names = set([c["code_name"] for c in participant_MM])
        for c in code_names:
            if c == "Local surface water supply":
                continue
            all_MMs[c].append(participant_id)
    return all_MMs


# Aggregated mental model results from all interviews
@router.get("/mental_model/interview/")
def get_interview_Mm():
    all_MMs = defaultdict(list)
    code_book = json.load(open(server_path("mm_data/all_codes.json")))
    all_codes = [code["name"] for code in code_book]
    parent_code_dict = {}  # from code to parent code
    for code in code_book:
        code_name = code["name"]
        parent_code = code["parent"]
        if parent_code != "N/A":
            parent_code_dict[code_name] = parent_code
        else:
            parent_code_dict[code_name] = code_name
    for participant_MM_file in glob.glob(server_path("mm_data/MMs/*.json")):
        participant_id = participant_MM_file.split("/")[-1].split(".")[0]
        participant_MM = json.load(open(participant_MM_file))
        participant_MM = list(
            filter(lambda x: x["code_name"] in all_codes, participant_MM)
        )
        participant_MM = list(filter(lambda x: x["mentioned"], participant_MM))
        participant_MM = list(filter(lambda x: x["impact"], participant_MM))
        participant_MM = list(
            filter(
                lambda x: x["logical_connection"] == "Good"
                and x["significance"] == "Good"
                and x["relevance"] == "Good"
                and x["inference"] == "Good"
                and x["interpretation"] == "Good"
                and x["preciseness"] == "Good",
                participant_MM,
            )
        )
        # code_names = set([c["code_name"] for c in participant_MM])
        # code_names = set(
        #     [parent_code_dict[c["code_name"]] for c in participant_MM]
        # )  # keep only the parent code
        code_names = set([c["code_name"] for c in participant_MM])
        for c in code_names:
            # all_MMs[c] += 1
            if c == "Local surface water supply":
                continue
            all_MMs[c].append(participant_id)
    return all_MMs


# Pydantic models for request/response validation
class Factor(BaseModel):
    name: str
    parent: str
    type: str


class Demographics(BaseModel):
    age: str
    deltaEngagement: str
    residence: str


class MentalModelSubmission(BaseModel):
    timestamp: str
    mentalModel: Dict[str, Any]
    demographics: Demographics


@router.post("/submit/")
def submit_mental_model(submission: MentalModelSubmission):
    """
    Submit a mental model with demographic data
    """
    try:
        # Create submissions directory if it doesn't exist
        submissions_dir = server_path("submissions")
        os.makedirs(submissions_dir, exist_ok=True)

        # Generate a unique filename based on timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"submission_{timestamp}.json"
        filepath = os.path.join(submissions_dir, filename)

        # Save the submission data
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(submission.dict(), f, indent=2, ensure_ascii=False)

        return {
            "status": "success",
            "message": "Mental model and demographic data submitted successfully",
            "submission_id": timestamp,
        }

    except Exception as e:
        return {"status": "error", "message": f"Failed to submit data: {str(e)}"}
