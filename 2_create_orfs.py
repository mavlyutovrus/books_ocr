  


import os
img_path = "rotated/"
out_path = "orfs/"
out_path_cuniform = "cuneiform/"

processed = 0
out = open("create_orf.sh", "w")
for fname in os.listdir(img_path):
    if not fname.endswith(".tif"):
        continue
    #action = "convert " + img_path + fname + " tmp.pbm; ocrad -x " + out_path + fname + " tmp.pbm;"
    #out.write(action + "\n")
    action = "cuneiform -f hocr  -l rus " + img_path + fname + " -o " + out_path_cuniform + fname + ";"
    out.write(action + "\n")
out.close()
