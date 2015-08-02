#-*- coding:utf8 -*-
import numpy
from matplotlib import pyplot as plt
from PIL import Image
from PIL import ImageDraw
import re
import os
import sys
from subprocess import call
from assign_page_numbers import assign_page_numbers
from assign_page_numbers import upload_page_data

from fix_grammar import tokenize
from fix_grammar import good_word
from fix_grammar import is_alpha

freq_dict = set()
for line in open("freq_dict.txt"):
  word = line.decode("utf8").split("\t")[0]
  freq = int(line.decode("utf8").split("\t")[1])
  freq_dict.add(word)


def merge_blocks(first, second):
    return ( (min(first[0][0], second[0][0]), max(first[0][1], second[0][1])), 
             (min(first[1][0], second[1][0]), max(first[1][1], second[1][1])), )
    
def block2PIL_block(block):
    return (block[1][0], block[0][0], block[1][1], block[0][1])

def block2PIL_2tuple_block(block):
    return ((block[1][0], block[0][0]), (block[1][1], block[0][1]),)

def extract_block_as_image(block, page_img, page_draw):
    region = page_img.crop(block2PIL_block(block)).copy()
    #page_draw.rectangle(block2PIL_block(block), fill="white")
    return region

def draw_mockup(original_image, paragraphs, letters, formulas, images, block2text):
    original_image = original_image.copy()
    colored_image = original_image.convert("RGB")
    draw = ImageDraw.Draw(colored_image)
    print images
    for block in images:
        print block
        draw.line((block[1][0],  block[0][0], block[1][1], block[0][0] )  , width = 10, fill=(255, 0, 0) )
        draw.line((block[1][0],  block[0][0], block[1][0], block[0][1] )  , width = 10, fill=(255, 0, 0) )
        draw.line((block[1][1],  block[0][0], block[1][1], block[0][1] )  , width = 10, fill=(255, 0, 0) )
        draw.line((block[1][0],  block[0][1], block[1][1], block[0][1] )  , width = 10, fill=(255, 0, 0) )                    
    

    for paragraph in paragraphs:
        parag_block = paragraph[0]
        for block in paragraph:
            color = (255, 0, 255)
            draw.line((block[1][0],  block[0][0], block[1][1], block[0][0] )  , width = 3, fill=color )
            draw.line((block[1][0],  block[0][0], block[1][0], block[0][1] )  , width = 3, fill=color )
            draw.line((block[1][1],  block[0][0], block[1][1], block[0][1] )  , width = 3, fill=color )
            draw.line((block[1][0],  block[0][1], block[1][1], block[0][1] )  , width = 3, fill=color )
            parag_block = merge_blocks(parag_block, block)
    
    for paragraph in paragraphs:
        parag_block = paragraph[0]
        for block in paragraph:
            parag_block = merge_blocks(parag_block, block)
        block = parag_block     
        color = (255, 0, 155)
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
    colored_image.save("mockup.png")
    



def join_parag_text(paragraph, block2text):
    parag_text = [block2text[line] for line in paragraph]
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
    parag_words = [word for words in parag_text for word in words]
    full_text = ""
    no_space_before = False
    for word in parag_words:
        if word[0] in u".,:;?!)}]\"»" or no_space_before:
            full_text += word
        else:
            full_text += " " + word
        no_space_before = word[-1] in u"«({[\""
    return full_text
      
def convert2html_block(block_img, block, whole_page_block, html_page_height, zindex, html_images_path, html_images_path_rel_path):
    whole_page_height = whole_page_block[0][1] - whole_page_block[0][0]
    whole_page_width = whole_page_block[1][1] - whole_page_block[1][0]
    html_page_width = html_page_height * whole_page_width / whole_page_height 
    x_scale = html_page_height / float(whole_page_height)
    y_scale = html_page_width / float(whole_page_width)
    
    top = (block[0][0] - whole_page_block[0][0]) * x_scale
    left = (block[1][0] - whole_page_block[1][0]) * y_scale
    height = (block[0][1] - block[0][0]) * x_scale
    width = (block[1][1] - block[1][0]) * y_scale
    top, left, height, width = int(top), int(left), int(height), int(width)
    
    #print top, left, height, width, x_scale, y_scale, whole_page_block, block
    
    import random 
    fname = str(random.random())[2:] + ".png"
    fpath = html_images_path + fname
    fpath_rel = html_images_path_rel_path + fname
    block_img.save(fpath)
    
    html_block = """<img src="%s" style="top: %dpx; left: %dpx; width: %dpx; height: %dpx; z-index: %d; position: absolute; " />\n""" %\
                (fpath_rel, top, left, width, height, zindex)    
    return html_block

def convert_parag2html_block(parag_lines, block2text, block, whole_page_block, html_page_height, 
                             zindex, html_images_path, html_images_path_rel_path):
    whole_page_height = whole_page_block[0][1] - whole_page_block[0][0]
    whole_page_width = whole_page_block[1][1] - whole_page_block[1][0]
    html_page_width = html_page_height * whole_page_width / whole_page_height 
    x_scale = html_page_height / float(whole_page_height)
    y_scale = html_page_width / float(whole_page_width)
    
    top = (block[0][0] - whole_page_block[0][0]) * x_scale
    left = (block[1][0] - whole_page_block[1][0]) * y_scale
    height = (block[0][1] - block[0][0]) * x_scale
    width = (block[1][1] - block[1][0]) * y_scale
    top, left, height, width = int(top), int(left), int(height), int(width)
    
    line_heights = [line_block[0][1] - line_block[0][0] for line_block in parag_lines]
    line_heights.sort()
    line_height = int(line_heights[len(line_heights) / 2] * x_scale * 0.8)
    
    
    
    print parag_lines
    text = join_parag_text(parag_lines, block2text) 
    print text.encode("utf8")
    
    
    html_block = """<p style="font-size: %dpx; top: %dpx; left: %dpx; width: %dpx; height: %dpx; z-index: %d; position: absolute; " >\n %s</p>\n""" %\
                (line_height, top, left, width, height, zindex, text)
    
    return html_block


def create_html_pages(images_input_dir, blocks_input_dir, output_dir):
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
        
    imgs_dir = output_dir + "/imgs/"
    if not os.path.isdir(imgs_dir):
        os.makedirs(imgs_dir)
    else:
        for img_fname in os.listdir(imgs_dir):
            os.remove(imgs_dir + img_fname)
    img_rel_dir = "imgs/"    
    
    files = [fname for fname in os.listdir(images_input_dir) \
                if not fname.startswith(".") and fname[-3:] in ["bmp", "tif", "png", "svg", "jpg", 'peg']]
    if not files:
        print "FUCKUP no files in images_input_dir"
        exit()
    files.sort()
    file2page_number, gaps = assigned_page_numbers, gaps = assign_page_numbers(files, blocks_input_dir)
    if gaps:
        print gaps
        print "FUCKUP with page numbers. TERMINATE."
        exit()
        
    html = """<html><head><title></title><meta charset="UTF-8"/></head><body>\n"""    
    
    processed = 0
    for fname in files:
        processed += 1
        if processed % 20 == 0:
            break
        
        html_filename = output_dir + fname.split(".")[0] + ".html"
        
        paragraphs, letters, formulas, images, block2text = upload_page_data(blocks_input_dir + fname)
        
        page_image = Image.open(images_input_dir + fname)
        page_image = page_image.convert('LA')
        page_draw = ImageDraw.Draw(page_image)
        
        draw_mockup(page_image, paragraphs, letters, formulas, images, block2text)
        
        images_count = 0
        paragraphs_count = 0
        formulas_count = 0
        
        all_blocks = [line for parag in paragraphs  for line in parag] + formulas + images
        page_block = ((0,100), (0, 100))
        if all_blocks:
            page_block = all_blocks[0]
            for block in all_blocks:
                page_block = merge_blocks(block, page_block)
        page_block = ((0, page_image.size[1],), (page_block[1][0] - 10, page_block[1][1] + 10,),)
        
                
        html_page_width = 800;
        html_page_height = html_page_width * (page_block[0][1] - page_block[0][0]) / (page_block[1][1] - page_block[1][0])  
        
        html_page_inner = ""
        
        for img_block in images:
            img_image = extract_block_as_image(img_block, page_image, page_draw)
            html_page_inner += convert2html_block(img_image, img_block, page_block, html_page_height, 5, imgs_dir, img_rel_dir)
        
        for paragraph in paragraphs:
            by_height = [(line[0][0], line) for line in paragraph]
            by_height.sort()
            paragraph = [line for _, line in by_height]
            paragraph_block = paragraph[0]
            for line_block in paragraph:
                paragraph_block = merge_blocks(line_block, paragraph_block)
            """
            img_regions = []
            for line_block in paragraph:
                region = extract_block_as_image(line_block, page_image, page_draw)
                coords_in_paragraph = ((line_block[0][0] - paragraph_block[0][0], line_block[0][1] - paragraph_block[0][0]),
                                       (line_block[1][0] - paragraph_block[1][0], line_block[1][1] - paragraph_block[1][0]))
                img_regions += [(coords_in_paragraph, region)]
            parag_x_size, parag_y_size = paragraph_block[0][1] - paragraph_block[0][0], paragraph_block[1][1] - paragraph_block[1][0]
            parag_image = Image.new("LA", (parag_y_size, parag_x_size), 255)
            for coord, line_img in img_regions: 
                parag_image.paste(line_img, block2PIL_block(coord)) 
            html_page_inner += convert2html_block(parag_image, paragraph_block, page_block, html_page_height, 10, html_images_path, html_images_path_rel_path)
            """
            html_page_inner += convert_parag2html_block(paragraph, block2text, paragraph_block, page_block, html_page_height, 10, imgs_dir, img_rel_dir)
            
        for formula_block in formulas:
            formula_img = extract_block_as_image(formula_block, page_image, page_draw)            
            html_page_inner += convert2html_block(formula_img, formula_block, page_block, html_page_height, 5, imgs_dir, img_rel_dir)
        
        del page_draw
        
        #html = """<html><head><title></title></head><body>\n<div id="page" style="width: %dpx; height: %dpx; border: 1px solid black; position: relative; " >\n%s\n</div></body></html>\n""" %\
        #        (html_page_width, html_page_height, html_page_inner) 
        #open(html_filename, "w").write(html)
        
        html += """\n<div id="page" style="width: %dpx; height: %dpx; border: 1px solid black; position: relative; " >\n%s\n</div>\n""" %\
                (html_page_width, html_page_height, html_page_inner)
        
    html += "</body></html>"
    open(output_dir + "/index.html", "w").write(html.encode("utf8"))
    
    
    

input_directory = "016774_blocks/"
output_directory = "016774_html/"
create_html_pages("016774_rot/", "016774_blocks/", output_directory)
