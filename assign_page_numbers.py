#-*- coding:utf8 -*-
import numpy
from scipy.misc import imread
from matplotlib import pyplot as plt

from PIL import Image
from PIL import ImageDraw

import re
import os
from subprocess import call
import sys

def block_dump2block(dump):
    x1, x2, y1, y2 = dump.split(",")
    return ((int(x1), int(x2)), (int(y1), int(y2)),)

def upload_page_data(fname):
    paragraphs = []
    letters = []
    images = []
    formulas = []  
    block2text = {}  
    text = open(fname).read().decode("utf8").strip()
    for line in text.split("\n"):
        chunks = line.split("\t")
        if chunks[0] == "paragraph" and chunks[1].strip():
            lines = [block_dump2block(item) for item in chunks[1].split(" ")]
            paragraphs += [lines]
        elif chunks[0] == "letters" and chunks[1].strip():
            letters = [block_dump2block(item) for item in chunks[1].strip().split(" ")]
        elif chunks[0] == "formulas" and chunks[1].strip():
            formulas = [block_dump2block(item) for item in chunks[1].split(" ")]          
        elif chunks[0] == "images" and chunks[1].strip():
            images = [block_dump2block(item) for item in chunks[1].split(" ")]
        elif chunks[0] == "text" and chunks[1].strip():
            coords = block_dump2block(chunks[1])
            text = chunks[2]
            block2text[coords] = text
        else:
            print "FUCKUP", chunks[0]
    return paragraphs, letters, formulas, images, block2text



#filenames must have a right order
def assign_page_numbers(files, blocks_directory):
    def longest_increasing_subsequence(d):
        l = []
        for i in range(len(d)):
            l.append(max([l[j] for j in range(i) if l[j][-1] < d[i]] or [[]], key=len) 
                      + [d[i]])
        return max(l, key=len)
    def extrapolate_and_assign_scores(scores, files, first, last, first_page_number):
        interval_size = last - first + 1
        if interval_size < 5: #remove shit
            return
        first_file_page_number = first_page_number - first
        if first_file_page_number > 0:
            for file_index in xrange(len(files)):
                page_number_assumpt = first_file_page_number + file_index
                distance = (file_index < first or file_index > last) and max(start - file_index, file_index - last) or 0
                score = (last - start) * (0.5 ** distance)
                scores[file_index].setdefault(page_number_assumpt, 0)  
                scores[file_index][page_number_assumpt] += score
    files.sort()
    MAX_PAGES_COUNT = len(files) * 1.5
    numbers_on_pages = []
    for file_index in xrange(len(files)):
        fname = files[file_index]
        paragraphs, letters, formulas, images, block2text = upload_page_data(blocks_directory + fname)
        
        by_height = [(coords[0][0], text) for coords, text in block2text.items()]
        by_height.sort()
        page_numbers = []
        for _, text in by_height[:3] + by_height[-3:]:
            page_numbers += [int(number) for number in re.findall("[1-9][0-9]*", text) if int(number) < MAX_PAGES_COUNT] 
        for number in page_numbers:
            numbers_on_pages += [(number, file_index)]
    
    subsequence = longest_increasing_subsequence(numbers_on_pages)
    if 1:
        to_drop = []
        for index in xrange(len(subsequence) - 1):
            if subsequence[index][1] == subsequence[index + 1][1]:
                to_drop += [index]
        to_drop = set(to_drop)
        subsequence = [subsequence[index] for index in xrange(len(subsequence)) if not index in to_drop]
    scores = [{} for _ in xrange(len(files))]
    start = 0
    for end in xrange(1, len(subsequence)):
        if subsequence[end][0] - subsequence[end - 1][0] > 1:
            anchor_page_number = subsequence[start][0]
            anchor_file_index = subsequence[start][1]
            extrapolate_and_assign_scores(scores, files, subsequence[start][1], subsequence[end - 1][1], subsequence[start][0])
            start = end
    extrapolate_and_assign_scores(scores, files, subsequence[start][1], len(files) - 1, subsequence[start][0])
    assigned_page_numbers = {}
    assigned_page_numbers_as_list = []
    for file_index in xrange(len(files)):
        assigned_page_number = max([(score, page_number) for page_number, score in scores[file_index].items()])[1]
        assigned_page_numbers[files[file_index]] = assigned_page_number
        assigned_page_numbers_as_list += [(file_index, files[file_index], assigned_page_number)]
    gaps = []
    for file_index in xrange(len(files) - 1):
        delta = assigned_page_numbers[files[file_index + 1]] - assigned_page_numbers[files[file_index]]
        if delta != 1:
            gaps += [ (files[file_index], files[file_index + 1], delta)]
    return assigned_page_numbers, gaps
    







    