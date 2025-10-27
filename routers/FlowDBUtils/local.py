import re
import json
import glob
import os
def save_json(data, filepath):
    with open(filepath, 'w', encoding='utf-8') as fp:
        json.dump(data, fp, indent=4)

def reverse_index(dict_of_list, post_process_func):
    res = {}
    for group_label, elements in dict_of_list.items():
        for element in elements:
            res[post_process_func(element)] = post_process_func(group_label)
    return res

def read_metadata(metadata_path):
    # metadata for categories
    factor_categories = json.load(open(metadata_path + 'factor_categories.json'))
    stakeholder_categories = json.load(open(metadata_path + 'stakeholder_group_categories.json'))
    strategy_categories = json.load(open(metadata_path + 'strategy_categories.json'))
    participant_categories = json.load(open(metadata_path + 'participant_categories.json'))
    metadata = {
        'participant_categories': participant_categories,
        'strategy_categories': strategy_categories,
        'factor_categories': factor_categories,
        'represented_categories': stakeholder_categories['represented'],
        'not_represented_categories': stakeholder_categories['not_represented'],
        'others_to_include_categories': stakeholder_categories['others_to_include']
    }
    # factor_category_dict = reverse_index(factor_categories, post_process_func=lambda x: x.lower())
    # strategy_category_dict = reverse_index(strategy_categories, post_process_func=lambda x: x.lower())
    # represented_category_dict = reverse_index(stakeholder_categories['represented'], post_process_func=lambda x: x.lower())
    # not_represented_category_dict = reverse_index(stakeholder_categories['not_represented'], post_process_func=lambda x: x.lower())
    # others_category_dict = reverse_index(stakeholder_categories['others_to_include'], post_process_func=lambda x: x.lower())
    # return metadata, factor_category_dict, strategy_category_dict, represented_category_dict, not_represented_category_dict, others_category_dict
    return metadata

def read_data(data_path, participant_metadata_dict):
    # data_path = "../data/json/chunked_summary/"
    # metadata of each participant
    # interview
    background = []  
    drivers_of_change = []
    future_management = [] 
    decision_making = [] 

    for interview_file in glob.glob(data_path + "*.json"):
        interview_data = json.load(open(interview_file))
        participant_id = interview_data[0]['id'].split("_")[0]
        participant = os.path.basename(interview_file).replace(".json", "")
        # add id to background summary
        interview_data[0]['summary']['id'] = participant_id
        interview_data[0]['summary']['categories'] = participant_metadata_dict[participant]['Categories']
        background.append(interview_data[0])

        # add id to drivers summary
        interview_data[1]['summary']['id'] = participant_id
        # keep top three
        interview_data[1]['summary']['factors'] = interview_data[1]['summary']['factors']
        drivers_of_change.append(interview_data[1])

        # add id to management summary
        interview_data[2]['summary']['id'] = participant_id
        future_management.append(interview_data[2])

        # add id to decision making summary
        interview_data[3]['summary']['id'] = participant_id
        # lower case fair/unfair
        interview_data[3]['summary']['Is the process fair'] = interview_data[3]['summary']['Is the process fair'].lower()
        decision_making.append(interview_data[3])
    return background, drivers_of_change, future_management, decision_making, participant_metadata_dict

def update_data(data_path, pid, action, section, column, before, before_value, after):
    if section == 'background' and action in ['delete', 'move']:
        filepath = data_path + "metadata/{}.json".format(pid)
        participant_metadata = json.load(open(filepath))
        if action == 'delete':
            participant_metadata['Categories'] = list(filter(lambda x: x != before, participant_metadata['Categories']))
        elif action == 'move':
            participant_metadata['Categories'] = [after if x == before else x for x in participant_metadata['Categories']]
        save_json(participant_metadata, filepath)
    else:
        filepath = data_path + "{}.json".format(pid)
        interview_data = json.load(open(filepath))
        section_index = {
            'background': 0,
            'drivers_of_change': 1,
            'future_management': 2,
            'decision_making': 3
        }
        column_key = {
            'category-': 'relationship to the delta',
            'factor-category-': 'factors',
            'strategy-': 'important salinity management strategies',
            'rect-': 'Is the process fair',
            'represented-': 'Who is represented',
            'not-represented-': 'Who is not represented',
            'others-to-include-': 'What other people to connect with',
        }
        obj_key = {
            'factor-category-': 'factor_name',
            'strategy-': 'strategy',
            'represented-': 'group',
            'not-represented-': 'group',
            'others-to-include-': 'group',
        }
        section_data = interview_data[section_index[section]]['summary']
        obj = section_data[column_key[column]]
        if action == 'edit':
            if type(obj) is list:
                for index, x in enumerate(obj):
                    if x[obj_key[column]] == before:
                        obj[index][obj_key[column]] = after
            elif isinstance(obj, dict):
                obj[obj_key[column]] = after
            else:
                obj = after
            section_data[column_key[column]] = obj
        elif action == 'add':
            assert(type(obj) is list)
            obj.append({
                obj_key[column]: after,
                'category': before
            })
            section_data[column_key[column]] = obj
        elif action == 'delete': 
            assert(type(obj) is list)
            obj = list(filter(lambda x: x[obj_key[column]] != before, obj))
            section_data[column_key[column]] = obj
        elif action == 'move':
            if type(obj) is list:
                for index, x in enumerate(obj):
                    if x[obj_key[column]] == before_value:
                        obj[index]['category'] = after
            elif isinstance(obj, dict): 
                obj['category'] = after
            else:
                assert(column == 'rect-')
                obj = after
            section_data[column_key[column]] = obj
        interview_data[section_index[section]]['summary'] = section_data
        save_json(interview_data, filepath)
    return

def update_metadata(metadata_path, action, section, column, value):
    file_name = {
        'background': 'participant_categories.json',
        'drivers_of_change': 'factor_categories.json',
        'future_management': 'strategy_categories.json',
        'decision_making': 'stakeholder_group_categories.json'
    }
    column_name_dict = {
        'represented-': 'represented',
        'not-represented-': 'not_represented',
        'others-to-include-': 'others_to_include'
    }
    metadata = json.load(open(metadata_path + file_name[section]))
    if section == "decision_making":
        column_obj = metadata[column_name_dict[column]]
        if action == 'add':
            column_obj.append(value)
        elif action == 'remove':
            column_obj = list(filter(lambda x: x != value, column_obj))
        metadata[column_name_dict[column]] = column_obj
    else:
        if action == 'add':
            metadata.append(value)
        elif action == 'remove':
            metadata = list(filter(lambda x: x != value, metadata))
    save_json(metadata, metadata_path + file_name[section])

    return

def read_participant_metadata(data_path):
    participant_metadata_dict = {}
    for metadata_file in glob.glob(data_path + "metadata/*.json"):
        p_metadata = json.load(open(metadata_file))
        participant = p_metadata['Interviewee']
        participant_metadata_dict[participant] = p_metadata
    return participant_metadata_dict
def clean_up_commas(text):
    # replace ',' inside parenthesis with 'and'
    pattern = r'\(([^)]*)\)'
    text = re.sub(pattern, lambda match: match.group(0).replace(',', ' and'), text)
    return text