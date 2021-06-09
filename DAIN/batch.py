import os, sys, subprocess as sp
file_list = []
with open("list.txt", "r") as inp:
    file_list = inp.read().split("\n")

print(file_list)
file_name = file_list[0]
if '!X!X!X' in file_list[0]:
    file_name = file_list[0].split('!X!X!X')
    pad = 3
elif '!X!X' in file_list[0]:
    file_name = file_list[0].split('!X!X')
    pad = 2
elif '!X' in file_list[0]:
    file_name = file_list[0].split('!X')
    pad = 1
else:
    print("variable not found")
    sys.exit()

intro_skip = file_list[1].split(" ")[1]
ending_skip = file_list[2].split(" ")[1]

for y in range(3):
    file_list.pop(0)

for x in range(len(file_list)-1):
    number = str(file_list[x]).zfill(pad)
    curr_file = f"{file_name[0]}{number}{file_name[1]}"
    print("||| current file:", curr_file, "|||")
    command = f"python -W ignore colab_interpolate.py     --netName DAIN_slowmotion --time_step 0.5 --input_file /content/drive/MyDrive/{curr_file} --output_dir /content/drive/MyDrive/DAIN --enable_transcoder 0 --overwrite 0 --upscale_only 0  --selective_interpolation 1 --dual_instance 1   --waifu2x_scale 2 --waifu2x_model ../waifu2x-ncnn-vulkan/models/models-upconv_7_anime_style_art_rgb --ph_this_bad_th 500 --use_debug_parts 0 --debug_nb_parts 0 --intro_skip {intro_skip} --ending_skip {ending_skip}"
    print("current command:", command)

    os.system(command)
