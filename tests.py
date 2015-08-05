import numpy
from scipy.misc import imread
from matplotlib import pyplot as plt

from PIL import Image
from PIL import ImageDraw





def upload_recognized_text_lines(file_orf):
    color = 0
    heights = []
    blocks = []
    min_x = 100000
    min_y = 100000
    max_x = 0
    max_y = 0
    lines = []
    for line in open(file_orf):
        if ";" in line:
            y, x, dy, dx = line.split(";")[0].split()
            y, x, dy, dx = int(y), int(x), int(dy), int(dx)
            
            min_x = min(x, min_x)
            min_y = min(y, min_y)
            max_x = max(x + dx, max_x)
            max_y = max(y + dy, max_y)        
            blocks += [ (x, y, x + dx, y + dy) ]
            heights += [dx]
    
        elif heights:
            heights.sort()
            quarter = len(heights) / 4
            mean, std = numpy.mean(heights[quarter:-quarter]), numpy.std(heights[quarter:-quarter])
            print mean, std, heights
            lines += [((mean, std), (min_x, min_y, max_x, max_y), blocks)]
            heights = []
            blocks = []
            min_x = 100000
            min_y = 100000
            max_x = 0
            max_y = 0

    if heights:
        heights.sort()
        quarter = len(heights) / 4
        mean, std = numpy.mean(heights[quarter:-quarter]), numpy.std(heights[quarter:-quarter])
        print mean, std, heights
        lines += [((mean, std), (min_x, min_y, max_x, max_y), blocks)]
    return lines


"""

original_image = Image.open("2.pbm")
original_image = original_image.convert("RGB")
draw = ImageDraw.Draw(original_image)

lines = upload_recognized_text_lines("1.orf")
for height_params, borders, blocks in lines:
    min_x, min_y, max_x, max_y = borders
    import random
    color= (random.randint(0,255),random.randint(0,255),random.randint(0,255))
    draw.rectangle((min_y, min_x, max_y, max_x), outline=color )
del draw

original_image.save("2.png")
exit()
"""



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

def get_borders(img, axis):
    MAX_ABSOLUTE_TRASH_SIZE = 10
    if axis:
        start = 0
        for x in xrange(img.shape[1]):
            if sum(img[:, x]) > MAX_ABSOLUTE_TRASH_SIZE:
                start = x
                break
        end = img.shape[1]
        for x in xrange(img.shape[1] - 1, -1, -1):
            if sum(img[:, x]) > MAX_ABSOLUTE_TRASH_SIZE:
                end = x + 1
                break
    else:
        start = 0
        for x in xrange(img.shape[0]):
            if sum(img[x, :]) > MAX_ABSOLUTE_TRASH_SIZE:
                start = x
                break
        end = img.shape[0]
        for x in xrange(img.shape[0] - 1, -1, -1):
            if sum(img[x, :]) > MAX_ABSOLUTE_TRASH_SIZE:
                end = x + 1
                break
    start = max(0, start - MAX_ABSOLUTE_TRASH_SIZE)
    end = min(end + MAX_ABSOLUTE_TRASH_SIZE, img.shape[axis])
    return (start, end)

def empty_intervals(profile):
    intervals = []
    start = -1
    for end in xrange(len(profile)):
        if profile[end] > 0:
            if start > -1:
                if start != 0:
                    intervals.append((end - start, start))
                start = -1
        elif start == -1:
            start = end
    #if start > -1:
    #    intervals.append((len(profile) - start, start)) 
    return intervals


def split_on_major_blocks(img, draw, block, MIN_BORDER_WIDTH):
    by_axis = [[], []]
    max_lengths = [-1, -1]
    for axis in xrange(2):
        profile = build_profile(img, block, axis)
        intervals = empty_intervals(profile)
        intervals = [(length, start) for length, start in intervals if length >= MIN_BORDER_WIDTH[axis]]
        by_axis[axis] = intervals
        if intervals:
            max_lengths[axis] = max(intervals)[0]
    axis2choose = max_lengths.index(max(max_lengths))
    if max_lengths[axis2choose] == -1:
        return
    
    intervals = by_axis[axis2choose]
    axis = axis2choose
    intervals_centers_abs = [start + length / 2 + block[axis][0] for length, start in intervals]
    intervals_centers_abs.sort()
    new_blocks = []
    if not axis:
        intervals_centers_abs = [block[0][0]] + intervals_centers_abs + [block[0][1]]
        for border_index in xrange(1, len(intervals_centers_abs)):
            new_blocks += [((intervals_centers_abs[border_index - 1], intervals_centers_abs[border_index]), block[1])]
    else:
        intervals_centers_abs = [block[1][0]] + intervals_centers_abs + [block[1][1]]
        for border_index in xrange(1, len(intervals_centers_abs)):
            new_blocks += [(block[0], (intervals_centers_abs[border_index - 1], intervals_centers_abs[border_index]))]        
    
    for new_block in new_blocks:
        
        draw.line((new_block[1][0],  new_block[0][0], new_block[1][1], new_block[0][0] )  , width = 20 )
        draw.line((new_block[1][0],  new_block[0][0], new_block[1][0], new_block[0][1] )  , width = 20 )
        draw.line((new_block[1][1],  new_block[0][0], new_block[1][1], new_block[0][1] )  , width = 20 )
        draw.line((new_block[1][0],  new_block[0][1], new_block[1][1], new_block[0][1] )  , width = 20 )        
        #draw.rectangle((new_block[1][0], new_block[0][0], new_block[1][1], new_block[0][1]), outline=0, width = 3)
        split_on_major_blocks(img, draw, new_block, MIN_BORDER_WIDTH)


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
    
    


import os
img_path = "chemtxt/tiff_scrappler/imgs/"
out_path = "rotated/"

processed = 0

for fname in os.listdir(img_path):
    if not fname.endswith(".tif"):
        continue
    original_image = Image.open(img_path + fname)
    rotate_on_angle = adjust_rotation(original_image)
    if abs(rotate_on_angle) > 2:
        print "rotate_on_angle",rotate_on_angle, fname
    original_image = rotate(original_image, rotate_on_angle, 255)
    original_image.save(out_path + fname)
    
    
    continue
    
    
    original_image_mat = original_image.load()
    draw = ImageDraw.Draw(original_image)
    img = numpy.zeros((original_image.size[1], original_image.size[0]))
    for x in xrange(img.shape[0]):
        for y in xrange(img.shape[1]):
            if original_image_mat[y, x] == 0:
                img[x, y] = 1
    initial_block = (get_borders(img, 0), get_borders(img, 1))
    MIN_BORDER_WIDTH = ((initial_block[0][1] - initial_block[0][0]) / 100, (initial_block[1][1] - initial_block[1][0]) / 20)
    draw.rectangle((initial_block[1][0], initial_block[0][0], initial_block[1][1], initial_block[0][1]), outline=0)
    split_on_major_blocks(img, draw, initial_block, MIN_BORDER_WIDTH)
    del draw
    original_image.save("processed/" + fname)

