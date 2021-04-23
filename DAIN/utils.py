import os, sys
import psutil
import GPUtil
import subprocess as sp
import ffmpeg, math
import numpy as np
from PIL import Image
from various import find_wti_offset
waifu2x_dir = "/home/amadeok/waifu2x-ncnn-vulkan/build"
def read_data(c, file_name):
    parts_dir = c.process_dir
    data = []
    ins = open(f'{parts_dir}/{file_name}.txt', "r")
    for line in ins:
        number_strings = line.split()  # Split the line on runs of whitespace
        numbers = [int(n) for n in number_strings]  # Convert to integers
        data.append(numbers)  # Add the "row" to your list.
        #arr = np.array([numbers])
    data.pop(0)

   # print(f"{file_name} data read")
    ins.close()

    return data
def time_step_calculation():
    INPUT_FILEPATH = f"/content/gdrive/My Drive/{input_file}"
    TARGET_FPS = target_fps
    import os
    filename = os.path.basename(INPUT_FILEPATH)

    import cv2
    cap = cv2.VideoCapture(INPUT_FILEPATH)

    fps = cap.get(cv2.CAP_PROP_FPS)
    time_step = fps/TARGET_FPS

    if(fps/TARGET_FPS>0.5):
        print("Define a higher fps, because there is not enough time for new frames. (Old FPS)/(New FPS) should be lower than 0.5. Interpolation will fail if you try.")
        print(f"{fps}, {TARGET_FPS}, {fps/TARGET_FPS}")
    return time_step

def get_file_info(input_file):
    import cv2
    cap = cv2.VideoCapture(input_file)
    width  = cap.get(cv2.CAP_PROP_FRAME_WIDTH)   # float `width`
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)  
    input_fps = cap.get(cv2.CAP_PROP_FPS)
    return [width, height, input_fps]

ffmpeg_dir = "/home/amadeok/ffmpeg_static/"
def interpret_intro_end(string ):
    string_l = string.split('-')
    start = string_l[0].split(':') 
    start_sec = (int(start[0])*60)+int(start[1])

    end = string_l[1].split(':') 
    end_sec = (int(end[0])*60)+int(end[1])
    return start_sec, end_sec
def get_part_data(c):
    print("Extracting data")
    i_s, i_e = interpret_intro_end(c.intro_skip)
    e_s, e_e = interpret_intro_end(c.ending_skip)
    if not os.path.isfile(c.input_file):
        print("Input file not found, exiting")
        sys.exit()
    vf = f"photosensitivity=bypass=1:export_data=4:is={i_s}:ie={i_e}:os={e_s}:oe={e_e}:f=24:target_dir='{c.process_dir}':log=1:this_badness_thres={c.ph_this_bad_th}:use_newbadness={c.use_newbadness} "
    os.system(
        f"{c.ffmpeg_bin} -i '{c.input_file}' -vf {vf} -loglevel 32 -f null  /dev/null > dump")
    print("Part data extraction finished")

    #is=1:ie=155:os=1390:oe=1430 one piece 945
    #is=59:ie=130:os=1290:oe=1380 kimetsu no yaiba

def check_index(c, count):
    if count == c.part_indexes[c.index_counter]:
        c.index_counter+=1
        return 1
    else: return 0

def get_tot_photosensitive_frames(c):
    loop_nb = 0
    u = 0
    while loop_nb <= c.nb_parts_tot:
        if check_index(c, loop_nb):
            u += c.part_data[loop_nb][5]
            if c.part_indexes[c.index_counter] == None:
                break
        if loop_nb == 5:
            pass
        loop_nb += 1

    print(f"{c.log}Total number of frames to interpolate: {u}")
    #print(f"{c.log}Interpolation bypass: {int_bypass}")
    #except: print(f"Total number of frames to interpolate: {u}")
    return u

# if get_part_info == 1:
#     get_part_data()
# read_data()

# time.sleep(1)




def get_min_decoder_parts():
    min_number_frames_decoder = 400
    min_part_decoder = 0
    u = 0
    while u <= min_number_frames_decoder:
        u += part_data[min_part_decoder][5]
        min_part_decoder += 2
    return (min_part_decoder + global_start_part) // 2


min_parts_decode = 8



def get_length(filename):
    ffmpeg_dir = ""
    try:
        result = sp.run([f"{ffmpeg_dir}ffprobe", "-v", "error", "-show_entries",
                                "format=duration", "-of",
                                "default=noprint_wrappers=1:nokey=1", filename],
                                stdout=sp.PIPE,
                                stderr=sp.STDOUT)
        error_message = "Invalid data found when"
        result_string = str(result)
        if error_message in result_string:
           # print(f"File {filename} is broken")
            return 0
        else:
            return float(result.stdout)
    except: return 0

def check_file(c, count, output_file):
    if os.path.isfile(output_file) == False:
        return False
    ms_per_frame = 1000 / c.input_fps
    #correct_lenght = c.part_data[count][4] / round(c.input_fps) * 1.001
    correct_lenght = c.part_data[count][4] * ms_per_frame /1000
    output_lenght = get_length(output_file)
    if math.isclose(correct_lenght, output_lenght, rel_tol=0.003) == False:
        print(
            f"Part {count} has wrong lenght, correct is {correct_lenght}")
        return False
    else: return True

def getCPUusage():
    cpu = psutil.cpu_percent(interval=None)
    # print("Cpu = {}  ".format(cpu), end='')
    return cpu


def extract_audio():
    input_stream = ffmpeg.input(
        '/content/gdrive/My Drive/{}'.format(input_file))
    aud = input_stream.audio
    outAud = ffmpeg.output(
        aud, "/content/gdrive/My Drive/output/audio.mp3".format(outFld))
    outAud.overwrite_output().run(capture_stdout=True, capture_stderr=True)

class pid_obj:
    def __init__(self, pid, name):
        self.name  = name
        self.pid = pid

def check_missing(c, which):
    for x in range(c.nb_parts_tot):
        curr_file = f"{c.process_dir}/{x:04}.mp4"
        if c.part_data[x][3] == which and not check_file(c, x, curr_file) or c.part_data[x][3] == which and c.overwrite: #:
            return 1 #some missing
    return 0 #none missing

def start_ffmpeg_wti(c):
    pixel_format = 'rgba'
    vf = f"photosensitivity=bypass=1:export_data=4:is=0:ie=0:os=0:oe=0:f=24:target_dir='{c.process_dir}/test':log=33:this_badness_thres={c.ph_this_bad_th}:use_newbadness={c.use_newbadness}"

    ffmpeg_pipe = f"/tmp/ffmpeg_pipe__0_id{c.instance_id}"
    cmd_command = [f'{c.ffmpeg_bin}',  '-r', f'{c.target_fps}', '-pix_fmt', pixel_format, '-s', c.target_resolution_s,
        '-f', 'rawvideo', '-i',  ffmpeg_pipe, '-vf', vf, '-f', 'null',  '/dev/null',  '-loglevel', '-8']# '>', f'dump']
    execute = sp.Popen(cmd_command, stdout=sp.PIPE,     stderr=sp.PIPE )

    return execute


def start_interpolate_ffmpeg(PID_list, output_file, c, transcode):

    if transcode:  pipe_count = c.pipe_counter_t
    else:           pipe_count = c.pipe_counter_i

    ffmpeg_pipe = f"/tmp/ffmpeg_pipe_{transcode}_{pipe_count}_id{c.instance_id}"
    pixel_format = 'rgba'
    print(f"{c.log} starting ffmpeg with {transcode} fifo: {ffmpeg_pipe}")

    if os.path.exists(ffmpeg_pipe) == False:
        try: os.mkfifo(ffmpeg_pipe)
        except: pass

    # if transcode:
    #     pixel_format = 'rgb24'

    vf_command =  ""
    cmd_command = ['ffmpeg',  '-r', f'{c.target_fps}', '-pix_fmt', pixel_format, '-s', c.target_resolution_s,
            '-f', 'rawvideo', '-i',  ffmpeg_pipe, '-vcodec', 'libx264', '-preset', 'medium', '-crf', '18', '-tune', 'animation',
             f'{c.process_dir}/{output_file}.mp4', "-y"]

    if (c.waifu2x_scale != 0 and not transcode):
        c.pipe_counter_i += 2

    execute = sp.Popen(cmd_command)
    PID_list.append(pid_obj(execute.pid, '2ffmpeg'))

    #pipe_video = open_fifo(ffmpeg_pipe)

def start_waifu2x(c, PID_list):
    R = sp.Popen([c.waifu2x_bin, 
    "-i",  "dain",  "-m",     c.waifu2x_model,  
    "-o",  "ffmpeg",  "-n",  "0",  "-s",str(c.waifu2x_scale), 
    "-j", "1:1:1","-p", str(c.imgs_per_frame), "-d", str(c.instance_id),
    "-z", str(c.upscale_only)])
    PID_list.append(pid_obj(R.pid, '0waifu2x'))

def start_another_instance(c, PID_list):
    R = sp.Popen([f'python',  'colab_interpolate.py',  
    f'--netName', 'DAIN_slowmotion', '--time_step',
    str(c.time_step),                 "--input_file",
    str(c.input_file),   "--output_dir",  str(c.output_dir),
   "--enable_transcoder", "0",#str(c.enable_transcoder),
    "--overwrite",  str(c.overwrite),   "--mode",
    str(c.mode), "--dual_instance",  "1",   "--waifu2x_scale",
     str(c.waifu2x_scale),   "--waifu2x_model", str(c.waifu2x_model),
     "--instance_id", "1", "--wti_offset", str(c.wti_offset), "--selective_interpolation",
     str(c.selective_interpolation), "--debug_nb_parts",  str(c.debug_nb_parts),
     "--upscale_only", str(c.upscale_only)])
    PID_list.append(pid_obj(R.pid, 'dainfu_'))

#start_another_instance(c, pip)


def add_audio_and_subs(c):
    process = sp.Popen([f'ffmpeg',  '-i',  
    f'{c.joined_file}', '-i', f'{c.input_file}',
    '-c',   "copy",   '-map',   "0:v",      '-c',   "copy",   '-map',   "1:a",   '-map', '1:s?',  '-c:s', 'mov_text', f'{c.final_file}',
    '-loglevel', '-8'])
    process.wait()
    print(f"{c.log} Added audio and subtitles")

def join_parts(c ):
    file_list = f'{c.process_dir}/files.txt'
    try: f = open(file_list, "w")
    except:    pass
    for x in range(c.nb_parts_tot):
        f.writelines([f"\nfile '{c.process_dir}/{x:04}.mp4'"])
        x+=1
    f.close()

    (
    ffmpeg
        .input(file_list, format='concat', safe=0)
        .output(c.joined_file, c='copy')
        .overwrite_output()
        .run()
    )
    add_audio_and_subs(c)


def find_parts(self):
    part_indexes = []
    if self.selective_interpolation == 0:
        part_indexes_even = []
        part_indexes_odd = []
        for x in range(self.nb_parts_tot):
            if x % 2 == 0:
                part_indexes_even.append(x)
                part_indexes_odd.append(x+1)
        part_indexes_even.append(None)
        part_indexes_odd.append(None)

        return part_indexes_even, part_indexes_odd

    if self.dual_instance == 0:
        for x in range(self.nb_parts_tot):
            if x %2 == 0:
                part_indexes.append(x)
    elif self.dual_instance:
        if self.instance_id == 0:
            for x in range(self.nb_parts_tot):
                if x % 4 == 0:
                    part_indexes.append(x)
        elif self.instance_id == 1:
            for x in range(self.nb_parts_tot):
                if x % 4 == 0:
                    part_indexes.append(x+2)
    part_indexes.append(None)

    return part_indexes

def get_tot_frames(input_file):
    import cv2
    cap= cv2.VideoCapture(input_file)
    totalframecount= int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print("The total number of frames in this video is ", totalframecount)
    return totalframecount

def find_ffmpeg_bin(self):
    ffmpeg_bin = "../ffmpeg-4.3.2/ffmpeg"
    if os.path.isfile(ffmpeg_bin)  == False:
        ffmpeg_bin = "../Dainfux/ffmpeg-4.3.2/ffmpeg"
        if os.path.isfile(ffmpeg_bin)  == False:
            print("modified ffmpeg binary missing")
            sys.exit()
        else:
            print("Using pre-built ffmpeg binary")    
            return ffmpeg_bin
    return ffmpeg_bin

def find_waifu2x_bin(self):
    waifu2x_bin = "../waifu2x-ncnn-vulkan/build/waifu2x-ncnn-vulkan"
    if os.path.isfile(waifu2x_bin)  == False:
        waifu2x_bin = "../Dainfux/waifu2x-ncnn-vulkan-20210210/build/waifu2x-ncnn-vulkan"
        if os.path.isfile(waifu2x_bin)  == False:
            print("waifu2x binary missing")
            sys.exit()
        else:
            print("Using pre-built waifu2x binary")    
            return waifu2x_bin
    return waifu2x_bin

def modify_wtinterpolate_data(self):
    nb_items_rm = abs(self.wti_offset-1)
    for y in range(len(self.wtinterpolate_data)):
        for z in range(nb_items_rm):
            if nb_items_rm > 0:
                self.wtinterpolate_data[y].pop(0)
                self.wtinterpolate_data[y].append(0)
            elif nb_items_rm < 0:
                self.wtinterpolate_data[y].insert(0, 0)
                self.wtinterpolate_data[y].pop(len(self.wtinterpolate_data[y])-1)
def generate_part_data(self):
    part_data = []

    block_time = 24

    if self.mode == 'interpolate_all':
        offset = 1
        nb_photosensitive_frames = block_time
        interpolate_part = 1
    elif self.mode == 'upscale_all':
        offset = 0
        nb_photosensitive_frames = 0
        interpolate_part = 0

    tot_frames = get_tot_frames(self.input_file)
    nb_parts = tot_frames // block_time
    rem = tot_frames % block_time
    #if rem:  nb_parts +=1

    start = 0
    end = block_time

    if self.mode == 'upscale_all':
        for u in range(nb_parts):
            part_data.append((u, start, end, 0, block_time, 0))
            start += block_time
            end += block_time
        if rem:
            part_data.append((u, start, tot_frames, 0, rem, 0))
    elif self.mode == 'interpolate_with_downscale':
        for u in range(nb_parts):
            part_data.append((u, start, end, 1, block_time, block_time))
            start += block_time
            end += block_time
        if rem:
            part_data.append((u, start, tot_frames, 1, rem, rem))
    return part_data
def gen_debug_parts(self):
    part_data = []
    block_size = 24
    start = 0
    end = block_size
    for x in range(self.debug_nb_parts):
        if x % 2 == 0:
            wti  = 1; offset = 1; wti2 = block_size
        else:
            wti =0; offset = 0; wti2 = 0
        part_data.append((x, start, end+offset, wti, block_size, wti2))
        start += block_size
        end += block_size
    return part_data
class context:        

    def __init__(self, args):
        self.filename = os.path.basename(args.input_file)
        self.filename_no_ext, self.file_extension = os.path.splitext(self.filename)
        self.instance_id = args.instance_id
        self.PID_list = []
        self.input_file = args.input_file
        self.output_dir = args.output_dir
        self.process_dir = self.output_dir + '/' + self.filename_no_ext

        self.mode = args.mode
        self.pipe_counter_t = 0
        self.pipe_counter_i = 0
        self.selective_interpolation = args.selective_interpolation
        self.waifu2x_scale = args.waifu2x_scale
        self.upscale_only = args.upscale_only
        self.ph_this_bad_th = args.ph_this_bad_th



        self.ffmpeg_bin = find_ffmpeg_bin(self)
        self.waifu2x_bin = find_waifu2x_bin(self)
        self.log = f"Dain ID {args.instance_id}:"

        self.use_newbadness = args.use_newbadness

        self.overwrite = args.overwrite
        self.ffmpeg_log_level = args.ffmpeg_log_level
        self.ffmpeg_codec = args.ffmpeg_codec
        self.time_step = args.time_step

        self.file_info = get_file_info(self.input_file)
        self.input_resolution = [int(self.file_info[0]), int(self.file_info[1])]
        self.input_fps = self.file_info[2]
        if self.upscale_only == 0:
            self.target_fps = self.input_fps / self.time_step
        else: self.target_fps = self.input_fps

        self.joined_file =  f'{self.output_dir}joined_{os.path.splitext(self.filename)[0]}.mp4'
        self.final_file = f'{self.output_dir}{os.path.splitext(self.filename)[0]}_{round(float(self.target_fps))}fps.mp4'

        self.input_resolution_s =  f"{self.input_resolution[0]}x{self.input_resolution[1]}"
        if self.upscale_only == 1:
            self.target_resolution = [self.input_resolution[0]*self.waifu2x_scale,self.input_resolution[1]*self.waifu2x_scale, ]
        else: self.target_resolution = self.input_resolution
        self.target_resolution_s = f"{self.target_resolution[0]}x{self.target_resolution[1]}"
        if self.selective_interpolation == 1:# and self.waifu2x_scale != 0:
            self.intro_skip = args.intro_skip
            self.ending_skip = args.ending_skip       
            if not os.path.isfile(self.process_dir + '/' + 'parts.txt'):
                if args.instance_id == 0:
                    get_part_data(self)
            self.part_data = read_data(self, 'parts')
            self.wtinterpolate_data =  read_data(self, 'wtinterpolate')
            if self.instance_id == 0:
                self.wti_offset = find_wti_offset(self)
            else: 
                print(f"{self.log} Getting wti from argument: {args.wti_offset} ")
                self.wti_offset = args.wti_offset
            #if self.wtinterpolate_data != 0:
            modify_wtinterpolate_data(self)

        else:
            self.part_data = generate_part_data(self)
            self.wtinterpolate_data = None
        self.nb_parts_tot = len(self.part_data)


        self.imgs_per_frame = int((self.target_fps * 1001 / 1000) / (self.input_fps * 1001 / 1000))
        self.intermediate_frames = self.imgs_per_frame - 1

        self.upscale_resolution_s =  args.upscale_resolution
        self.downscale_resolution_s = args.downscale_resolution
        self.upscale_resolution = list(map(int, args.upscale_resolution.split('x')))
        if self.waifu2x_scale != 0:
            self.downscale_resolution = [self.input_resolution[0]//self.waifu2x_scale, self.input_resolution[1]//self.waifu2x_scale]
        else: self.downscale_resolution = None
        self.start_offset = args.start_offset
        self.dual_instance = args.dual_instance
        self.waifu2x_model = args.waifu2x_model 
        if os.path.isdir(self.process_dir) == False:
            os.makedirs(self.process_dir)
        self.part_indexes = None
        if self.selective_interpolation == 0 and self.mode != 'upscale_all':
            self.part_indexes_even, self.part_indexes_odd = find_parts(self)
        else:
            self.part_indexes = find_parts(self)
        self.index_counter = 0
        if args.debug_nb_parts:
            self.debug_nb_parts = args.debug_nb_parts
            self.nb_parts_tot = self.debug_nb_parts
        else:
            self.debug_nb_parts = 0
        self.debug_parts = gen_debug_parts(self)
        if args.use_debug_parts and self.selective_interpolation == 1:
            self.part_data = self.debug_parts

        if args.count_ph:
            get_tot_photosensitive_frames(self)
            sys.exit()
        else: self.tot_frames_to_int = get_tot_photosensitive_frames(self)

    def add_more(self, image_io_reader, frames_list, PID_list):
        self.R = image_io_reader
        self.frames = frames_list
    def reset_vals(self):
        self.frames.clear()
        self.index_counter= 0
        # self.pipe_counter_t = 0
        # self.pipe_counter_i = 0
