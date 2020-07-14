import os
from os.path import join
import requests
import json

CHEF_DIR = os.path.dirname(os.path.realpath(__file__))
print(CHEF_DIR)

DATA_DIR = os.path.join(CHEF_DIR, 'chefdata')
print(DATA_DIR)
TREES_DATA_DIR = os.path.join(DATA_DIR, 'trees')
print(TREES_DATA_DIR)


PRADIGI_DOMAIN = 'prathamopenschool.org'
FULL_DOMAIN_URL = 'https://' + PRADIGI_DOMAIN
PAGED_TOPICS_ENDPOINT = FULL_DOMAIN_URL + '/api/catalog/PagedTopics'
PAGED_CONTENTS_ENDPOINT = FULL_DOMAIN_URL + '/api/catalog/PagedContents'


def hindi_parent_tree():
    topic_response = requests.post(PAGED_TOPICS_ENDPOINT, data={'Page': '1'})
    topics_data = topic_response.json()

    catalog_tree = {
        "kind": "catalog_tree",
        "url": "https://prathamopenschool.org/Catalog",
        "content_id": "PrathamOpenSchool Hindi Content",
        "cont_title": "Pratham PraDigi",
        "cont_thumburl": "chefdata/plogo.jpg",
        "children": [],
    }

    for item in topics_data["items"]:
        if item["content_id"] == "1":
            subtree = get_all_json_of_hindi(item["content_id"])
            catalog_tree['children'].append(subtree)
        else:
            break
    return catalog_tree


def get_all_json_of_hindi(content_id):
    print('Downloading content_id=' + content_id)
    post_data = {'Page': '1', "Id": content_id}
    response = requests.post(PAGED_CONTENTS_ENDPOINT, data=post_data)
    contents_data = response.json()

    # pprint(contents_data)
    node = contents_data['mainItem']

    if node["resource_type"] == "Topic" and node["cont_type"] == "Topic":
        node["kind"] = "Topic"
    elif node["cont_type"] == "Course" and node["resource_type"] == "Topic":
        node["kind"] = "Topic"
    elif node["cont_type"] == "Subject" and node["resource_type"] == "Topic":
        node["kind"] = "Topic"
    elif node["cont_type"] == "Course" and node["resource_type"] == "Topic":
        node["kind"] = "Topic"
    elif node["cont_type"] == "Language" and node["resource_type"] == "Language":
        node["kind"] = "Topic"
    elif node["cont_type"] == "Resource" and node["resource_type"] == "Game":
        node["kind"] = "PrathamZipResource"
    elif node["cont_type"] == "Resource" and node["resource_type"] == "Video":
        node["kind"] = "PrathamVideoResource"
    elif node["cont_type"] == "Resource" and node["resource_type"] == "PDF":
        node["kind"] = "PrathamPdfResource"
    elif node["cont_type"] == "Resource" and node["resource_type"] == "Audio":
        node["kind"] = "PrathamAudioResource"

    node['children'] = []  # this is where we'll append items to build the subtree

    # handle paginated API results
    if contents_data['pager']['totalPages'] > 1:
        # CASE A: obtain all_items by combining info from all pages
        print('On', content_id, 'found multi-page result', contents_data['pager']['totalPages'], 'pages')
        all_items = contents_data['items']  # first page
        total_pages = contents_data['pager']['totalPages']
        for page_num in range(2, total_pages + 1):
            # print('getting page_num', page_num)
            post_data2 = {'Page': page_num, "Id": content_id}
            response2 = requests.post(PAGED_CONTENTS_ENDPOINT, data=post_data2)
            contents_data2 = response2.json()
            all_items.extend(contents_data2['items'])
        print('len(all_items)=', len(all_items))
    else:
        #     CASE B: just a single page of results
        all_items = contents_data['items']

    for item in all_items:
        if item["resource_type"] == "Topic" and item["cont_type"] == "Topic":
            item["kind"] = "Topic"
        elif item["cont_type"] == "Course" and item["resource_type"] == "Topic":
            item["kind"] = "Topic"
        elif item["cont_type"] == "Subject" and item["resource_type"] == "Topic":
            item["kind"] = "Topic"
        elif item["cont_type"] == "Course" and item["resource_type"] == "Topic":
            item["kind"] = "Topic"
        elif item["cont_type"] == "Language" and item["resource_type"] == "Language":
            item["kind"] = "Topic"
        elif item["cont_type"] == "Resource" and item["resource_type"] == "Game":
            item["kind"] = "PrathamZipResource"
        elif item["cont_type"] == "Resource" and item["resource_type"] == "Video":
            item["kind"] = "PrathamVideoResource"
        elif item["cont_type"] == "Resource" and item["resource_type"] == "PDF":
            item["kind"] = "PrathamPdfResource"
        elif item["cont_type"] == "Resource" and item["resource_type"] == "Audio":
            item["kind"] = "PrathamAudioResource"
        if item["cont_type"] == "Topic":
            subtree = get_all_json_of_hindi(item['content_id'])
            node['children'].append(subtree)
        else:
            # must be a Resource item, just add it to children
            node['children'].append(item)

    return node


# Obtain the channel tree information by making POST requests to
# /api/catalog/PagedContents recursively to obtain all the content info
catalog_tree = hindi_parent_tree()

# save it to a file for further processing
with open(join(TREES_DATA_DIR, 'pradigi_hindi_web_resource_tree.json'), 'w') as jsonf:
    json.dump(catalog_tree, jsonf, indent=2, ensure_ascii=False)

