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


from fix_grammar import TGrammarCorrector
from fix_grammar import tokenize
from fix_grammar import good_word
from fix_grammar import is_alpha
from gi.overrides.keysyms import paragraph

grammar_corrector = TGrammarCorrector()
freq_dict = set()
for line in open("freq_dict.txt"):
  word = line.decode("utf8").split("\t")[0]
  freq = int(line.decode("utf8").split("\t")[1])
  freq_dict.add(word)

def upload_cuneiform(fname):
    text = open(fname).read().decode("utf8").replace("\n", " ")
    paragraphs_str = [paragraph for paragraph in re.findall("<p.+?<\/p>", text)]
    paragraphs = []
    letters = []
    line2text = {}
    
    PADDING = 2
    for paragraph_str in paragraphs_str:
        paragraph = []
        ocr_lines_str = [line for line in re.findall("<span class='ocr_line.+?<span class='ocr_cinfo'.+?<\/span>", paragraph_str)]
        for line in ocr_lines_str:
            """line"""
            parag_added =  False
            update_line = False
            text = re.findall("<span class='ocr_line.+?>(.+?)<span class='ocr_cinfo'.+?<\/span>", line)[0]
            text = re.subn("</*[a-z]+[^>]*>", "", text)[0]
            coords = [int(item) for item in re.findall("title=\"bbox ([0-9 -]+)\"", line)[0].strip().split()]
            block_y_min, block_x_min, block_y_max, block_x_max = coords
            
            if  block_y_min != block_y_max and not -1 in [block_y_min, block_x_min, block_y_max, block_x_max]:
                #fuckup case
                if 0 in [block_y_min, block_x_min, block_y_max, block_x_max]:
                    update_line = True
                parag_added = True
                paragraph += [ ((block_x_min - PADDING, block_x_max + PADDING), (block_y_min - PADDING, block_y_max + PADDING)) ]
            """letters"""
            coords_str = re.findall("x_bboxes ([0-9 -]+)", line)[0]
            coords = [int(item) for item in coords_str.strip().split()]
            ocr_line = []
            min_x, max_x = 100000, -10000
            min_y, max_y = 100000, -10000
            mins = []
            for coord_index in xrange(0, len(coords), 4):
                block_y_min, block_x_min, block_y_max, block_x_max = coords[coord_index: coord_index + 4]
                if -1 in [block_y_min, block_x_min, block_y_max, block_x_max]:
                    continue
                if 0 in [block_y_min, block_x_min, block_y_max, block_x_max]:
                    continue
                min_x = min(min_x, block_x_min)
                max_x = max(max_x, block_x_max)
                min_y = min(min_y, block_y_min)
                max_y = max(max_y, block_y_max)
                letters += [((block_x_min - PADDING, block_x_max + PADDING), (block_y_min - PADDING, block_y_max + PADDING))]
            if parag_added and update_line:
                paragraph[-1] = ((min_x - PADDING, max_x + PADDING), (min_y - PADDING, max_y + PADDING))
            if parag_added:
                line2text[paragraph[-1]] = text
        if paragraph:
            paragraphs += [paragraph]
    """ sort line by height_min"""
    for parag_index in xrange(len(paragraphs)):
        paragraph = paragraphs[parag_index]
        paragraph = [(line[1][0], line)  for line in paragraph]
        paragraph.sort()
        paragraphs[parag_index] = [line for _, line in paragraph]
    return paragraphs, letters, line2text
    




def build_profile(img, borders, axis):
    profile = numpy.zeros(borders[axis][1] - borders[axis][0])
    counter_axis_length = borders[1 - axis][1] - borders[1 - axis][0]
    if axis:
        for x in xrange(borders[axis][0], borders[axis][1]):
            profile[x - borders[axis][0]] = sum(img[borders[1 - axis][0] : borders[1 - axis][1], x]) / float(counter_axis_length)
    else:
        
        for x in xrange(borders[axis][0], borders[axis][1]):
            profile[x - borders[axis][0]] = sum(img[x, borders[1 - axis][0] : borders[1 - axis][1]]) / float(counter_axis_length)
    return profile


def empty_intervals(profile):
    intervals = []
    start = -1
    for end in xrange(len(profile)):
        if profile[end] > 0:
            if start > -1:
                intervals.append((end - start, start))
                start = -1
        elif start == -1:
            start = end
    if start != -1:
        intervals.append((len(profile) - start, start))
    return intervals


def detect_non_empty_blocks(img, block, final_blocks):
    by_axis = [[], []]
    max_lengths = [-1, -1]
    for axis in xrange(2):
        profile = build_profile(img, block, axis)
        intervals = empty_intervals(profile)
        intervals = [(length, start) for length, start in intervals]
        
        by_axis[axis] = intervals
        if intervals:
            max_lengths[axis] = max(intervals)[0]
    axis2choose = max_lengths.index(max(max_lengths))
    if max_lengths[axis2choose] == -1:
        final_blocks.append(block)
        return
    intervals = by_axis[axis2choose]
    axis = axis2choose
    block_size_by_axis = block[axis][1] - block[axis][0]
    new_blocks = []
    block_start = 0
    for interval_index in xrange(len(intervals)):
        interval_length, interval_start = intervals[interval_index]
        if interval_start > block_start:
            if not axis:
                new_blocks += [((block[0][0] + block_start, block[0][0] + interval_start), block[1])]
            else:
                new_blocks += [(block[0], (block[1][0] + block_start, block[1][0] + interval_start))]
        block_start = interval_start + interval_length
    if block_start < block_size_by_axis:
        if not axis:
            new_blocks += [((block[0][0] + block_start, block[0][1]), block[1])]
        else:
            new_blocks += [(block[0], (block[1][0] + block_start, block[1][1]))]        
    if not new_blocks:
        final_blocks.append(block)
    for new_block in new_blocks:
        detect_non_empty_blocks(img, new_block, final_blocks)

def get_matrix(img):
    original_image_mat = img.load()
    mat = numpy.zeros((img.size[1], img.size[0]))
    for x in xrange(mat.shape[0]):
        for y in xrange(mat.shape[1]):
            if original_image_mat[y, x] == 0 or original_image_mat[y, x] == (0, 0, 0):
                mat[x, y] = 1
    return mat   


def rotate(image, angle, color, filter=Image.NEAREST):
    if image.mode == "P" or filter == Image.NEAREST:
        matte = Image.new("1", image.size, 1) # mask
    else:
        matte = Image.new("L", image.size, 255) # true matte
    bg = Image.new(image.mode, image.size, color)
    bg.paste(image.rotate(angle, filter),
             matte.rotate(angle, filter))
    return bg

def adjust_rotation(original_image):
    best_angle = 0
    max_vert_space = 0
    for rotation in xrange(-5, 5, 1):
        img = rotate(original_image, rotation, "white")
        #img = original_image.rotate(rotation)
        mat = img.load()
        empty_count = 0
        for y in xrange(img.size[1]):
            inked = 0
            for x in xrange(img.size[0]):
                if mat[x, y] != 255:
                    inked += 1
                    if inked >= 10:
                        break
            if inked < 10:
                empty_count += 1
        if empty_count > max_vert_space:
            best_angle = rotation
            max_vert_space = empty_count
    return best_angle

def max_distance(first, second):
    first_top, first_bottom = first[0]
    first_left, first_right = first[1]
    second_top, second_bottom = second[0]
    second_left, second_right = second[1]
    distances = [0, 0]
    if first_top > second_bottom:
        distances[0] = first_top - second_bottom
    elif second_top > first_bottom:
        distances[0] = second_top - first_bottom
    if first_left > second_right:
        distances[1] = first_left - second_right
    elif second_left > first_right:
        distances[1] = second_left - first_right
    return max(distances)

def merge_blocks(first, second):
    return ( (min(first[0][0], second[0][0]), max(first[0][1], second[0][1])), 
             (min(first[1][0], second[1][0]), max(first[1][1], second[1][1])) )
    

def do_ocr(page):
    page.save("tmp.tif")
    call("cuneiform -f hocr  -l rus tmp.tif -o tmp.cune_out".split())
    cune_paragraphs, cune_letters, cune_texts = upload_cuneiform("tmp.cune_out")
    return  cune_paragraphs, cune_letters, cune_texts 



def do_main_analysis(original_image):
    cune_paragraphs, cune_letters, cune_texts = do_ocr(original_image)
    image_blocks = []
    if 1:
        if "initial image blocks":
            image_mat_no_text = get_matrix(original_image)
            #for paragraph in cune_paragraphs:
            #    for line in paragraph:
            for letter in cune_letters:
                x_min, x_max  = letter[0]
                y_min, y_max  = letter[1] 
                image_mat_no_text[x_min:x_max, y_min:y_max] = 0
                        
            initial_block = ( (0, image_mat_no_text.shape[0]), (0, image_mat_no_text.shape[1]) )
            detect_non_empty_blocks(image_mat_no_text, initial_block, image_blocks)
            
        line_heights = [block[0][1] - block[0][0] for block in cune_letters]
        line_heights.sort()
        line_height_avg = line_heights and line_heights[len(line_heights) / 2] or 1   
        
        if "remove small image blocks":
            image_blocks = [block for block in image_blocks\
                                 if (block[0][1] - block[0][0] >= line_height_avg or \
                                 block[1][1] - block[1][0] >= line_height_avg)]
        
        if "join image blocks":
            while True:
                used = set()
                for first in xrange(len(image_blocks)):
                    if first in used:
                        continue
                    for second in xrange(first + 1, len(image_blocks)):
                        if max_distance(image_blocks[first], image_blocks[second]) < 2 * line_height_avg:
                            image_blocks[first] = merge_blocks(image_blocks[first], image_blocks[second])
                            used.add(second)
                if not used:
                    break
                image_blocks = [image_blocks[index] for index in xrange(len(image_blocks)) if not index in used]
        
        if "remove not big image blocks":
            image_blocks = [block for block in image_blocks\
                                 if (block[0][1] - block[0][0] > 4 * line_height_avg and \
                                 block[1][1] - block[1][0] > 4 * line_height_avg)]
    
    if 1:
        """ ocr without images """
        if image_blocks: 
            page_no_imgs = original_image.copy()
            draw = ImageDraw.Draw(page_no_imgs)
            for block in image_blocks:
                draw.rectangle( (block[1][0], block[0][0], block[1][1], block[0][1]), fill=255)        
            del draw
            page_no_imgs.save("tmp.tif")
            call("cuneiform -f hocr  -l rus tmp.tif -o tmp.cune_out".split())
            cune_paragraphs, cune_letters, cune_texts = upload_cuneiform("tmp.cune_out")   
        
        if """ merge verticaly divided paragraphs """:
            line_heights = [block[0][1] - block[0][0] for block in cune_letters]
            line_heights.sort()
            line_height_avg = line_heights and line_heights[len(line_heights) / 2] or 1  
            parag_coordinates = []
            for parag in cune_paragraphs:
                min_x, max_x = 100000, -10000
                min_y, max_y = 100000, -10000
                for (block_x_min, block_x_max), (block_y_min, block_y_max) in parag:
                    min_x = min(min_x, block_x_min)
                    max_x = max(max_x, block_x_max)
                    min_y = min(min_y, block_y_min)
                    max_y = max(max_y, block_y_max)
                parag_coordinates += [((min_x, max_x), (min_y, max_y))]
            while True:
                used = set()
                for first in xrange(len(cune_paragraphs)):
                    first_left, first_right = parag_coordinates[first][1]
                    for second in xrange(first + 1, len(cune_paragraphs)):
                        if second in used:
                            continue
                        second_left, second_right = parag_coordinates[second][1]
                        if len(cune_paragraphs[first]) == len(cune_paragraphs[second]) and  \
                                 abs(parag_coordinates[first][0][0] - parag_coordinates[second][0][0]) < line_height_avg and \
                                (abs(second_left - first_right) < line_height_avg or abs(second_right - first_left) < line_height_avg):
                            used.add(second)
                            """merge"""
                            merged_paragraph = []
                            for first_line, second_line in zip(cune_paragraphs[first], cune_paragraphs[second]):
                                 merged_paragraph += [merge_blocks(first_line, second_line)]
                                 cune_texts[merged_paragraph[-1]] = cune_texts[first_line] + " " + cune_texts[second_line]
                            cune_paragraphs[first] = merged_paragraph
                            #print "MERGE", first, second
                if not used:
                    break
                cune_paragraphs = [cune_paragraphs[first] for first  in xrange(len(cune_paragraphs)) if not first in used]  
                
        
        
        formulas = []
        if """extract good paragraphs""":
            filtered_paragraphs = []
            for paragraph in cune_paragraphs:
                parag_text = [cune_texts[line] for line in paragraph]
                parag_text = [tokenize(line) for line in parag_text]
                for line_index in xrange(len(parag_text) - 1):
                    cur_last_word = parag_text[line_index] and parag_text[line_index][-1] or " "
                    last_is_dash = False
                    if cur_last_word in u"‒–—―-" and len(parag_text[line_index]) > 1:
                        cur_last_word = parag_text[line_index][-2]
                        last_is_dash = True
                    next_first_word = parag_text[line_index + 1] and parag_text[line_index + 1][0] or " "
                    compound = cur_last_word + next_first_word
                    if next_first_word[0] in u"aбвгдежзиклмнопрстуфхцчшщэюя" and (last_is_dash or compound.lower() in freq_dict):
                        if not last_is_dash:
                            parag_text[line_index][-1] = compound
                        else:
                            parag_text[line_index][-2] = compound
                            parag_text[line_index] = parag_text[line_index][:-1]
                        parag_text[line_index + 1] = parag_text[line_index + 1][1:]
                full_text = []
                for words in parag_text:
                    full_text += words
                good_words = 0
                corrected_words = []
                for word in full_text:
                    corrected_word = grammar_corrector.correct_word(word.lower())
                    corrected_words += [corrected_word]
                    if is_alpha(corrected_word) and len(corrected_word) > 2 and corrected_word in grammar_corrector.dict and  grammar_corrector.dict[corrected_word] > 10:
                        good_words += 1
                if len(full_text) == 1 and good_words != 1 or good_words < 2:
                    formulas += [paragraph]
                else:
                    filtered_paragraphs += [paragraph]
                #print good_words, len(full_text)
                #print " ".join(full_text)
                #print " ".join(corrected_words)
                #print 
            cune_paragraphs = filtered_paragraphs
        
        formulas = []
        if """ update formulas """:
            image_mat_no_text_no_imgs = get_matrix(original_image)
            for paragraph in cune_paragraphs:
                for line in paragraph:
                    x_min, x_max  = line[0]
                    y_min, y_max  = line[1] 
                    image_mat_no_text_no_imgs[x_min:x_max, y_min:y_max] = 0
            for block in image_blocks:
                x_min, x_max  = block[0]
                y_min, y_max  = block[1] 
                image_mat_no_text_no_imgs[x_min:x_max, y_min:y_max] = 0
                        
            initial_block = ( (0, image_mat_no_text_no_imgs.shape[0]), (0, image_mat_no_text_no_imgs.shape[1]) )
            detect_non_empty_blocks(image_mat_no_text_no_imgs, initial_block, formulas)
            
            line_heights = [block[0][1] - block[0][0] for block in cune_letters]
            line_heights.sort()
            line_height_avg = line_heights and line_heights[len(line_heights) / 2] or 1 
            
            
            if "remove small blocks":
                formulas = [block for block in formulas\
                                     if (block[0][1] - block[0][0] >= 0.5 * line_height_avg or \
                                     block[1][1] - block[1][0] >= 0.5 *  line_height_avg)]
            
            if "join formulas' blocks":
                while True:
                    used = set()
                    for first in xrange(len(formulas)):
                        if first in used:
                            continue
                        for second in xrange(first + 1, len(formulas)):
                            if max_distance(formulas[first], formulas[second]) < 2 * line_height_avg:
                                formulas[first] = merge_blocks(formulas[first], formulas[second])
                                used.add(second)
                    if not used:
                        break
                    formulas = [formulas[index] for index in xrange(len(formulas)) if not index in used]
            
            if "remove not big formulas blocks":
                formulas = [block for block in formulas\
                                     if (block[0][1] - block[0][0] > 0.5 * line_height_avg and \
                                     block[1][1] - block[1][0] > 0.5 * line_height_avg)]
    def dump_block(block):
        return ",".join(str(item) for item in [block[0][0], block[0][1], block[1][0], block[1][1]])
    
    dump_line = ""
    for paragraph in cune_paragraphs:
        dump_line += "paragraph\t" + " ".join([dump_block(line) for line in paragraph])
        dump_line += "\n"
    if 1:
        dump_line += "letters\t" + " ".join([dump_block(line) for line in cune_letters])
        dump_line += "\n"
    for block in image_blocks:
        dump_line += "images\t" + " ".join([dump_block(line) for line in image_blocks])
        dump_line += "\n"   
    for block in formulas:
        dump_line += "formulas\t" + " ".join([dump_block(line) for line in formulas])
        dump_line += "\n"  
    for block, text in cune_texts.items():
        dump_line += "text\t" + dump_block(block) + "\t" + text.encode("utf8")
        dump_line += "\n"
    return dump_line
    
    """
    colored_image = original_image.convert("RGB")
    draw = ImageDraw.Draw(colored_image)
    
    for block in image_blocks:
        block_x_min, block_x_max = block[0]
        block_y_min, block_y_max = block[1]
        block_lines = []
        draw.line((block[1][0],  block[0][0], block[1][1], block[0][0] )  , width = 10, fill=(255, 0, 0) )
        draw.line((block[1][0],  block[0][0], block[1][0], block[0][1] )  , width = 10, fill=(255, 0, 0) )
        draw.line((block[1][1],  block[0][0], block[1][1], block[0][1] )  , width = 10, fill=(255, 0, 0) )
        draw.line((block[1][0],  block[0][1], block[1][1], block[0][1] )  , width = 10, fill=(255, 0, 0) )    
        for line_block, letter_blocks in block_lines:
            draw.line((line_block[1][0],  line_block[0][0], line_block[1][1], line_block[0][0] )  , width = 1, fill=(0, 255, 0) )
            draw.line((line_block[1][0],  line_block[0][0], line_block[1][0], line_block[0][1] )  , width = 1, fill=(0, 255, 0) )
            draw.line((line_block[1][1],  line_block[0][0], line_block[1][1], line_block[0][1] )  , width = 1, fill=(0, 255, 0) )
            draw.line((line_block[1][0],  line_block[0][1], line_block[1][1], line_block[0][1] )  , width = 1, fill=(0, 255, 0) )                  
    
    
    for block in cune_letters:
        block_x_min, block_x_max = block[0]
        block_y_min, block_y_max = block[1]
        block_lines = []
        draw.line((block[1][0],  block[0][0], block[1][1], block[0][0] )  , width = 10, fill=(255, 255, 0) )
        draw.line((block[1][0],  block[0][0], block[1][0], block[0][1] )  , width = 10, fill=(255, 255, 0) )
        draw.line((block[1][1],  block[0][0], block[1][1], block[0][1] )  , width = 10, fill=(255, 255, 0) )
        draw.line((block[1][0],  block[0][1], block[1][1], block[0][1] )  , width = 10, fill=(255, 255, 0) )    
        for line_block, letter_blocks in block_lines:
            draw.line((line_block[1][0],  line_block[0][0], line_block[1][1], line_block[0][0] )  , width = 1, fill=(255, 255, 0) )
            draw.line((line_block[1][0],  line_block[0][0], line_block[1][0], line_block[0][1] )  , width = 1, fill=(255, 255, 0) )
            draw.line((line_block[1][1],  line_block[0][0], line_block[1][1], line_block[0][1] )  , width = 1, fill=(255, 255, 0) )
            draw.line((line_block[1][0],  line_block[0][1], line_block[1][1], line_block[0][1] )  , width = 1, fill=(255, 255, 0) )
    
    for paragraph in cune_paragraphs:
        parag_block = paragraph[0]
        for block in paragraph:
            color = (255, 0, 255)
            draw.line((block[1][0],  block[0][0], block[1][1], block[0][0] )  , width = 3, fill=color )
            draw.line((block[1][0],  block[0][0], block[1][0], block[0][1] )  , width = 3, fill=color )
            draw.line((block[1][1],  block[0][0], block[1][1], block[0][1] )  , width = 3, fill=color )
            draw.line((block[1][0],  block[0][1], block[1][1], block[0][1] )  , width = 3, fill=color )
            parag_block = merge_blocks(parag_block, block)
    for paragraph in cune_paragraphs:
        parag_block = paragraph[0]
        for block in paragraph:
            parag_block = merge_blocks(parag_block, block)
        block = parag_block     
        color = (255, 0, 255)
        draw.line((block[1][0],  block[0][0], block[1][1], block[0][0] )  , width = 3, fill=color )
        draw.line((block[1][0],  block[0][0], block[1][0], block[0][1] )  , width = 3, fill=color )
        draw.line((block[1][1],  block[0][0], block[1][1], block[0][1] )  , width = 3, fill=color )
        draw.line((block[1][0],  block[0][1], block[1][1], block[0][1] )  , width = 3, fill=color )    

    for block in formulas:
        color = (0, 0, 255)
        draw.line((block[1][0],  block[0][0], block[1][1], block[0][0] )  , width = 10, fill=color )
        draw.line((block[1][0],  block[0][0], block[1][0], block[0][1] )  , width = 10, fill=color )
        draw.line((block[1][1],  block[0][0], block[1][1], block[0][1] )  , width = 10, fill=color )
        draw.line((block[1][0],  block[0][1], block[1][1], block[0][1] )  , width = 10, fill=color )  
    
    del draw
    colored_image.save("_out.png")
    """


in_path = "016774_rot/"
out_path = "016774_blocks/"
processed = 0
for fname in os.listdir(in_path):
    if len(fname) < 4:
        continue
    processed += 1
    if processed % 10 == 0:
        print "..processed", processed
    if os.path.isfile(out_path + fname):
        continue
    print fname
    original_image = Image.open(in_path + fname)
    dump = do_main_analysis(original_image)
    open(out_path + fname, "w").write(dump)
