import os,sys
import datetime
import argparse
import numpy
no_cuda = 0
if "--count_ph" in sys.argv:
    n = sys.argv.index('--count_ph')
    if sys.argv[n+1] != '0':    
        no_cuda = 1
    #ret = sys.argv.remove("--count_ph")
if not no_cuda:
    import  torch
    import networks

    modelnames =  networks.__all__
# import datasets
datasetNames = ('Vimeo_90K_interp') #datasets.__all__

parser = argparse.ArgumentParser(description='DAIN')

parser.add_argument('--debug',action = 'store_true', help='Enable debug mode')

if no_cuda == 0:
    parser.add_argument('--netName', type=str, default='DAIN',
                    choices = modelnames,help = 'model architecture: ' +
                        ' | '.join(modelnames) +
                        ' (default: DAIN)')
    parser.add_argument('--datasetName', default='Vimeo_90K_interp',
                        choices= datasetNames,nargs='+',
                        help='dataset type : ' +
                            ' | '.join(datasetNames) +
                            ' (default: Vimeo_90K_interp)')
else: 
    parser.add_argument('--netName', type=str, default='None')
    parser.add_argument('--datasetName', default='None')

parser.add_argument('--datasetPath',default='',help = 'the path of selected datasets')
parser.add_argument('--dataset_split', type = int, default=97, help = 'Split a dataset into trainining and validation by percentage (default: 97)')

parser.add_argument('--seed', type=int, default=1, help='random seed (default: 1)')

parser.add_argument('--numEpoch', '-e', type = int, default=100, help= 'Number of epochs to train(default:150)')

parser.add_argument('--batch_size', '-b',type = int ,default=1, help = 'batch size (default:1)' )
parser.add_argument('--workers', '-w', type =int,default=8, help = 'parallel workers for loading training samples (default : 1.6*10 = 16)')
parser.add_argument('--channels', '-c', type=int,default=3,choices = [1,3], help ='channels of images (default:3)')
parser.add_argument('--filter_size', '-f', type=int, default=4, help = 'the size of filters used (default: 4)',
                    choices=[2,4,6, 5,51]
                    )


parser.add_argument('--lr', type =float, default= 0.002, help= 'the basic learning rate for three subnetworks (default: 0.002)')
parser.add_argument('--rectify_lr', type=float, default=0.001, help  = 'the learning rate for rectify/refine subnetworks (default: 0.001)')

parser.add_argument('--save_which', '-s', type=int, default=1, choices=[0,1], help='choose which result to save: 0 ==> interpolated, 1==> rectified')
parser.add_argument('--time_step',  type=float, default=0.5, help='choose the time steps')
parser.add_argument('--flow_lr_coe', type = float, default=0.01, help = 'relative learning rate w.r.t basic learning rate (default: 0.01)')
parser.add_argument('--occ_lr_coe', type = float, default=1.0, help = 'relative learning rate w.r.t basic learning rate (default: 1.0)')
parser.add_argument('--filter_lr_coe', type = float, default=1.0, help = 'relative learning rate w.r.t basic learning rate (default: 1.0)')
parser.add_argument('--ctx_lr_coe', type = float, default=1.0, help = 'relative learning rate w.r.t basic learning rate (default: 1.0)')
parser.add_argument('--depth_lr_coe', type = float, default=0.001, help = 'relative learning rate w.r.t basic learning rate (default: 0.01)')
# parser.add_argument('--deblur_lr_coe', type = float, default=0.01, help = 'relative learning rate w.r.t basic learning rate (default: 0.01)')

parser.add_argument('--alpha', type=float,nargs='+', default=[0.0, 1.0], help= 'the ration of loss for interpolated and rectified result (default: [0.0, 1.0])')

parser.add_argument('--epsilon', type = float, default=1e-6, help = 'the epsilon for charbonier loss,etc (default: 1e-6)')
parser.add_argument('--weight_decay', type = float, default=0, help = 'the weight decay for whole network ' )
parser.add_argument('--patience', type=int, default=5, help = 'the patience of reduce on plateou')
parser.add_argument('--factor', type = float, default=0.2, help = 'the factor of reduce on plateou')
#
parser.add_argument('--pretrained', dest='SAVED_MODEL', default=None, help ='path to the pretrained model weights')
parser.add_argument('--no-date', action='store_true', help='don\'t append date timestamp to folder' )
parser.add_argument('--use_cuda', default= True, type = bool, help='use cuda or not')
parser.add_argument('--use_cudnn',default=1,type=int, help = 'use cudnn or not')
if no_cuda == 0:
    parser.add_argument('--dtype', default=torch.cuda.FloatTensor, choices = [torch.cuda.FloatTensor,torch.FloatTensor],help = 'tensor data type ')
else:
    parser.add_argument('--dtype', default=None)
# parser.add_argument('--resume', default='', type=str, help='path to latest checkpoint (default: none)')


parser.add_argument('--uid', type=str, default= None, help='unique id for the training')
parser.add_argument('--force', action='store_true', help='force to override the given uid')

# Colab version
parser.add_argument('--start_frame', type = int, default = 1, help='first frame number to process')
parser.add_argument('--end_frame', type = int, default = 100, help='last frame number to process')

parser.add_argument('--input_file', type = str, default = '/content/DAIN/input_frames', help='input directory')
parser.add_argument('--output_dir', type = str, default = '/content/DAIN/output_frames', help='output directory')
parser.add_argument('--parts_data_dir', type = str, default = os.getcwd(), help='directory where to save part data')


parser.add_argument('--ffmpeg_log_level', type = int, default = 32, help='ffmpeg_log_level')
parser.add_argument('--ffmpeg_codec', type = str, default = 'libx264', help='ffmpeg_codec')

parser.add_argument('--enable_transcoder', type = int, default = 0, help='enable_transcoder')
parser.add_argument('--overwrite', type = int, default = 0, help='overwrite')

parser.add_argument('--upscale_resolution', type = str, default = '0', help='resolution to upsacale to ')

parser.add_argument('--downscale_resolution', type = str, default = '0', help='resolution to downscale to')

default_model_dir = f'{os.getcwd()}/waifu2x-ncnn-vulkan/models/models-upconv_7_anime_style_art_rgb/'
parser.add_argument('--waifu2x_model', type = str, default = default_model_dir, help='waifu2x model directory')
parser.add_argument('--waifu2x_scale', type = int, default = 0, help='scale argument for waifu2x')
parser.add_argument('--mode', type = str, default = 'interpolate_with_downscale', help='application operating mode')
parser.add_argument('--start_offset', type = int, default = 0, help='start part offset ')
parser.add_argument('--instance_id', type = int, default = 0, help='numeric id of the instance ')
parser.add_argument('--dual_instance', type = int, default = 0, help='use two application instances')
parser.add_argument('--selective_interpolation', type = int, default = 1, help='choose which frames to interpolate based on ffmpegs filter')
parser.add_argument('--use_debug_parts', type = int, default = 0, help='use debug parts')
parser.add_argument('--debug_nb_parts', type = int, default = 0, help='custom number of parts')
parser.add_argument('--upscale_only', type = int, default = 0, help='upscale only mode')
parser.add_argument('--ph_this_bad_th', type = int, default = 100, help='threshold for ffmpeg photosensitivity filters low badness fix')

parser.add_argument('--count_ph', type = int, default = 0, help='count photosensitivity frames')
parser.add_argument('--use_newbadness', type = int, default = 0, help='use newbadness instead of this_badness')
parser.add_argument('--intro_skip', type = str, default = '0:0-0:0', help='specified part will not be interpolated')
parser.add_argument('--ending_skip', type = str, default = '0:0-0:0', help='specified part will not be interpolated')
parser.add_argument('--wti_offset', type = int, default = 0, help='wti offset')
parser.add_argument('--waifu2x_verbose', type = int, default = 0, help='waifu2x_verbose')
parser.add_argument('--use_ffmpeg_dec', type = int, default = 0, help='use ffmpeg decoder')
parser.add_argument('--smart_fill', type = int, default = 0, help='replace consecutive equal frames with  interpolated frames')

args = parser.parse_args()

import shutil

if args.uid == None:
    unique_id = str(numpy.random.randint(0, 100000))
    print("revise the unique id to a random numer " + str(unique_id))
    args.uid = unique_id
    timestamp = datetime.datetime.now().strftime("%a-%b-%d-%H-%M")
    save_path = './model_weights/'+ args.uid  +'-' + timestamp
else:
    save_path = './model_weights/'+ str(args.uid)

# print("no pth here : " + save_path + "/best"+".pth")
if not os.path.exists(save_path + "/best"+".pth"):
    # print("no pth here : " + save_path + "/best" + ".pth")
    os.makedirs(save_path,exist_ok=True)
else:
    if not args.force:
        raise("please use another uid ")
    else:
        print("override this uid" + args.uid)
        for m in range(1,10):
            if not os.path.exists(save_path+"/log.txt.bk" + str(m)):
                shutil.copy(save_path+"/log.txt", save_path+"/log.txt.bk"+str(m))
                shutil.copy(save_path+"/args.txt", save_path+"/args.txt.bk"+str(m))
                break



parser.add_argument('--save_path',default=save_path,help = 'the output dir of weights')
parser.add_argument('--log', default = save_path+'/log.txt', help = 'the log file in training')
parser.add_argument('--arg', default = save_path+'/args.txt', help = 'the args used')

args = parser.parse_args()


with open(args.log, 'w') as f:
    f.close()
with open(args.arg, 'w') as f:
    print(args)
    print(args,file=f)
    f.close()
if args.use_cudnn:
    if not no_cuda:
        print("cudnn is used")
        torch.backends.cudnn.benchmark = True  # to speed up the
else:
    print("cudnn is not used")
    torch.backends.cudnn.benchmark = False  # to speed up the

