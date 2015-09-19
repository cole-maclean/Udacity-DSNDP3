import xml.etree.cElementTree as ET
import pprint
import re
import codecs
import json
import math
import numpy as np
import matplotlib.pyplot as plt
import heapq
from pymongo import MongoClient

def get_element(osm_file, tags=('node', 'way', 'relation')): 
    """Yield element if it is the right type of tag

    Reference:
    http://stackoverflow.com/questions/3095434/inserting-newlines-in-xml-file-generated-via-xml-etree-elementtree-in-python
    """
    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()

def OSM_sample(sampling_size):
    with open(SAMPLE_FILE, 'wb') as output:
        output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        output.write('<osm>\n  ')

        # Write every sampleing_size-th top level element
        for i, element in enumerate(get_element(OSM_FILE)):
            if i % sampling_size == 0:
                output.write(ET.tostring(element, encoding='utf-8'))
        output.write('</osm>')

#Utility data structures for nested dicts/lists
TOP_LEVEL_DATA = ['id','visible']
CREATED = [ "version", "changeset", "timestamp", "user", "uid"]
POS=['lat','lon']

#This function returns a data dictionary by parsing the data from each key of an elements attributes
#listed in the data_list argument
def data_dict(elem_attribs,data_list):
    return {data_elem:elem_attribs[data_elem] for data_elem in data_list if data_elem in elem_attribs.keys()} 

def extract_top_level_data(element): # this function extract top level data from the elements attributes
    node = data_dict(element.attrib,TOP_LEVEL_DATA)
    created_dict = data_dict(element.attrib,CREATED)
    if created_dict:
        node['created'] = created_dict
    pos_list = [float(element.attrib[pos_data]) for pos_data in POS if pos_data in element.attrib.keys()] #extracts lat/lon data in list and converts to float
    if pos_list:
        node['pos'] = pos_list
    node['type'] = element.tag
    return node
    
def shape_element(element): #This function extracts the top level and key/value pairs from a node or ways tag element
    node_refs = []
    if element.tag == "node" or element.tag == "way":
       node = extract_top_level_data(element)
       for child in element.iter():
            if child.tag == 'tag':
                if child.attrib['k'] == "addr:housenumber": #Standardize addr:housenumber to list of house numbers in attribute
                    house_num = child.attrib['v']
                    try:
                        if "-" in house_num:
                            num_split = house_num.split("-")
                            node["addr:housenumber"] = [str(num) for num in range(int(num_split[0]),int(num_split[1]))]
                        elif "," in house_num:
                            num_split = house_num.split(",")
                            node["addr:housenumber"] = [num for num in num_split]
                        else:
                            node["addr:housenumber"] = [house_num]
                    except:
                        node["addr:housenumber"] = [house_num]
                else:
                    node[child.attrib['k']] = child.attrib['v']
       return node
    return None

def OSM_file_mongo_update(file_in): #Insert each shaped element into MongoDB OSM collection
    for _, element in ET.iterparse(file_in):
        el = shape_element(element)
        if el:
            osm.update(el,el,{"upsert":"True"})
    return osm.find_one()

def connect_OSM_collection():
    client = MongoClient('mongodb://localhost:27017/')
    db = client.OSMdb
    osm = db.OSM
    return osm