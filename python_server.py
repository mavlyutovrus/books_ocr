import numpy
import time
from datetime import timedelta
import BaseHTTPServer
import urlparse
import urllib2
import json
import os
import sys


from assign_page_numbers import upload_page_data


def merge_blocks(first, second):
    return ( (min(first[0][0], second[0][0]), max(first[0][1], second[0][1])), 
             (min(first[1][0], second[1][0]), max(first[1][1], second[1][1])), )


from datetime import datetime
from urlparse import parse_qs




def dump_block(block):
    return ",".join(str(item) for item in [block[0][0], block[0][1], block[1][0], block[1][1]])

def parse_block_dump(block):
    x1, x2, y1, y2=  [int(item) for item in block.split(",")]
    return ((x1, x2), (y1, y2))

def overlap(first, second):
    if first[0][0] < second[0][1] and first[0][1] > second[0][0] and \
            first[1][0] < second[1][1] and first[1][1] > second[1][0]:
        return True
    return False

def remove_all_formulas_overlapping_images(paragraphs, images, formulas):
    while True:
        to_drop_images = set()
        to_drop_formulas = set()
        for first in xrange(len(images)):
            if first in to_drop_images:
                continue
            for second in xrange(first + 1, len(images)):
                if second in to_drop_images:
                    continue
                if overlap(images[first], images[second]):
                    images[first] = merge_blocks(images[first], images[second])
                    to_drop_images.add(second)
            for form_index in xrange(len(formulas)):
                if form_index in to_drop_formulas:
                    continue
                if overlap(images[first], formulas[form_index]):
                    images[first] = merge_blocks(images[first], formulas[form_index])
                    to_drop_formulas.add(form_index)      
        if not to_drop_formulas and not to_drop_images:
            break
        formulas = [formulas[form_index] for form_index in xrange(len(formulas)) if not form_index in to_drop_formulas]
        images = [images[index] for index in xrange(len(images)) if not index in to_drop_images]
    return paragraphs, images, formulas
        
        

img_source = "/home/arslan/src/ngpedia/016774_rot/"
blocks_source = "/home/arslan/src/ngpedia/016774_blocks/"
pages = [fname for fname in os.listdir(img_source) \
                        if not fname.startswith(".") and fname[-3:] in ["png", "tif", "jpg", "peg"]]
pages.sort()





def save_corrected_blocks(paragraphs, images, formulas, page):
    paragraphs, images, formulas = remove_all_formulas_overlapping_images(paragraphs, images, formulas)
    dump_line = "" 
    for block in paragraphs:
        dump_line += "paragraph\t" + dump_block(block) + "\n"
    for block in images:
        dump_line += "image\t" + dump_block(block) + "\n"
    for block in formulas:
        dump_line += "formula\t" + dump_block(block) + "\n"
    open(blocks_source + page + ".corr", "w").write(dump_line)

def load_corrected_blocks(paragraphs, images, formulas, page):
    if os.path.isfile(blocks_source + page + ".corr"):
        for line in open(blocks_source + page + ".corr"):
            addr, block_str = line.strip().split("\t")
            block = parse_block_dump(block_str)
            if addr == "paragraph":
                paragraphs.append(block)
            elif addr =="image":
                images.append(block)
            elif addr == "formula":
                formulas.append(block)
            else:
                print "FUCKUP", line
        return True
    return False



class GetHandler (BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        full_query = self.path
        full_query = full_query.replace("?callback=", "&callback=")
        query = urlparse.parse_qs(urlparse.urlparse(full_query).query)
        query_type = full_query.split("?")[0]
        
        page = pages[0]
        
        response = "['', [], [], []]"
        if "/next_page" in query_type and "page" in query:
            page = query["page"][0].split("/")[-1]
            if page in pages:
                cur_index = pages.index(page)
                if cur_index < len(pages):
                    page = pages[cur_index + 1]

        if "/prev_page" in query_type and "page" in query:
            page = query["page"][0].split("/")[-1]
            if page in pages:
                cur_index = pages.index(page)
                if cur_index > 0:
                    page = pages[cur_index - 1]
        
        if "/page_send" in query_type and "page" in query:
            page = query["page"][0].split("/")[-1]
            paragraphs = []
            formulas = []
            images = []
            for field, array in [("p", paragraphs), ("f", formulas), ("i", images)]:
                if field in query:
                    for block in query[field]:
                        try:
                            x1, x2, y1, y2 = [int(chunk) for chunk in block.split(',')]
                            array += [((x1, x2), (y1, y2),)]
                        except:
                            print "fuckup:", block
            save_corrected_blocks(paragraphs, images, formulas, page) 
            print "saved"
        
        
        if 1:
            print page
            paragraphs_blocks = []
            formulas = []
            images = []
            if not load_corrected_blocks(paragraphs_blocks, images, formulas, page):
                print "load orig"
                paragraphs, _, formulas, images, _ = upload_page_data(blocks_source + page)
                paragraphs_blocks = []
                for paragraph in paragraphs:
                    by_height = [(line[0][0], line) for line in paragraph]
                    by_height.sort()
                    paragraph = [line for _, line in by_height]
                    paragraph_block = paragraph[0]
                    for line_block in paragraph:
                        paragraph_block = merge_blocks(line_block, paragraph_block)       
                    paragraphs_blocks += [paragraph_block]
            
            parags_str = ",".join([str(coord) for block in paragraphs_blocks for dim in block for coord in dim])
            formulas_str = ",".join([str(coord) for block in formulas for dim in block for coord in dim])
            images_str = ",".join([str(coord) for block in images for dim in block for coord in dim])    
            response = "[\"%s\", [%s], [%s], [%s]]" % (img_source + page, parags_str, images_str, formulas_str)
            
        
        function_name = query.has_key("callback") and query["callback"][0] or ""
        response = function_name + "(" + response + ")"    
        
        response = response.encode("utf8")    

        request_headers = self.headers.__str__().replace(chr(10), " ").replace(chr(13), " ")
        print "[STAT]\tclient:", self.client_address, "\theaders:", request_headers, "\tquery:", full_query
        sys.stdout.flush()
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        #self.wfile.write(json_result)
        self.wfile.write(response)
        print response
        
                    

def run(server_class=BaseHTTPServer.HTTPServer,
        handler_class=GetHandler):
    print "starting"
    server_address = ('', 8084)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

run()

