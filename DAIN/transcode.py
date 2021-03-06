import os, sys, io, signal, fcntl, subprocess as sp
import PIL, imageio
from various import * #create_pipes, open_fifo, pipe_array, check_key_presses, draw_index_and_save, ret_pipe_desc, transcode
from utils import *
import argparse
from my_args import args
args_ = None

class frame_obj:
    def __init__(self, frame, index):
        self.frame  = frame
        self.index = index

def get_args_():
    parser = argparse.ArgumentParser(description='transcode')

    parser.add_argument('--time_step',  type=float, default=0.5, help='choose the time steps')

    parser.add_argument('--input_file', type = str, default = '/content/DAIN/input_frames', help='input directory')
    parser.add_argument('--output_dir', type = str, default = '/content/DAIN/output_frames', help='output directory')
    parser.add_argument('--parts_data_dir', type = str, default = os.getcwd(), help='directory where to save part data')

    parser.add_argument('--ffmpeg_log_level', type = int, default = 32, help='ffmpeg_log_level')
    parser.add_argument('--ffmpeg_codec', type = str, default = 'libx264', help='ffmpeg_codec')

    parser.add_argument('--overwrite', type = int, default = 0, help='overwrite')

    args_ = parser.parse_args_()
    return args_ 


def write_list(frames):
    with open(f"{os.getcwd()}/fraemes", 'w+') as out:    
        for (i, item) in enumerate(frames, start=1):
            out.write(str(str(i) + ' ' + str(item) + '\n'))

PID_list =  []
frames = []
def transcode_v2(c):

    # if c.met['codec_name'] != 'hevc':
    #     R = imageio.get_reader(c.input_file, format="ffmpeg", input_params=c.decoder_input_param, output_params=c.decoder_output_param)
    # else:
    #     R = imageio.get_reader(c.input_file, format="ffmpeg")
    R = vapoursynth_setup(c)
    check_fps(c)

    count = 0
    need_to_retranscode = 0
    
    def index():
        return R.index

    
    if not check_missing(c, 0):
        return 0
    for x in range(c.nb_parts_tot):
        curr_file = f"{c.process_dir}/{count:04}.mp4"

        if c.part_data[count][3] == 0 and not check_file(c, count, curr_file) or c.part_data[count][3] == 0 and c.overwrite: #:
            t0 = time.time()
            start_frame = c.part_data[count][1]
            final_frame = c.part_data[count][2]
            #R.set_image_index(start_frame)

            #frames.append(frame_obj(R.get_next_data(), R.index))
            start_interpolate_ffmpeg(PID_list, f'{count:0>4d}', c, 'transcode')      
            
            fd2 = open_fifo('ffmpeg_pipe', 'transcode', c)

            while R.index < final_frame-1:
                frames.append(frame_obj(R.get_next_data(), R.index))

                F0 =  draw_index_and_save(frames[R.index], 'aT', None, None) #frame a
                LPB = R.index.to_bytes(2, 'little') + b'\x61'
                #F0.save('test.bmp')

                for x in range(c.imgs_per_frame):
                    pipe_array(F0, 'to_bytes',  b'\x00\x00\x00', LPB,  'ffmpeg')#pipe the first frame at original resolution
                frames[R.index] = None    
                #try: frames[R.index-1] = None
                #except: pass    
            #write_list(frames)
            print(f"transcode part {count} with  {c.part_data[count][4]-1} frames  took {time.time() - t0}")

            os.close(fd2)
        elif c.part_data[count][3] == 0: #part exists, skipping
            for x in range(c.part_data[count][4]):
                frames.append(frame_obj(R.get_next_data(), R.index))
                frames[R.index] = None
            #write_list(frames)
        else:
            for x in range(c.part_data[count][4]):
                frames.append(frame_obj(R.get_next_data(), R.index))
                frames[R.index] = None
            #write_list(frames)


        count +=1
    

args_ = str(sys.argv)
alone = 0

if "--alone" in sys.argv:
    ret = sys.argv.remove("--alone")
    alone = 1

if alone:
    args_ = get_args_()
    part_data = read_data(args_.parts_data_dir, 'parts')
    c = context(args_, part_data, None)

    transcode_v2(c)

