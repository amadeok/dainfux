import time
import os, sys, io, signal, fcntl, subprocess as sp
import numpy as np
import numpy
from my_args import args
from imageio import imread, imsave
import shutil
import datetime
from various import * #create_pipes, open_fifo, pipe_array, check_key_presses, draw_index_and_save, ret_pipe_desc, transcode
from utils import *

import termios, tty, threading
import cv2, struct
from PIL import Image, ImageDraw
import PIL, imageio
import warnings
warnings.filterwarnings("ignore")
from transcode import transcode_v2


if args.upscale_only == 0 and args.count_ph == 0:
    import torch
    import networks
    torch.backends.cudnn.benchmark = True
    from torch.autograd import Variable
    from AverageMeter import  *

ffmpeg_pipe = f"/tmp/ffmpeg_pipe"
frame_id = '1a'
cdir = os.getcwd()

settings = []

pipe_to_ffmpeg =1

if args.waifu2x_scale != 0:
    pipe_to_waifu = 1

directory = f'{cdir}'

signals = bytearray(b'\x00\x01\x00')

part_data = []

def vram_init(dummy_img):
    X0 = torch.from_numpy(np.transpose(dummy_img, (2,0,1)).astype("float32") / 255.0).type(args.dtype)
    X1 = torch.from_numpy(np.transpose(dummy_img, (2,0,1)).astype("float32") / 255.0).type(args.dtype)
    intWidth = X0.size(2)
    intHeight = X0.size(1)
    channels = X0.size(0)
    if intWidth != ((intWidth >> 7) << 7):
        intWidth_pad = (((intWidth >> 7) + 1) << 7)  # more than necessary
        intPaddingLeft = int((intWidth_pad - intWidth) / 2)
        intPaddingRight = intWidth_pad - intWidth - intPaddingLeft
    else: 
        intPaddingLeft = 32
        intPaddingRight= 32
    if intHeight != ((intHeight >> 7) << 7):
        intHeight_pad = (((intHeight >> 7) + 1) << 7)  # more than necessary
        intPaddingTop = int((intHeight_pad - intHeight) / 2)
        intPaddingBottom = intHeight_pad - intHeight - intPaddingTop
    else: 
        intPaddingTop = 32
        intPaddingBottom = 32
    pader = torch.nn.ReplicationPad2d([intPaddingLeft, intPaddingRight, intPaddingTop, intPaddingBottom])
    X0 = Variable(torch.unsqueeze(X0,0))
    X1 = Variable(torch.unsqueeze(X1,0))
    X0 = pader(X0)
    X1 = pader(X1)
    if args.use_cuda:
        X0 = X0.cuda()
        X1 = X1.cuda()
    y_s, offset, filter = model(torch.stack((X0, X1),dim = 0))


c = context(args)
c.PID_list.append(pid_obj(os.getpid(), '1dain'))


#join_parts(c)
start_it = 1
if c.waifu2x_scale != 0 and start_it:
    start_waifu2x(c, c.PID_list)
if args.count_ph == 0:
    thread1 = threading.Thread(target=check_key_presses, args=(c.PID_list, signals, c))
    thread1.start()


if args.enable_transcoder or args.count_ph == 2:
    start_time = time.time()
    print(f"{c.log} Starting transcode")

    transcode_v2(c)
    print(f"{c.log}transcode took ",time.time() - start_time)
    #transcode_t = threading.Thread(taR.get=transcode, args=(c,))
    #transcode_t.start()
    if args.count_ph: sys.exit()
#time.sleep(10)
bypass = 0


if bypass == 0 and c.upscale_only == 0:
    model = networks.__dict__[args.netName](
                                        channel = args.channels,
                                        filter_size = args.filter_size,
                                        timestep = args.time_step,
                                        training = False)

    if args.use_cuda:
        model = model.cuda()
    model_path = './model_weights/best.pth'
    if not os.path.exists(model_path):
        print(f"{c.log}*****************************************************************")
        print(f"{c.log}**** We couldn't load any trained weights ***********************")
        print(f"{c.log}*****************************************************************")
        exit(1)

    if args.use_cuda:
        pretrained_dict = torch.load(model_path)
    else:
        pretrained_dict = torch.load(model_path, map_location=lambda storage, loc: storage)

    model_dict = model.state_dict()
    # 1. filter out unnecessary keys
    pretrained_dict = {k: v for k, v in pretrained_dict.items() if k in model_dict}
    # 2. overwrite entries in the existing state dict
    model_dict.update(pretrained_dict)
    # 3. load the new state dict
    model.load_state_dict(model_dict)
    # 4. release the pretrained dict for saving memory
    pretrained_dict = []

    model = model.eval() # deploy mode

    timestep = args.time_step
    time_offsets = [kk * timestep for kk in range(1, int(1.0 / timestep))]
    torch.set_grad_enabled(False)

loop_timer = AverageMeter()


#########
save_pngs = None #f"{picdir}/tmp/"
#########
cdir = os.getcwd()


if c.waifu2x_scale != 0:
    create_pipes(c)
    pipes = ret_pipe_desc()
    fd1 = pipes[1]


if bypass:
    signals[1] = 0


S = imageio.read(c.input_file, "ffmpeg")
dummy_img = S.get_next_data()
dummy_img = Image.fromarray(dummy_img)

if c.waifu2x_scale != 0 and c.upscale_only == 0:
    dummy_img = dummy_img.resize(c.downscale_resolution)
#do some dummy VRAM initialization
if (c.upscale_only == 0):
    vram_init(dummy_img)

if c.waifu2x_scale != 0:
    pipe_array(dummy_img.convert('RGBA'), 'BytesIO',  signals, b'\x00\x67',  None) # pipe a dummy image to get settings
S = None; dummy_img = None

time.sleep(0.5)
if c.dual_instance and c.instance_id == 0:
    start_another_instance(c,c.PID_list)

frames = []
fd2 = 0

R = imageio.read(c.input_file, "ffmpeg")

c.add_more(R, frames, None)

#draw_index_and_save(frames[0], 'f', save_pngs, (c.downscale_resolution))

def index():
    return c.R._BaseReaderWriter_last_index

def interpolate_and_pipe(c, F0_mod, F1_mod):
    X0 = torch.from_numpy(np.transpose(F0_mod, (2,0,1)).astype("float32") / 255.0).type(args.dtype)
    X1 = torch.from_numpy(np.transpose(F1_mod, (2,0,1)).astype("float32") / 255.0).type(args.dtype)

    assert (X0.size(1) == X1.size(1))
    assert (X0.size(2) == X1.size(2))

    intWidth = X0.size(2)
    intHeight = X0.size(1)
    channels = X0.size(0)
    if not channels == 3:
        print(f"{c.log}Skipping {filename_frame_1}-{filename_frame_2} -- expected 3 color channels but found {channels}.")
        return -1

    if intWidth != ((intWidth >> 7) << 7):
        intWidth_pad = (((intWidth >> 7) + 1) << 7)  # more than necessary
        intPaddingLeft = int((intWidth_pad - intWidth) / 2)
        intPaddingRight = intWidth_pad - intWidth - intPaddingLeft
    else:
        intPaddingLeft = 32
        intPaddingRight= 32

    if intHeight != ((intHeight >> 7) << 7):
        intHeight_pad = (((intHeight >> 7) + 1) << 7)  # more than necessary
        intPaddingTop = int((intHeight_pad - intHeight) / 2)
        intPaddingBottom = intHeight_pad - intHeight - intPaddingTop
    else:
        intPaddingTop = 32
        intPaddingBottom = 32

    pader = torch.nn.ReplicationPad2d([intPaddingLeft, intPaddingRight, intPaddingTop, intPaddingBottom])

    X0 = Variable(torch.unsqueeze(X0,0))
    X1 = Variable(torch.unsqueeze(X1,0))
    X0 = pader(X0)
    X1 = pader(X1)

    if args.use_cuda:
        X0 = X0.cuda()
        X1 = X1.cuda()

    y_s, offset, filter = model(torch.stack((X0, X1),dim = 0))
    y_ = y_s[args.save_which]

    if args.use_cuda:
        X0 = X0.data.cpu().numpy()
        if not isinstance(y_, list):
            y_ = y_.data.cpu().numpy()
        else:
            y_ = [item.data.cpu().numpy() for item in y_]
        offset = [offset_i.data.cpu().numpy() for offset_i in offset]
        filter = [filter_i.data.cpu().numpy() for filter_i in filter]  if filter[0] is not None else None
        X1 = X1.data.cpu().numpy()
    else:
        X0 = X0.data.numpy()
        if not isinstance(y_, list):
            y_ = y_.data.numpy()
        else:
            y_ = [item.data.numpy() for item in y_]
        offset = [offset_i.data.numpy() for offset_i in offset]
        filter = [filter_i.data.numpy() for filter_i in filter]
        X1 = X1.data.numpy()

    X0 = np.transpose(255.0 * X0.clip(0,1.0)[0, :, intPaddingTop:intPaddingTop+intHeight, intPaddingLeft: intPaddingLeft+intWidth], (1, 2, 0))
    y_ = [np.transpose(255.0 * item.clip(0,1.0)[0, :, intPaddingTop:intPaddingTop+intHeight,
                                intPaddingLeft:intPaddingLeft+intWidth], (1, 2, 0)) for item in y_]
    offset = [np.transpose(offset_i[0, :, intPaddingTop:intPaddingTop+intHeight, intPaddingLeft: intPaddingLeft+intWidth], (1, 2, 0)) for offset_i in offset]
    filter = [np.transpose(
        filter_i[0, :, intPaddingTop:intPaddingTop + intHeight, intPaddingLeft: intPaddingLeft + intWidth],
        (1, 2, 0)) for filter_i in filter]  if filter is not None else None
    X1 = np.transpose(255.0 * X1.clip(0,1.0)[0, :, intPaddingTop:intPaddingTop+intHeight, intPaddingLeft: intPaddingLeft+intWidth], (1, 2, 0))

    interpolated_frame_number = 0
    
    for item, time_offset in zip(y_, time_offsets):
        interpolated_frame_number += 1
        item_to_save =  np.round(item).astype(numpy.uint8)

        pilimage = Image.fromarray(item_to_save).convert('RGBA')
        d0 = ImageDraw.Draw(pilimage)
        d0.text((10,10), f"{index()-1}b", fill=(255,255,0))
        if save_pngs:
            pilimage.save(f"{save_pngs}/{index()-1:0>4d}b.png")

        if c.waifu2x_scale != 0:
            LPB = index().to_bytes(2, 'little') + b'\x62'
            pipe_array(pilimage, 'to_bytes',  signals, LPB,  None) #pipe the interpolated frame to waifu
        
        elif c.waifu2x_scale == 0: #we are not upscaling, pipe to ffmpeg directly
            pipe_array(pilimage, 'to_bytes',  b'\x00\x00\x00', b'\x00\x00\x00',  'ffmpeg')#pipe to ffmpeg the interpolated frame



def process_task(c, which):
        
    c.R = None    
    c.R = imageio.read(c.input_file, "ffmpeg")
    c.reset_vals()
    count = 0

    if which == None:
        c.part_indexes = c.part_indexes
    elif which == 'even':
        c.part_indexes = c.part_indexes_even
    elif which == 'odd':
        c.part_indexes = c.part_indexes_odd
        # for x in range(c.part_data[count][4]):
        #     c.frames.append(frame_obj(c.R.get_next_data(), c.R._BaseReaderWriter_last_index))
        #     c.frames[index()] = None
        # count = 1

    for x in range(c.nb_parts_tot):
        curr_file = f"{c.process_dir}/{count:0>4d}.mp4"
    
        if check_index(c, count):
            if c.part_data[count][3] == 1 and not check_file(c,count,curr_file): #:
                
                start_frame = c.part_data[count][1]
                final_frame = c.part_data[count][2] #-1
                if c.selective_interpolation == 1:
                    final_frame -= 1
                #c.R.set_image_index(start_frame)
                c.frames.append(frame_obj(c.R.get_next_data(), c.R._BaseReaderWriter_last_index))
                if start_frame  != index():
                    print(f"{c.log}warning")
                if pipe_to_ffmpeg:
                    if c.waifu2x_scale != 0:
                        os.read(fd1, 1) #wait for waif2x to open the pipes before launching ffmpeg
                    start_interpolate_ffmpeg(c.PID_list, f'{count:0>4d}', c, '')      
                    if c.waifu2x_scale == 0: #open ffmpeg pipe
                        fd2 = open_fifo('ffmpeg_pipe', '', c)


                while index() < final_frame:    
                    in0 = index()
                    if c.selective_interpolation == 1:
                        wtinterpolate = c.wtinterpolate_data[count][index() - start_frame]
                    elif c.upscale_only == 1: wtinterpolate = 0 
                    else: wtinterpolate = 1 # interpolate all frames

                    if bypass == 0:
                         signals[1] = wtinterpolate
                
                    if index() == final_frame-1: 
                        signals[2] = 1 #it's the last frame of the part, signal to waifu
                    else: signals[2] = 0
                        
                    c.frames.append(frame_obj(c.R.get_next_data(), c.R._BaseReaderWriter_last_index))
                    in1 = index()
                    F0 =  draw_index_and_save(c.frames[index()-1], 'a', None, None) #frame a
                    F1 = Image.fromarray(c.frames[index()].frame) #frame c

                    if wtinterpolate == 1 and c.waifu2x_scale != 0:
                        F0_mod = F0.resize(c.downscale_resolution)
                        F1_mod = F1.resize(c.downscale_resolution)
                    else:
                        F0_mod = F0
                        F1_mod = F1
                    
                    draw_index_and_save(c.frames[index()-1], 'a', save_pngs, (c.downscale_resolution))
                    
                    if bypass or wtinterpolate == 0:
                        draw_index_and_save(c.frames[index()-1], 'a', save_pngs, (c.downscale_resolution))

                    if c.waifu2x_scale != 0:
                        LPB = index().to_bytes(2, 'little') + b'\x61'
                        pipe_array(F0.convert('RGBA'), 'to_bytes',  signals, LPB,  None)# pipe the first frame to waifu2x at original resolution
                    elif c.waifu2x_scale == 0: #we are not upscaling, pipe to ffmpeg directly
                        pipe_array(F0.convert('RGBA'), 'to_bytes',  b'\x00\x00\x00', b'\x00\x00\x00',  'ffmpeg')#pipe the first frame at original resolution

                    c.frames[index()-1] = None

                    start_time = time.time()

                    if bypass == 0 and wtinterpolate == 1 and c.upscale_only == 0: 
                        interpolate_and_pipe(c, F0_mod, F1_mod) #interpolate two frames and pipe to waifu2x or ffmpeg
                    elif wtinterpolate == 0:
                        if c.waifu2x_scale == 0: #we are not upscaling, pipe to ffmpeg directly
                            pipe_array(F0.convert('RGBA'), 'to_bytes',  b'\x00\x00\x00', b'\x00\x00\x00',  'ffmpeg')#pipe dummy frame

                    end_time = time.time()
                    loop_timer.update(end_time - start_time)
                    print(f"{c.log}****** Processed frame {index()} of part {count}| Time per frame (avg): {loop_timer.avg:2.2f}s | Time left: ******************" )
                if c.waifu2x_scale == 0:
                    os.close(fd2)
            else:
                skip_photosensitive_part(c, count)
        elif c.part_data[count][3] == 1: #and c.selective_interpolation:

            skip_photosensitive_part(c, count)
            # for x in range(c.part_data[count][4]+1):
            #     c.frames.append(frame_obj(R.get_next_data(), R._BaseReaderWriter_last_index))
            #     c.frames[index()] = None
        else:
            skip_photosensitive_part(c, count)

            # t0 = time.time()
            # for x in range(c.part_data[count][4]-1):
            #     c.frames.append(frame_obj(c.R.get_next_data(), c.R._BaseReaderWriter_last_index))
            #     c.frames[index()] = None
            # print(f"skipping {c.part_data[count][4]-1} frames took {time.time() - t0}")
        if c.part_indexes[c.index_counter] == None:
            break
        count+=1
    time.sleep(0.5)
    if check_missing(c, 0) == 0 and check_missing(c, 1) == 0:
        join_parts(c )
        print(f"{c.log} Parts joined")
    else:
        print(f"{c.log}: Some parts missing, didn't join")
    print(f"Dain ID {c.instance_id}: Finished processing images.")



if c.selective_interpolation == 1:
    process_task(c, None)
    finish(c, c.PID_list)
elif c.selective_interpolation == 0:
    if c.dual_instance == 0:
        process_task(c, 'even')
        process_task(c, 'odd')
        send_sigterm(c, PID_list)

    elif c.dual_instance == 1:
        if c.instance_id == 0:
            process_task(c, 'even')
        else:
            process_task(c, 'odd')
        finish(c, PID_list)



