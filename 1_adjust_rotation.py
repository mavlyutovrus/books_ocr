import numpy
from scipy.misc import imread
from matplotlib import pyplot as plt

from PIL import Image
from PIL import ImageDraw


def rotate(image, angle, color, filter=Image.NEAREST):
    if image.mode == "P" or filter == Image.NEAREST:
        matte = Image.new("1", image.size, 1) # mask
    else:
        matte = Image.new("L", image.size, 255) # true matte
    bg = Image.new(image.mode, image.size, color)
    bg.paste(image.rotate(angle, filter),
             matte.rotate(angle, filter))
    return bg

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

def get_matrix(img):
    original_image_mat = img.load()
    mat = numpy.zeros((img.size[1], img.size[0]))
    for x in xrange(mat.shape[0]):
        for y in xrange(mat.shape[1]):
            if original_image_mat[y, x] == 0 or original_image_mat[y, x] == (0, 0, 0):
                mat[x, y] = 1
    return mat   

def get_std_with_rotation(original_image, rotation):
    img = rotate(original_image, rotation, "white")
    mat = get_matrix(img)
    profile = build_profile(mat, ((0, mat.shape[0]), (0, mat.shape[1])), 0)
    stdev = numpy.std(profile)
    return stdev    

def adjust_rotation(original_image):
    best_angle = 0
    max_stdev = 0
    prev_val = 0
    for rotation in xrange(-4, 5):
        rotation /= 4.0
        img = rotate(original_image, rotation, "white")
        mat = get_matrix(img)
        profile = build_profile(mat, ((0, mat.shape[0]), (0, mat.shape[1])), 0)
        stdev = numpy.std(profile)
        prev_val = stdev
        if stdev > max_stdev:
            best_angle = rotation
            max_stdev = stdev
    return best_angle



import os
img_path = "016774/"
out_path = "016774_rot/"

processed = 0
files = [fname for fname in  os.listdir(img_path) if ".png" in fname]
for fname in files:
    if os.path.isfile(out_path + fname):
        print "..", fname, "existed"
        processed += 1
        continue
    original_image = Image.open(img_path + fname)
    angle = adjust_rotation(original_image)
    print "..", fname, angle
    rotated_image = rotate(original_image, angle, "white")
    rotated_image.save(out_path + fname)
    processed += 1
    if processed % 10 == 0:
        print "..processed", processed, "/", len(files)
