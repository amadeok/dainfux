#from MegaDepth.util.util import mkdir
import os, sys, distro, time
import psutil
import GPUtil
import subprocess as sp
import ffmpeg, math, cv2, imageio
import numpy as np
from PIL import Image
import various  
import vapoursynth as vs
from vapoursynth import core
from datetime import datetime, timedelta
from my_args import args
core.std.LoadPlugin(path='/usr/local/lib/libffms2.so') 

t_counter = 0;t0 = 0
def t(text=None):
    global t_counter;global t0
    t_counter+=1
    if t_counter == 1:
        t0 = time.time()
    elif t_counter == 2:
        t_counter = 0
        print(f"{text} {time.time()-t0}")
    return time.time()

def read_data(c, file_name, no_skip=None):
    if no_skip == None:
        parts_dir = c.process_dir
    else: 
        parts_dir = c.process_dir + "/" + "temp2"
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

def time_step_calculation(ctx, input_file):
    INPUT_FILEPATH = input_file
    cap = cv2.VideoCapture(INPUT_FILEPATH)
    first_fps = cap.get(cv2.CAP_PROP_FPS)
    time_step = ctx.input_fps/first_fps
    return time_step

def get_file_info(input_file):
    import cv2
    cap = cv2.VideoCapture(input_file)
    width  = cap.get(cv2.CAP_PROP_FRAME_WIDTH)   # float `width`
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)  
    input_fps = cap.get(cv2.CAP_PROP_FPS)
    return [width, height, input_fps]

def interpret_intro_end(string ):
    string_l = string.split('-')
    start = string_l[0].split(':') 
    start_sec = (int(start[0])*60)+int(start[1])

    end = string_l[1].split(':') 
    end_sec = (int(end[0])*60)+int(end[1])
    return start_sec, end_sec

def get_part_data(c, no_skip=None):
    print("Extracting data")
    if no_skip == None:
        i_s, i_e = interpret_intro_end(c.intro_skip)
        e_s, e_e = interpret_intro_end(c.ending_skip)
        target_dir = c.process_dir
    else:
        print("Data extractor with no skip")
        i_s, i_e, e_s, e_e = 0, 0, 0, 0
        target_dir = c.process_dir + "/" + "temp2"
        if os.path.isdir(target_dir) == False:
            os.mkdir(target_dir)

    if not os.path.isfile(c.input_file):
        print("Input file not found, exiting")
        sys.exit()
    vf = f"photosensitivity=bypass=1:export_data=4:is={i_s}:ie={i_e}:os={e_s}:oe={e_e}:f=24:target_dir='{target_dir}':log=0:this_badness_thres={c.ph_this_bad_th}:use_newbadness={c.use_newbadness} "
    cmd =  f"{c.ffmpeg_bin} -i '{c.input_file}' -vf {vf} -loglevel 32 -f null  /dev/null > dump"
    if no_skip == None:
        subp = sp.call([f"{c.ffmpeg_bin}", f"-i", f'{c.input_file}', "-vf", f"{vf}", "-loglevel", "32", "-f", "null",  "/dev/null"])
        #subp.wait()
        print("Part data extraction finished")
    else:
        subp = sp.Popen([f"{c.ffmpeg_bin}", f"-i", f'{c.input_file}', "-vf", f"{vf}", "-loglevel", "32", "-f", "null",  "/dev/null"])
        return subp.pid


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
    try: 
      while loop_nb <= c.nb_parts_tot:
          if check_index(c, loop_nb):
              u += c.part_data[loop_nb][5]
              if c.part_indexes[c.index_counter] == None:
                  break
          if loop_nb == 5:
              pass
          loop_nb += 1
      print(f"{c.log}Total number of frames to interpolate: {u}")    
    except:  print(f"{c.log}Total number of frames to interpolate: {u}")
    #print(f"{c.log}Interpolation bypass: {int_bypass}")
    #except: print(f"Total number of frames to interpolate: {u}")
    return u


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
    pixel_format = 'rgb24'
    vf = f"photosensitivity=bypass=1:export_data=4:is=0:ie=0:os=0:oe=0:f=24:target_dir='{c.process_dir}/test':log=33:this_badness_thres={c.ph_this_bad_th}:use_newbadness={c.use_newbadness}"

    ffmpeg_pipe = f"/tmp/ffmpeg_pipe__0_id{c.instance_id}"
    cmd_command = [f'{c.ffmpeg_bin}',  
                '-color_primaries', c.color_primaries_ff,
              '-color_trc', c.color_transfer_ff,
               '-color_range', c.color_range_ff,
                '-colorspace', c.color_space_ff, 
                '-r', f'{c.target_fps}', '-pix_fmt', pixel_format, '-s', c.target_resolution_s,
        '-f', 'rawvideo', '-i',  ffmpeg_pipe, '-vf', vf, '-f', 'null',  '/dev/null',  '-loglevel', '-8']# '>', f'dump']
    execute = sp.Popen(cmd_command, stdout=sp.PIPE,     stderr=sp.PIPE )

    return execute


def start_interpolate_ffmpeg(PID_list, output_file, c, transcode):

    if transcode:  pipe_count = c.pipe_counter_t
    else:           pipe_count = c.pipe_counter_i

    ffmpeg_pipe = f"/tmp/ffmpeg_pipe_{transcode}_{pipe_count}_id{c.instance_id}"
    input_pixel_format = 'rgb24' #'rgb24' 
    output_pixel_format = 'yuv420p' #'rgb24' 

    print(f"{c.log} starting ffmpeg with {transcode} fifo: {ffmpeg_pipe}")

    if os.path.exists(ffmpeg_pipe) == False:
        try: os.mkfifo(ffmpeg_pipe)
        except: pass

    # if transcode:
    #     pixel_format = 'rgb24'
    codec = "libx264" 

    vf_command =  ""
    cmd_command = ['ffmpeg',  '-r', f'{c.target_fps}', 
             '-pix_fmt', input_pixel_format, 
             '-s', c.target_resolution_s, 
                '-color_primaries', c.color_primaries_ff,
              '-color_trc', c.color_transfer_ff,
               '-color_range', c.color_range_ff,
                '-colorspace', c.color_space_ff, 
            '-f', 'rawvideo', '-i',  ffmpeg_pipe, '-vcodec', codec, '-preset', 'medium', '-crf', '18', '-tune', 'animation',
           # '-vf', c.decoder_output_param[1], 
            '-pix_fmt', output_pixel_format,
                '-color_primaries', c.color_primaries_ff,
              '-color_trc', c.color_transfer_ff,
               '-color_range', c.color_range_ff,
                '-colorspace', c.color_space_ff, 
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
    "-z", str(c.upscale_only), "-b", str(c.waifu2x_verbose)])
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
    dist = distro.linux_distribution()
    print(os.getcwd())
    ffmpeg_bin = "../ffmpeg-4.3.2/ffmpeg"
    if os.path.isfile(ffmpeg_bin)  == False:
        ffmpeg_bin = f"../Dainfux/ffmpeg-4.3.2/ubuntu{dist[1]}/ffmpeg"
        if os.path.isfile(ffmpeg_bin)  == False:
            if os.path.isdir(f"../Dainfux/") == False:
                print("Dainfux directory missing")
            print("modified ffmpeg binary missing: ", ffmpeg_bin)
            sys.exit()
        else:
            print("Using pre-built ffmpeg binary")    
            return ffmpeg_bin
    return ffmpeg_bin

def find_waifu2x_bin(self):
    dist = distro.linux_distribution()
    waifu2x_bin = "../waifu2x-ncnn-vulkan/build/waifu2x-ncnn-vulkan"
    if os.path.isfile(waifu2x_bin)  == False:
        waifu2x_bin = f"../Dainfux/waifu2x-ncnn-vulkan-20210210/build/ubuntu{dist[1]}/waifu2x-ncnn-vulkan"
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

    self.tot_frames = get_tot_frames(self.input_file)
    nb_parts = self.tot_frames // block_time
    rem = self.tot_frames % block_time
    #if rem:  nb_parts +=1

    start = 0
    end = block_time

    if self.mode == 'upscale_all':
        for u in range(nb_parts):
            part_data.append((u, start, end, 0, block_time, 0))
            start += block_time
            end += block_time
        if rem:
            part_data.append((u, start, self.tot_frames, 0, rem, 0))
    elif self.mode == 'interpolate_with_downscale':
        for u in range(nb_parts):
            part_data.append((u, start, end, 1, block_time, block_time))
            start += block_time
            end += block_time
        if rem:
            part_data.append((u, start, self.tot_frames, 1, rem, rem))
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

def get_video_metadata(c):
  vid = ffmpeg.probe(c.input_file)
  streams = vid['streams']
  for x in range(len(streams)):
    if streams[x]['codec_type'] == 'video':
      #print(streams[x])
      return streams[x]
 # asdas
ffmpeg_vs = {
    #space
    'rgb': 'rgb',
    'bt709': '709',
    'fcc': 'fcc',
    'bt470bg': '470bg',
    'smpte170m': '170m',
    'smpte240m': '240m',
    'ycocg': 'ycgco',
    'bt2020nc': '2020ncl',
    'bt2020_ncl': '2020ncl',
    'bt2020c': '2020cl',
    'bt2020_cl': '2020cl',
    'smpte2085': 'unspec',
    'chroma-derived-nc': 'chromancl',
    'chroma-derived-c': 'chromacl',
    'ictcp': 'ictcp',
    #color_trc
    'bt709': '709',
    'gamma22': '470m',
    'gamma28': '470bg',
    'smpte170m': 'unspec', #?
    'smpte240m': '240m',
    'linear': 'linear',
    'log': 'log100', #?
    'log100': 'log100',
    'log_sqrt': 'log316',
    'log316': 'log316',
    'iec61966_2_4': 'xvycc',
    'iec61966-2-4': 'xvycc',
    'bt1361': 'unspec',
    'bt1361e': 'unspec',
    'iec61966_2_1': 'srgb',
    'iec61966-2-1': 'srgb',
    'bt2020_10': '2020_10',
    'bt2020_10bit': '2020_10',
    'bt2020_12': '2020_12',
    'bt2020_12bit': '2020_12',
    'smpte2084': 'st2084',
    'smpte428': 'unspec',
    'smpte428_1': 'unspec',
    'arib-std-b67': 'std-b67',
    #color_primaries
    'bt709': '709',
    'bt470m': '470m',
    'bt470bg': '470bg',
    'smpte170m': '170m',
    'smpte240m': '240m',
    'film': 'film',
    'bt2020': '2020',
    'smpte428': 'xyz',
    'smpte428_1': 'xyz',
    'smpte431': 'st431-2',
    'smpte432': 'st432-1',
    'jedec-p22': 'jedec-p22',
    #range
    'tv': 'limited',
    'mpeg': 'limited',
    'pc': 'full',
    'jpeg': 'full',

}


def define_color_attr(c):
    
    def set_(str):
        if str in c.met.keys():
            value = ffmpeg_vs[c.met[str]]
            value_ff = c.met[str]
            if value == 'unspec':
                if str == "color_range":
                    value =  'limited'; value_ff = 'tv'
                else: value = '709'; value_ff = 'bt709'
                print(f"{c.log} Defaulting {str} to:  {value }")
            else:
                print(f"{c.log} Using {str} from metadata:   {value }")
        else:
            if str == "color_range":
                 value =  'limited'; value_ff = 'tv'
            else: value = value = '709'; value_ff = 'bt709'
            print(f"{c.log} Defaulting {str} to:  {value }")

        setattr(c, str, value)
        setattr(c, str+'_ff', value_ff)

    set_('color_range')
    set_('color_primaries')
    set_('color_space')
    set_('color_transfer')

    c.decoder_input_param = ["-color_primaries", c.color_primaries, "-color_trc", c.color_transfer,  
                            "-colorspace", c.color_space, "-color_range", c.color_range]

    c.decoder_output_param = ["-vf", f"colorspace=primaries={c.color_primaries}:trc={c.color_transfer}:space={c.color_space}:range={c.color_range}" ]
    return c.decoder_input_param, c.decoder_output_param

def check_fps(ctx):
    first = ctx.process_dir + '/' + '0000.mp4'
    if os.path.isfile(first):
        prev = ctx.time_step
        ctx.time_step = time_step_calculation(ctx, first)
        print(f"{ctx.log} found existing file 0000.mp4 with time step {ctx.time_step}, overwriting user settings: {prev}")

def vapoursynth_setup(c):
    class vs_reader:
        def __init__(self, c):
            self.index = -1
            if args.use_ffmpeg_dec == 0:
                self.video = core.ffms2.Source(source=c.input_file)
                first = self.video.get_frame(0)
                self.vs_metadata = first.props
                first = None
                self.video = core.resize.Bicubic(clip=self.video, format=vs.RGB24, matrix_in_s=c.color_space, transfer_in_s=c.color_transfer , primaries_in_s=c.color_primaries ,range_in_s=c.color_range)
                self.generator = self.video.frames()
            else:
                self.reader = imageio.read(c.input_file, "ffmpeg")
        def get_next_data(self):
            self.index +=1
            if args.use_ffmpeg_dec == 0:
                frame = next(self.generator)
                r = np.array(frame.get_read_array(0))
                g = np.array(frame.get_read_array(1))
                b = np.array(frame.get_read_array(2))
                #rgb = np.dstack((r,g,b)) 
                return cv2.merge((r, g, b)) 
            else: 
                return self.reader.get_next_data()


    
    return vs_reader(c)


class context:        

    def __init__(self, args):
        self.filename = os.path.basename(args.input_file)
        self.filename_no_ext, self.file_extension = os.path.splitext(self.filename)
        self.instance_id = args.instance_id
        self.PID_list = []
        self.input_file = args.input_file
        print("Input file:",  self.input_file)
        if os.path.isfile(self.input_file) == False:
            print("Input file missing, exiting")
            sys.exit()

        self.output_dir = args.output_dir
        self.process_dir = self.output_dir + '/' + self.filename_no_ext
        if os.path.isfile(f"{self.process_dir}/FINISHED.txt") == True and args.count_ph == 0:
            print("Processing for this file has already been done, exiting")
            sys.exit()
        self.mode = args.mode
        self.pipe_counter_t = 0
        self.pipe_counter_i = 0
        self.selective_interpolation = args.selective_interpolation
        self.waifu2x_scale = args.waifu2x_scale
        self.upscale_only = args.upscale_only
        self.ph_this_bad_th = args.ph_this_bad_th


        self.waifu2x_verbose = args.waifu2x_verbose

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
        
        check_fps(self)

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

        self.met = get_video_metadata(self)
        define_color_attr(self)
        if args.count_ph == 0:
            self.R = vapoursynth_setup(self)

        if self.selective_interpolation == 1:# and self.waifu2x_scale != 0:
            self.intro_skip = args.intro_skip
            self.ending_skip = args.ending_skip       
            if not os.path.isfile(self.process_dir + '/' + 'parts.txt'):
                if args.instance_id == 0:
                    get_part_data(self)
            self.part_data = read_data(self, 'parts')
            self.wtinterpolate_data =  read_data(self, 'wtinterpolate')

            if self.instance_id == 0 and args.count_ph == 0:
                self.wti_offset = various.find_wti_offset(self)
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

        if args.count_ph == 1:
            get_tot_photosensitive_frames(self)
            sys.exit()
        else: 
            self.tot_frames_to_int = get_tot_photosensitive_frames(self)
        self.tot_frames = get_tot_frames(self.input_file)
        self.nb_interpolated_frames = 0
        self.skept_frames = 0
        self.tot_frames_to_skip = int(self.tot_frames) - self.tot_frames_to_int
        self.skil_avg = 0
    def perc(self):
        return self.nb_interpolated_frames / self.tot_frames_to_int * 100

    def time_left(self):
        remaining_frames = self.tot_frames_to_int - self.nb_interpolated_frames
        remaining_frames_skip = self.tot_frames_to_skip -  self.skept_frames 
        str_ = ''
        tot_sec = remaining_frames*self.loop_timer.avg + remaining_frames_skip*self.skil_avg
        sec = timedelta(seconds=int(tot_sec))
        try: 
            d = datetime(1,1,1) + sec
            str_ = str("%dd:%dh:%dm:%ds" % (d.day-1, d.hour, d.minute, d.second))
        except: pass
        return str_

    def add_more(self, image_io_reader, frames_list, PID_list):
        self.R = image_io_reader
        self.frames = frames_list
    def reset_vals(self):
        self.frames.clear()
        self.index_counter= 0
        # self.pipe_counter_t = 0
        # self.pipe_counter_i = 0
