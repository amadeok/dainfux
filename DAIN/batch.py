import os, sys, subprocess as sp

if len(sys.argv) > 1:
    transcode = int(sys.argv[1])
else: transcode = 0

def read_file():
    global file_list; global file_name; global intro_skip_ori; global ending_skip_ori; global time_step_ori; global pad; global out_dir_; global smart_fill

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
    out_dir_ = file_list[1]
    intro_skip_ori = file_list[2].split(" ")[1]
    ending_skip_ori = file_list[3].split(" ")[1]
    time_step_ori = file_list[4].split(" ")[1]
    smart_fill = file_list[5].split(" ")[1]

    for y in range(6):
        file_list.pop(0)
    return file_list

read_file()

for x in range(len(file_list)):
    read_file()
    intro_skip = intro_skip_ori
    ending_skip = ending_skip_ori
    time_step = time_step_ori

    len_ = len(file_list[x].split(" "))
    if len_ == 1:
        number = str(file_list[x]).zfill(pad)
    elif len_ >= 3:
        number = str(file_list[x].split(" ")[0]).zfill(pad)
        intro_skip = file_list[x].split(" ")[1]
        ending_skip = file_list[x].split(" ")[2]
        if len_ == 4:     
            time_step = file_list[x].split(" ")[3]


    elif len_ == 2:
        number = str(file_list[x].split(" ")[0]).zfill(pad)
        time_step = file_list[x].split(" ")[1]


    curr_file = f"{file_name[0]}{number}{file_name[1]}"

    print("||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
    print("||| current file:", curr_file, "|||",  "intro_skip: ", intro_skip, "intro_skip: ",  ending_skip, "|||", "time_step:", time_step)
    full_cmd = f"python -W ignore colab_interpolate.py     --netName DAIN_slowmotion --time_step {time_step} --input_file '/content/drive/MyDrive/{curr_file}' --output_dir /content/drive/MyDrive/DAIN --enable_transcoder 0 --overwrite 0 --upscale_only 0  --selective_interpolation 1 --dual_instance 1   --waifu2x_scale 2 --waifu2x_model ../waifu2x-ncnn-vulkan/models/models-upconv_7_anime_style_art_rgb --ph_this_bad_th 500 --use_debug_parts 0 --debug_nb_parts 0 --intro_skip {intro_skip} --ending_skip {ending_skip} --smart_fill {smart_fill}"

    if transcode == 0:
        cmd = full_cmd
    else: 
        transcode_cmd = f"python colab_interpolate.py --time_step {time_step} --count_ph 2 --input_file '{curr_file}' --output_dir '{out_dir_}' --selective_interpolation 1 --intro_skip {intro_skip} --ending_skip {ending_skip} --use_ffmpeg_dec 1"
        cmd = transcode_cmd
    print("current command:", cmd)

    os.system(cmd)
