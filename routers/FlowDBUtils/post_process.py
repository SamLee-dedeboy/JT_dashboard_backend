import re
from collections import defaultdict
import collections
import numpy as np
def prepareParticipantData(background, drivers_of_change, future_management, decision_making):
    participant_data = {}
    category_dict = defaultdict(list)
    # init
    for participant_summary in background:
        participant_id = participant_summary['id'].split("_")[0]
        participant_data[participant_id] = {
            "id": None,
            "categories": None,
            "factors": None,
            "strategies": None,
            "fairness": None,
            "represented_groups": None,
            "not_represented_groups": None,
            "others_to_include": None,
            "conversations": {
                "background": None,
                "drivers_of_change": None,
                "future_management": None,
                "decision_making": None,
            },
            "summaries": {
                "background": None,
                "drivers_of_change": None,
                "future_management": None,
                "decision_making": None,
            }
        }
    # background
    for participant_background in background:
        participant_id = participant_background['id'].split("_")[0]
        # print("id", participant_id)
        # age = participant_background['summary']['age']
        categories = participant_background['summary']['categories']
        # living_space = participant_background['summary']['living place']
        # relationship = participant_background['summary']['relationship to the delta']
        # summary = participant_background['summary']['summary']
        participant_data[participant_id]["id"] = participant_id
        participant_data[participant_id]["categories"] = categories
        participant_data[participant_id]['conversations']['background'] = participant_background['conversation']
        participant_data[participant_id]['summaries']['background'] = participant_background['summary']['summary']
    # drivers of change    
    for participant_drivers_of_change in drivers_of_change:
        participant_id = participant_drivers_of_change['id'].split("_")[0]
        factors = participant_drivers_of_change['summary']['factors']
        participant_data[participant_id]["factors"] = list(map(lambda factor: factor['category'], factors))
        # print("In for loop")
        participant_data[participant_id]['conversations']['drivers_of_change'] = participant_drivers_of_change['conversation']
        participant_data[participant_id]['summaries']['drivers_of_change'] = participant_drivers_of_change['summary']['summary']
    # future management and design options
    for participant_future_management in future_management:
        participant_id = participant_future_management['id'].split("_")[0]
        strategies = participant_future_management['summary']['important salinity management strategies']
        strategy_categories = list(map(lambda strategy: strategy['category'], strategies))
        participant_data[participant_id]["strategies"] = strategy_categories
        participant_data[participant_id]['conversations']['future_management'] = participant_future_management['conversation']
        participant_data[participant_id]['summaries']['future_management'] = participant_future_management['summary']['summary']
        # strategies = flatten([participant_future_management['summary']['most important salinity management strategy']])
        # summary = participant_future_management['summary']['summary']
    # decision making
    for participant_decision_making in decision_making:
        participant_id = participant_decision_making['id'].split("_")[0]
        fairness = participant_decision_making['summary']['Is the process fair']
        # reason = [participant_decision_making['summary']['Reason']]
        other_people = participant_decision_making['summary']['What other people to connect with']
        represented = participant_decision_making['summary']['Who is represented']
        not_represented = participant_decision_making['summary']['Who is not represented']
        # comments = [participant_decision_making['summary']['comments on the decision-making in the Delta']]
        # summary = participant_decision_making['summary']['summary']
        participant_data[participant_id]["fairness"] = fairness
        participant_data[participant_id]["represented_groups"] = list(map(lambda people: people['category'], represented))
        participant_data[participant_id]["not_represented_groups"] = list(map(lambda people: people['category'], not_represented))
        participant_data[participant_id]["others_to_include"] = list(map(lambda people: people['category'], other_people))
        participant_data[participant_id]['conversations']['decision_making'] = participant_decision_making['conversation']
        participant_data[participant_id]['summaries']['decision_making'] = participant_decision_making['summary']['summary']

    category_metadata_list = [
        {
            "key": "categories",
            "isList": True,
        },
        {
            "key": "factors",
            "isList": True,
        },
        {
            "key": "strategies",
            "isList": True,
        },
        {
            "key": "fairness",
            "isList": False,
        },
        {
            "key": "represented_groups",
            "isList": True,
        },
        {
            "key": "not_represented_groups",
            "isList": True,
        },
        {
            "key": "others_to_include",
            "isList": True,
        },
    ]
    for pid, data in participant_data.items():
        for category_metadata in category_metadata_list:
            key = category_metadata["key"]
            isList = category_metadata["isList"]
            if isList:
                for category in data[key]:
                    category_dict[key + "-" + category].append(pid)
            else:
                category_dict[key + "-" + data[key]].append(pid)
    return participant_data, category_dict

def calculateSimilarity(participant_data):
    features = ['categories', 'factors', 'strategies', 'fairness', 'represented_groups', 'not_represented_groups', 'others_to_include']
    sim_matrix = defaultdict(dict)

    for i1, datum1 in enumerate(list(participant_data.values())):
        pid1 = datum1['id']
        for i2, datum2 in enumerate(list(participant_data.values())):
            pid2 = datum2['id']
            feature_sims = np.array([jaccard_similarity(list(datum1[key]), list(datum2[key])) for key in features])
            overall_sim = np.mean(feature_sims)
            sim_matrix[pid1][pid2] = overall_sim

    return sim_matrix

def jaccard_similarity(list1: list, list2: list):
    if not isinstance(list1, collections.abc.Sequence):
        return 1 if list1 == list2 else 0
    list1 = list(set(list1))
    list2 = list(set(list2))
    intersection = len(list(set(list1).intersection(list2)))
    union = (len(list1) + len(list2)) - intersection
    if union == 0: return 0
    return float(intersection) / union


def flatten(l):
    return [item for sublist in l for item in sublist]
def reverse_index(dict_of_list, post_process_func):
    res = {}
    for group_label, elements in dict_of_list.items():
        for element in elements:
            res[post_process_func(element)] = post_process_func(group_label)
    return res
