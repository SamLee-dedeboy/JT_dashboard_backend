import glob
from io import StringIO
from fastapi import APIRouter
import json
from functools import cmp_to_key
import copy
from operator import itemgetter
from collections import defaultdict
import collections
from . import FlowDBUtils
import os

dirname = os.path.dirname(__file__)
relative_path = lambda filename: os.path.join(dirname, "..", filename)

router = APIRouter()

# metadata_path = relative_path("metadata/tmp/")
metadata_path = relative_path("flow_data/metadata/")
# backup can be found under '../data/json/chunked_summary/'
# data_path = relative_path("data/tmp/chunked_summary/")
data_path = relative_path("flow_data/chunked_summary/")


@router.get("/test/")
async def test():
    return "Hello CaDelta"


@router.get("/data/")
async def get_data():
    res = reload_data(metadata_path, data_path)
    return res


def reload_data(metadata_path, data_path):
    metadata = FlowDBUtils.local.read_metadata(metadata_path)
    participant_metadata_dict = FlowDBUtils.local.read_participant_metadata(data_path)
    (
        background,
        drivers_of_change,
        future_management,
        decision_making,
        participant_metadata,
    ) = FlowDBUtils.local.read_data(data_path, participant_metadata_dict)
    participant_data, category_dict = FlowDBUtils.post_process.prepareParticipantData(
        background, drivers_of_change, future_management, decision_making
    )
    participant_similarities = FlowDBUtils.post_process.calculateSimilarity(
        participant_data
    )
    return {
        "background": background,
        "drivers_of_change": drivers_of_change,
        "future_management": future_management,
        "decision_making": decision_making,
        "metadata": metadata,
        "participant_data": participant_data,
        "category_dict": category_dict,
        "similarities": participant_similarities,
    }
