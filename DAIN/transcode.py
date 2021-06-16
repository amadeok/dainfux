import os, sys, io, signal, fcntl, subprocess as sp
import PIL, imageio
from various import * #create_pipes, open_fifo, pipe_array, check_key_presses, draw_index_and_save, ret_pipe_desc, transcode
from utils import *
import argparse
args = None

class frame_obj:
    def __init__(self, frame, index):
        self.frame  = frame
        self.index = index

def get_args():
    parser = argparse.ArgumentParser(description='transcode')

    parser.add_argument('--time_step',  type=float, default=0.5, help='choose the time steps')

    parser.add_argument('--input_file', type = str, default = '/content/DAIN/input_frames', help='input directory')
    parser.add_argument('--output_dir', type = str, default = '/content/DAIN/output_frames', help='output directory')
    parser.add_argument('--parts_data_dir', type = str, default = os.getcwd(), help='directory where to save part data')

    parser.add_argument('--ffmpeg_log_level', type = int, default = 32, help='ffmpeg_log_level')
    parser.add_argument('--ffmpeg_codec', type = str, default = 'libx264', help='ffmpeg_codec')

    parser.add_argument('--overwrite', type = int, default = 0, help='overwrite')

    args = parser.parse_args()
    return args 
def write_list(frames):
    with open(f"{os.getcwd()}/fraemes", 'w+') as out:    
        for (i, item) in enumerate(frames, start=1):
            out.write(str(str(i) + ' ' + str(item) + '\n'))

PID_list =  []
frames = []
def transcode_v2(c):
         
    R = imageio.read(c.input_file, "ffmpeg")
    count = 0
    need_to_retranscode = 0
    
    def index():
        return R._BaseReaderWriter_last_index

    
    if not check_missing(c, 0):
        return 0
    for x in range(c.nb_parts_tot):
        curr_file = f"{c.process_dir}/{count:04}.mp4"

        if c.part_data[count][3] == 0 and not check_file(c, count, curr_file) or c.part_data[count][3] == 0 and c.overwrite: #:
            t0 = time.time()
            start_frame = c.part_data[count][1]
            final_frame = c.part_data[count][2]
            #R.set_image_index(start_frame)

            #frames.append(frame_obj(R.get_next_data(), R._BaseReaderWriter_last_index))
            start_interpolate_ffmpeg(PID_list, f'{count:0>4d}', c, 'transcode')      
            
            fd2 = open_fifo('ffmpeg_pipe', 'transcode', c)

            while index() < final_frame-1:
                frames.append(frame_obj(R.get_next_data(), R._BaseReaderWriter_last_index))

                F0 =  draw_index_and_save(frames[index()], 'aT', None, None) #frame a
                LPB = index().to_bytes(2, 'little') + b'\x61'
                #F0.convert('RGBA').save("test0.bmp")
                for x in range(c.imgs_per_frame):
                    pipe_array(F0.convert('RGBA'), 'to_bytes',  b'\x00\x00\x00', LPB,  'ffmpeg')#pipe the first frame at original resolution
                frames[index()] = None    
                #try: frames[index()-1] = None
                #except: pass    
            #write_list(frames)
            print(f"transcode part {count} with  {c.part_data[count][4]-1} frames  took {time.time() - t0}")

            os.close(fd2)
        elif c.part_data[count][3] == 0: #part exists, skipping
            for x in range(c.part_data[count][4]):
                frames.append(frame_obj(R.get_next_data(), R._BaseReaderWriter_last_index))
                frames[index()] = None
            #write_list(frames)
        else:
            for x in range(c.part_data[count][4]):
                frames.append(frame_obj(R.get_next_data(), R._BaseReaderWriter_last_index))
                frames[index()] = None
            #write_list(frames)


        count +=1
    

args = str(sys.argv)
alone = 0
if "--alone" in sys.argv:
    ret = sys.argv.remove("--alone")
    alone = 1
if alone:
    args = get_args()
    part_data = read_data(args.parts_data_dir, 'parts')
    c = context(args, part_data, None)

    transcode_v2(c)

