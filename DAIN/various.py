import os, sys, io, struct, signal, fcntl, time, select
import termios, tty, threading
from PIL import Image, ImageDraw
exiting = 0

ffmpeg_pipe = f"/tmp/ffmpeg_pipe"

F_SETPIPE_SZ = 1031  # Linux 2.6.35+
F_GETPIPE_SZ = 1032  # Linux 2.6.35+

def open_fifo(pipe, transcode, c):
    global fd2;
    if transcode:  pipe_count = c.pipe_counter_t
    else:           pipe_count = c.pipe_counter_i

    fifo = f"/tmp/{pipe}_{transcode}_{pipe_count}_id{c.instance_id}"
    print(f"{c.log} opening {transcode} fifo: {fifo}")
    #c.pipe_counter +=2
    if c.waifu2x_scale == 0:
        c.pipe_counter_i += 2
    if transcode: c.pipe_counter_t += 2
    
    try:
        RET = os.path.isfile(fifo)                
        if os.path.exists(fifo) == False:
            os.mkfifo(fifo)
        print(f"{c.log}Checking fifo file …")
        fd2 = os.open(fifo, os.O_WRONLY)
        print ("Pipe size            : "+str(fcntl.fcntl(fd2, F_GETPIPE_SZ)))
        fcntl.fcntl(fd2, F_SETPIPE_SZ, 1048576)
        print ("Pipe (modified) size : "+str(fcntl.fcntl(fd2, F_GETPIPE_SZ)))
        return fd2
    except Exception as e:
        print( "Unable to create fifo, error: "+str(e)

    
)
class frame_obj:
    def __init__(self, frame, index):
        self.frame  = frame
        self.index = index

def check_index(c, count):

    if count == c.part_indexes[c.index_counter]:
        c.index_counter+=1
        return 1
    else: return 0

def skip_photosensitive_part(c, count):
    skip_count = 0
    if c.selective_interpolation == 0:
        while c.R._BaseReaderWriter_last_index < c.part_data[count][2]-1:
            c.frames.append(frame_obj(c.R.get_next_data(), c.R._BaseReaderWriter_last_index))
            c.frames[c.R._BaseReaderWriter_last_index] = None
            skip_count+=1
        # if count == c.part_indexes[c.index_counter-1]:
        #     offset = 1
        # else: offset = -1
    else:# offset = 1

        while c.R._BaseReaderWriter_last_index < c.part_data[count][2]-1:
            c.frames.append(frame_obj(c.R.get_next_data(), c.R._BaseReaderWriter_last_index))
            c.frames[c.R._BaseReaderWriter_last_index] = None
            skip_count+=1
        # for x in range(c.part_data[count][4]+1):
        #     c.frames.append(frame_obj(c.R.get_next_data(), c.R._BaseReaderWriter_last_index))
        #     c.frames[c.R._BaseReaderWriter_last_index] = None
        #     skip_count+=1

    print(f"{c.log} skept ", skip_count )
def create_pipes(c):
    global fd0; global fd1
    output_pipe = f"/tmp/dain_a_id{c.instance_id}"
    input_pipe = f"/tmp/dain_b_id{c.instance_id}"

    if os.path.exists(output_pipe) == False:
        os.mkfifo(output_pipe)
    if os.path.exists(input_pipe) ==  False:
        os.mkfifo(input_pipe)
    

    print(f"{c.log}Opening pipes...")
    fd1 = os.open(input_pipe, os.O_RDONLY)

    fd0 = os.open(output_pipe, os.O_WRONLY)

    print(f"{c.log}Pipes opened")
    
def terminate():
    time.sleep(5)
    print(f"Exiting")
    sys.exit()

 

def pipe_array(image_obj, mode, signals, frame_id, ffmpeg):
    if mode == 'to_bytes':
        bytearr = image_obj.tobytes()
    elif mode == 'BytesIO':
        output = io.BytesIO()
        image_obj.save(output, format='PNG')
        bytearr = bytearray(output.getvalue())

    if ffmpeg: dest = fd2
    else: dest = fd0

   
    if not ffmpeg: 
        os.write(dest, signals)
        ready = os.read(fd1, 1)
    if exiting == 101:
        terminate()

    size = len(bytearr)
    size_bytes = struct.pack("I", size)
    if not ffmpeg: 
        os.write(dest, size_bytes)
        ready = os.read(fd1, 1)
        print(len(frame_id))
    
    if not ffmpeg:
        os.write(dest, frame_id)
        ready = os.read(fd1, 1)

    start = 0
    end = 1048576
    nb_times = size // 1048576
    for v in range(nb_times):
        ret = os.write(dest, bytearr[start:end])
        if not ffmpeg: ready = os.read(fd1, 1)
        start+= 1048576
        end += 1048576

    ret = os.write(dest, bytearr[(1048576*nb_times):size])
    if not ffmpeg: ready = os.read(fd1, 1)



class BlockingTestThread(threading.Thread):
    def __init__(self):
        self._running_flag = False
        self.stop  = threading.Event()
        threading.Thread.__init__(self, target=self.test_method)

    def test_method(self):
        try:
            while(not self.stop.wait(1)):
                self._running_flag = True
                while 1 and exiting == 0:  # ESC
                    x = sys.stdin.read(1)[0]
                    print("pressed ", x)
                print ('Start wait')
                self.stop.wait(100)
                print ('Done waiting')
        finally:
                self._running_flag = False

    def terminate(self):
         self.stop.set()  



def check_key_presses(PID_list, signals, c):
    x = 0
    orig_settings = termios.tcgetattr(sys.stdin)
    global exiting; global print_settings
    counter = 0
    while 1 and exiting == 0:  # ESC
        #sys.stdin = sys.__stdin__
        x = sys.__stdin__.read(1)[0]
        #if sys.stdin in select.select([sys.stdin], [], [], 5)[0]:
            #print('Input is waiting to be read.')      
        if x == 'q' or x == 'Q':
            print(f"{c.log}Exiting")
            exiting = 101
            signals[0] = exiting
            time.sleep(3)
            time.sleep(1)
            sys.exit("Exiting")
            try:
                for v in range(len(PID_list)-1, 0, -1):
                    if PID_list[v] != None:
                        os.kill(PID_list[v], 9)
                os.kill(PID_list[0], 9)
            except:
                pass
        

    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, orig_settings)

def draw_index_and_save(frame_obj, a_or_b, save_pngs, resize):
    Dtemp = Image.fromarray(frame_obj.frame)
    if resize:
        Dtemp = Dtemp.resize(resize)
    d0 = ImageDraw.Draw(Dtemp)
    d0.text((10,10), f"{frame_obj.index}{a_or_b}", fill=(255,255,0))

    if save_pngs:
        Dtemp.save(f"{save_pngs}/{frame_obj.index:0>4d}{a_or_b}.png")
    return Dtemp

def ret_pipe_desc():
    return [fd0, fd1]

def send_sigterm(c, PID_list):
    os.kill(PID_list[1].pid, signal.SIGTERM)
    os.kill(PID_list[0].pid, signal.SIGTERM)

def get_tot_photosensitive_frames(c):
    loop_nb = 0
    u = 0
    try: 
        while loop_nb <= c.nb_parts_tot:
            u += c.part_data[loop_nb][5]
            loop_nb += 2
        print(f"Total number of frames to interpolate: {u}")
    except: print(f"Total number of frames to interpolate: {u}")
