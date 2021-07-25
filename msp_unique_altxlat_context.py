import xml.etree.ElementTree as ET
from io import StringIO, BytesIO
from lxml import etree
from tabulate import tabulate
import hashlib
import pprint
from translate.storage.tmx import tmxfile
import sys


# ======== CONSTANTS ============

USE_FILENAME = True
USE_REPETITION_POSITION = True


# ======== FUNCTIONS ============

def create_hash(*match_props):
    """ Creates hash value of a tuple including details such as the segment's source text and
    anything else (prev, next, rpos, etc.) """
    fingerprint = hashlib.md5()
    # fingerprint is a md5 HASH object
    if isinstance(match_props, tuple):
        for p in match_props:
            fingerprint.update(str(p).encode())
        hash_value = fingerprint.hexdigest()
        return hash_value
    else:
        print("The input to the create_hash function must be a tuple.")
        return None


def get_prev(lines, index):
    if index - 1 < 0:
        return None
    else:
        return lines[index-1]


def get_next(lines, index):
    if index + 1 > len(lines) - 1:
        return None
    else:
        return lines[index+1]


def get_translations(fname):
    default_translations = {}
    alternative_translations = {}
    tree = ET.parse(fname)
    root = tree.getroot()
    tus = root.iter('tu')
    for tu in tus:
        context = []
        for child in list(tu):
            # ET.dump(child)
            if child.tag == 'tuv' and child.attrib['lang'] == 'en':
                seg = list(child)[0].text
                source_text = seg
            if child.tag == 'tuv' and child.attrib['lang'] == 'el':
                seg = list(child)[0].text
                target_text = seg
            if child.tag == 'prop' and child.attrib['type'] == 'prev':
                context.append(child.text)
            if child.tag == 'prop' and child.attrib['type'] == 'next':
                context.append(child.text)
            if child.tag == 'prop' and child.attrib['type'] == 'file' and USE_FILENAME:
                context.append(child.text)
            if child.tag == 'prop' and child.attrib['type'] == 'rpos' and USE_REPETITION_POSITION:
                context.append(int(child.text))

        if context:
            search_key = create_hash((source_text,) + tuple(context))
            alternative_translations[search_key] = target_text
        else:
            search_key = create_hash(tuple([source_text]))
            default_translations[search_key] = target_text

    return alternative_translations, default_translations


def add_positions_to_segments(list_of_strings):
    """ Assigns to each segment string:
        - its position within the extracted list of segments
        - its posibion within its group of repetitions (if any)
        Unique (not repeated) segments are the only members of a group of repetitions
        of size 1, so their position with their group of repetitions will always be 1. """

    segments_with_positions = []
    repetition_counter = {}

    for seg_str in list_of_strings:
        if seg_str in repetition_counter:
            # print("The string has been counted")
            repetition_counter[seg_str] += 1
        else:
            # print("The string is counted for the first time")
            repetition_counter[seg_str] = 1

        # tuple
        segment_with_positions = seg_str, repetition_counter[seg_str],
        segments_with_positions.append(segment_with_positions)

    return segments_with_positions


def print_tabular(units):
    reversed_units = [list(reversed(u)) for u in units]
    print(tabulate(reversed_units, headers=[
          "Seg. #", "Rep. pos.", "Source text", "Translation"]))


def get_context(index, lines, file=None):
    prev_segm = get_prev(lines, index)
    next_segm = get_next(lines, index)
    if file:
        return file, prev_segm, next_segm
    else:
        return prev_segm, next_segm


def search_for_matches(search_key, match_type):
    project_save = 'project_save_en-el_02.tmx'
    if match_type == 'default':
        matches = get_translations(project_save)[1]
    elif match_type == 'alternative':
        matches = get_translations(project_save)[0]
    if search_key in matches:
        return matches[search_key]


def search_for_exact_match(search_key, match_type):
    project_save = 'project_save_en-el_02.tmx'
    if match_type == 'alternative':
        matches = get_translations(project_save)[0]
    elif match_type == 'default':
        matches = get_translations(project_save)[1]
    if search_key in matches:
        return matches[search_key]  # can only be one match


# ======== BUSINESS LOGIC ============

source_file = 'text1.txt'
with open(source_file) as f:
    lines = [line.strip() for line in f.readlines() if line != '\n']

enriched_units = add_positions_to_segments(lines)
indexed_units = [list(u + (i+1,))
                 for i, u in enumerate(enriched_units)]
# print(tabulate(indexed_units, headers=["Seg. #", "Rep. pos.", "Segment"]))

print("Source text:")
print()
print_tabular(indexed_units)


print("===================================================================================================================")
print("Looking for default translations only (will ignore alternative translations):")
print()

translated_units = []
for index, unit in enumerate(enriched_units):
    source_text = unit[0]
    try:
        assert enriched_units[index] == unit
    except AssertionError as e:
        print("Assertion failed: " + e)

    if source_text == "Petitions to the European Parliament":
        search_key = create_hash(tuple([source_text]))
        target_text = search_for_exact_match(search_key, match_type="default")
        translated_unit = (target_text,) + enriched_units[index] + (index,)
        translated_units.append(translated_unit)

print_tabular(translated_units)

print("===================================================================================================================")
print("Normal behaviour: looking for alternative translations (only use default if no alternative found):")
print()

translated_units = []
for index, unit in enumerate(enriched_units):
    # print(index, unit)
    # print(enriched_units[index])
    source_text = unit[0]
    rpos = unit[1]
    try:
        assert enriched_units[index] == unit
    except AssertionError as e:
        print(e)

    if source_text == "Petitions to the European Parliament":
        context = get_context(index, lines, source_file)

        str_search_key = create_hash(tuple([source_text]))
        if USE_REPETITION_POSITION:
            ice_search_key = create_hash((source_text,) + context + (rpos,))
        else:
            ice_search_key = create_hash((source_text,) + context)

        if search_for_exact_match(ice_search_key, match_type="alternative"):
            target_text = search_for_exact_match(
                ice_search_key, match_type="alternative")
        elif search_for_exact_match(str_search_key, match_type="default"):
            target_text = search_for_exact_match(
                str_search_key, match_type="default")
        else:
            target_text = None

        translated_unit = (target_text,) + enriched_units[index] + (index,)
        translated_units.append(translated_unit)

print_tabular(translated_units)
print("======================================================================================================")
