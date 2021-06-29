// waifu2x implemented with ncnn library

#include <stdio.h>
#include <algorithm>
#include <queue>
#include <vector>
#include <clocale>
#include <utils.h>
#include <fcntl.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <stdlib.h>
#include <fstream>
#include <semaphore.h>

#if _WIN32
// image decoder and encoder with wic
#include "wic_image.h"
#else // _WIN32
// image decoder and encoder with stb
#define STB_IMAGE_IMPLEMENTATION
#define STBI_NO_PSD
#define STBI_NO_TGA
#define STBI_NO_GIF
#define STBI_NO_HDR
#define STBI_NO_PIC
#define STBI_NO_STDIO
#include "stb_image.h"
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"
#endif // _WIN32
#include "webp_image.h"
char *dir = "/home/amadeok/waifu2x-ncnn-vulkan/src/log";
char *dain_dir = "/home/amadeok/dain/content/DAIN/";
int fd0, fd1, fd2;
int pipe_to_waifu = 1;
int pipe_to_ffmpeg = 1;
int wtinterpolate = 0;
uint8_t signals[3] = {0, 0, 0};
int exiting = 0;
int lp_load = 0;
int lp_save = 0;
int part_counter = 0;
char waifu_ffmpeg_a[200];
int debug_verbose = 1;
int upscale_only = 0;
volatile int upscaler_busy = 0;
volatile int last_frame_of_part = 0;
volatile int frame_counter = 0;
int interpolation_frames_nb = 0;
int instance_id = 0;
char load_frame_id[3] = {0, 0, 0};
char save_frame_id[3] = {0, 0, 0};
unsigned char *filedata2;
uint32_t initial_image_size[1];
static char log0[50];
int rgb_mult = 3;
int max_pipe_size(int pipe_desc)
{
    long pipe_size = (long)fcntl(pipe_desc, F_GETPIPE_SZ);
    int ret = fcntl(pipe_desc, F_SETPIPE_SZ, 1048576);
    std::string the_ret = "";
    pipe_size = (long)fcntl(pipe_desc, F_GETPIPE_SZ);
    std::string string_buf = "";
    if (debug_verbose == 1)
        printf("%s new pipe size: %ld\n", log0, pipe_size);
    return pipe_desc;
}

int open_ffmpeg_pipe(int pipe_desc, int part_counter)
{
    sprintf(waifu_ffmpeg_a, "%s%s%d_id%d", "/tmp/", "ffmpeg_pipe__", part_counter, instance_id);
    if (debug_verbose == 1)
        printf("%s ffmpeg pipe %s\n", log0, waifu_ffmpeg_a);
    mkfifo(waifu_ffmpeg_a, 0666);
    pipe_desc = open(waifu_ffmpeg_a, O_WRONLY);
    max_pipe_size(pipe_desc);
    if (debug_verbose)
        printf("%s ffmpeg pipe part %d opened\n", log0, part_counter);
    return pipe_desc;
}
void close_ffmpeg_pipe(int pipe_desc, int part_counter)
{
    close(pipe_desc);
    printf("%s ffmpeg pipe part %d closed\n", log0, part_counter);
}

void start_pipes()
{
    char input_pipe[200];
    char output_pipe[200];
    sprintf(input_pipe, "%s_id%d", "/tmp/dain_a", instance_id);
    sprintf(output_pipe, "%s_id%d", "/tmp/dain_b", instance_id);
    sprintf(log0, "Waifu2x ID %d:", instance_id);

    printf("%s dain-waifu pipe: %s\n", log0, input_pipe);
    mkfifo(input_pipe, 0666);
    mkfifo(output_pipe, 0666);

    if (pipe_to_waifu == 1)
    {
        fd1 = open(output_pipe, O_WRONLY);

        fd0 = open(input_pipe, O_RDONLY);
        printf("%s c++ python-waifu pipes opened\n", log0);
    }

    int change_pipe_size = true;
    if (change_pipe_size == true)
    {
        if (pipe_to_waifu)
            max_pipe_size(fd0);
    }
}

int read_pipe(unsigned char *data, uint32_t *pixel_data_size)
{
    int ret2;
    uint16_t nb[1];
    ret2 = read(fd0, load_frame_id, 3);
    write(fd1, "1", 1);
    memcpy(nb, load_frame_id, 2);
    //  printf("load_frame id %d%c\n", nb[0], load_frame_id[2]);
    int nb_times = pixel_data_size[0] / 1048576;

    for (int h = 0; h < nb_times; h++)
    {
        ret2 = read(fd0, data + h * 1048576, 1048576 * sizeof(unsigned char));
        write(fd1, "1", 1);
        if (ret2 != 1048576)
            printf("warning \n");
    }

    ret2 = read(fd0, data + nb_times * 1048576, pixel_data_size[0] - nb_times * 1048576);
    if (ret2 != pixel_data_size[0] - nb_times * 1048576)
        printf("warning \n");

    write(fd1, "1", 1);
    return ret2;
    //array_to_file(v.outimage.data, size_write, dir, "pd", lp);
    // return &data;
}
void write_pipe(void *data, int width, int height, int nb, char *inter)
{
    int ret2 = 0;
    //  printf("writing frame to pipe id %d%s\n", nb, inter);

    int size_write = (width) * (height)*rgb_mult;

    //write(fd1, "1", 1);

    int nb_times = size_write / 1048576;

    for (int h = 0; h < nb_times; h++)
    {
        ret2 = write(fd2, data + h * 1048576, 1048576 * sizeof(unsigned char));
    }

    ret2 = write(fd2, data + nb_times * 1048576, size_write - nb_times * 1048576);
}
#if _WIN32
#include <wchar.h>
static wchar_t *optarg = NULL;
static int optind = 1;
static wchar_t getopt(int argc, wchar_t *const argv[], const wchar_t *optstring)
{
    if (optind >= argc || argv[optind][0] != L'-')
        return -1;

    wchar_t opt = argv[optind][1];
    const wchar_t *p = wcschr(optstring, opt);
    if (p == NULL)
        return L'?';

    optarg = NULL;

    if (p[1] == L':')
    {
        optind++;
        if (optind >= argc)
            return L'?';

        optarg = argv[optind];
    }

    optind++;

    return opt;
}

static std::vector<int> parse_optarg_int_array(const wchar_t *optarg)
{
    std::vector<int> array;
    array.push_back(_wtoi(optarg));

    const wchar_t *p = wcschr(optarg, L',');
    while (p)
    {
        p++;
        array.push_back(_wtoi(p));
        p = wcschr(p, L',');
    }

    return array;
}
#else               // _WIN32
#include <unistd.h> // getopt()

static std::vector<int> parse_optarg_int_array(const char *optarg)
{
    std::vector<int> array;
    array.push_back(atoi(optarg));

    const char *p = strchr(optarg, ',');
    while (p)
    {
        p++;
        array.push_back(atoi(p));
        p = strchr(p, ',');
    }

    return array;
}
#endif              // _WIN32

// ncnn
#include "cpu.h"
#include "gpu.h"
#include "platform.h"

#include "waifu2x.h"

#include "filesystem_utils.h"

static void print_usage()
{
    fprintf(stdout, "Usage: waifu2x-ncnn-vulkan -i infile -o outfile [options]...\n\n");
    fprintf(stdout, "  -h                   show this help\n");
    fprintf(stdout, "  -v                   verbose output\n");
    fprintf(stdout, "  -i input-path        input image path (jpg/png/webp) or directory\n");
    fprintf(stdout, "  -o output-path       output image path (jpg/png/webp) or directory\n");
    fprintf(stdout, "  -n noise-level       denoise level (-1/0/1/2/3, default=0)\n");
    fprintf(stdout, "  -s scale             upscale ratio (1/2/4/8/16/32, default=2)\n");
    fprintf(stdout, "  -t tile-size         tile size (>=32/0=auto, default=0) can be 0,0,0 for multi-gpu\n");
    fprintf(stdout, "  -m model-path        waifu2x model path (default=models-cunet)\n");
    fprintf(stdout, "  -g gpu-id            gpu device to use (-1=cpu, default=auto) can be 0,1,2 for multi-gpu\n");
    fprintf(stdout, "  -j load:proc:save    thread count for load/proc/save (default=1:2:2) can be 1:2,2,2:2 for multi-gpu\n");
    fprintf(stdout, "  -x                   enable tta mode\n");
    fprintf(stdout, "  -f format            output image format (jpg/png/webp, default=ext/png)\n");
}

class Task
{
public:
    int id;
    int webp;

    path_t inpath;
    path_t outpath;

    ncnn::Mat inimage;
    ncnn::Mat outimage;
};
path_t dain = PATHSTR("dain");

class TaskQueue
{
public:
    TaskQueue()
    {
    }

    void put(const Task &v)
    {
        lock.lock();

        while (tasks.size() >= 8) // FIXME hardcode queue length
        {
            condition.wait(lock);
        }

        tasks.push(v);

        lock.unlock();

        condition.signal();
    }

    void get(Task &v)
    {
        lock.lock();

        while (tasks.size() == 0)
        {
            condition.wait(lock);
        }

        v = tasks.front();
        tasks.pop();

        lock.unlock();

        condition.signal();
    }

private:
    ncnn::Mutex lock;
    ncnn::ConditionVariable condition;
    std::queue<Task> tasks;
};

TaskQueue toproc;
TaskQueue tosave;

void exit_application()
{
    printf("%s Waifu2x-vulkan exiting \n", log0);
    close(fd0);
    close(fd1);
    close(fd2);
    exiting = 101;
    sleep(1);
    //exit(EXIT_SUCCESS);
}

int receive_signals()
{
    int ret2 = read(fd0, signals, 3 * sizeof(unsigned char));
    if (signals[0] == 101)
        exit_application();
    write(fd1, "1", 1);
    return signals[0];
}

class LoadThreadParams
{
public:
    int scale;
    int jobs_load;

    // session data
    std::vector<path_t> input_files;
    std::vector<path_t> output_files;
};
int first_time = 1;
void *load(void *args)
{
    uint32_t pixel_data_size[1];

    const LoadThreadParams *ltp = (const LoadThreadParams *)args;
    const int count = ltp->input_files.size();
    const int scale = ltp->scale;
    int i = 0;
#pragma omp parallel for schedule(static, 1) num_threads(ltp->jobs_load)
    for (int d = 0; d < 999999; d++)
    {
        if (d == 999998)
            d = 0;
        if (exiting == 101)
        {
            exiting = 1999999;
            exit_application();
            exit(EXIT_SUCCESS);
        }
        while (upscaler_busy == 1)
        {
            // if (debug_verbose == 1)
            //  printf("upscaler busy\n");
            usleep(100 * 1000);
        }
        const path_t &imagepath = ltp->input_files[i];

        int webp = 0;

        unsigned char *pixeldata = 0;
        unsigned char *first_frame_data;
        unsigned char *interpolated_data;
        int w;
        int h;
        int c;

        if (first_time == 1)
        {
#if _WIN32
            FILE *fp = _wfopen(imagepath.c_str(), L"rb");
#else
            int size_piped_file = 0;

            //  FILE *fp = fopen(imagepath.c_str(), "rb");
#endif
            if (filedata2)
            {

                unsigned char *filedata = 0;

                fd2 = open_ffmpeg_pipe(fd2, part_counter);

                filedata = filedata2;
                if (filedata)
                {
                    pixeldata = webp_load(filedata, initial_image_size[0], &w, &h, &c);
                    if (pixeldata)
                    {
                        webp = 1;
                    }
                    else
                    {
                        // not webp, try jpg png etc.
#if _WIN32
                        pixeldata = wic_decode_image(imagepath.c_str(), &w, &h, &c);
#else  // _WIN32
                        pixeldata = stbi_load_from_memory(filedata, initial_image_size[0], &w, &h, &c, 0);
                        if (pixeldata)
                        {
                            // stb_image auto channel
                            if (c == 1)
                            {
                                // grayscale -> rgb
                                stbi_image_free(pixeldata);
                                pixeldata = stbi_load_from_memory(filedata, initial_image_size[0], &w, &h, &c, 3);
                                c = 3;
                            }
                            else if (c == 2)
                            {
                                // grayscale + alpha -> rgba
                                stbi_image_free(pixeldata);
                                pixeldata = stbi_load_from_memory(filedata, initial_image_size[0], &w, &h, &c, 4);
                                c = 4;
                            }
                        }
#endif // _WIN32
                    }

                    // free(filedata);
                }
            }
            int rgba_data_size = w * scale * h * scale * rgb_mult;
            first_frame_data = (unsigned char *)malloc(rgba_data_size);
            interpolated_data = (unsigned char *)malloc(rgba_data_size);

            first_time = 0;
        }
        int ret2;
        if (pipe_to_waifu == 1)
        {
            //  if (counter1 == 1)
            // {
            if (pipe_to_ffmpeg == 1)
            {
                if (frame_counter == 0 && upscale_only == 0)
                {
                    do //receive the first frame and pipe it to ffmpeg
                    {

                        if (receive_signals() == 101)
                            break;
                        ret2 = read(fd0, pixel_data_size, 4 * sizeof(unsigned char));
                        write(fd1, "1", 1);
                        if (debug_verbose == 1)
                            printf("%s Receiving A frame\n", log0);
                        if (read_pipe(first_frame_data, pixel_data_size) == -1)
                            break;
                        if (debug_verbose == 1)
                            printf("%s Piping A frame\n", log0);

                        write_pipe(first_frame_data, w * scale, h * scale, lp_load, "a");

                        for (int b = 0; b < signals[1] - 1; b++) //if (signals[1] == 2)
                        {
                            write_pipe(first_frame_data, w * scale, h * scale, lp_load, "a");
                            if (debug_verbose == 1)
                                printf("%s Piping interpolated frame %d for smart fill \n", log0, b);
                        }
                        lp_load++;
                        if (signals[1] == 0)
                        {
                            for (int u = 0; u < interpolation_frames_nb - 1; u++)
                            {
                                if (debug_verbose == 1)
                                    printf("%s Piping Dummy frame %d\n", log0, u + 1);
                                write_pipe(first_frame_data, w * scale, h * scale, lp_load, "a");
                            }
                            lp_load++;
                            if (signals[0] == 101)
                                break;
                            if (signals[2] == 1)
                            {
                                if (debug_verbose == 1)
                                    printf("%s last frame of the part\n", log0);
                                close_ffmpeg_pipe(fd2, part_counter);
                                part_counter += 2;
                                usleep(200 * 1000);
                                write(fd1, "1", 1);

                                fd2 = open_ffmpeg_pipe(fd2, part_counter);
                            }
                        }
                    } while (signals[1] == 0);
                    frame_counter++;
                }
            }
            //     }

            //receive the interpolated frame and proceed to upscale it
            if (receive_signals() == 101)
                exit_application();
            ret2 = read(fd0, pixel_data_size, 4 * sizeof(unsigned char));
            write(fd1, "1", 1);
            if (debug_verbose == 1 && upscale_only == 0)
                printf("%s Receiving  interpolated frame \n", log0);
            else if (debug_verbose == 1)
                printf("%s Receiving frame to upscale\n", log0);
            upscaler_busy = 1;
            read_pipe(interpolated_data, pixel_data_size);
            pixeldata = interpolated_data;
            if (signals[2] == 1)
                last_frame_of_part = 1;
            else
                last_frame_of_part = 0;
        }
        if (pixeldata)
        {
            //   int size_write = (w*2)*(h*2)*4;
            // array_to_file(pixeldata, size_write, dir, "pixeldata", 0 );
            Task v;
            v.id = i;
            v.webp = webp;
            v.inpath = dain;
            v.outpath = dain;

            v.inimage = ncnn::Mat(w, h, (void *)pixeldata, (size_t)c, c);
            v.outimage = ncnn::Mat(w * scale, h * scale, (size_t)c, c);
            toproc.put(v);

            path_t ext = get_file_extension(v.outpath);
            if (c == 4 && (ext == PATHSTR("jpg") || ext == PATHSTR("JPG") || ext == PATHSTR("jpeg") || ext == PATHSTR("JPEG")))
            {
                path_t output_filename2 = ltp->output_files[i] + PATHSTR(".png");
                v.outpath = output_filename2;
#if _WIN32
                fwprintf(stderr, L"image %ls has alpha channel ! %ls will output %ls\n", imagepath.c_str(), imagepath.c_str(), output_filename2.c_str());
#else  // _WIN32
                fprintf(stderr, "image %s has alpha channel ! %s will output %s\n", imagepath.c_str(), imagepath.c_str(), output_filename2.c_str());
#endif // _WIN32
            }
        }
        else
        {
#if _WIN32
            fwprintf(stderr, L"decode image %ls failed\n", imagepath.c_str());
#else  // _WIN32 \
       //      toproc.put(v);
#endif // _WIN32
        }
    }

    return 0;
}

class ProcThreadParams
{
public:
    const Waifu2x *waifu2x;
};

void *proc(void *args)
{
    const ProcThreadParams *ptp = (const ProcThreadParams *)args;
    const Waifu2x *waifu2x = ptp->waifu2x;

    for (;;)
    {
        if (exiting == 1999999)
        {
            printf("%s Proc thread exiting\n", log0);
            sleep(2);
            exit(EXIT_SUCCESS);
        }
        Task v;

        toproc.get(v);

        if (v.id == -233)
            break;

        const int scale = v.outimage.w / v.inimage.w;
        int scale_run_count = 0;
        if (scale == 1 || scale == 2)
        {
            scale_run_count = 1;
        }
        if (scale == 4)
        {
            scale_run_count = 2;
        }
        if (scale == 8)
        {
            scale_run_count = 3;
        }
        if (scale == 16)
        {
            scale_run_count = 4;
        }
        if (scale == 32)
        {
            scale_run_count = 5;
        }

        for (int i = 0; i < scale_run_count; i++)
        {
            if (i == scale_run_count - 1)
            {
                waifu2x->process(v.inimage, v.outimage);
            }
            else
            {
                ncnn::Mat tmpimage(v.inimage.w * 2, v.inimage.h * 2, (size_t)v.inimage.elemsize, (int)v.inimage.elemsize);
                waifu2x->process(v.inimage, tmpimage);
                v.inimage = tmpimage;
            }
        }

        tosave.put(v);
    }

    return 0;
}

class SaveThreadParams
{
public:
    int verbose;
};

void *save(void *args)
{
    const SaveThreadParams *stp = (const SaveThreadParams *)args;
    const int verbose = stp->verbose;
    for (;;)
    {
        if (exiting == 1999999)
        {
            sleep(2);
            exit(EXIT_SUCCESS);
        }
        Task v;

        tosave.get(v);

        if (v.id == -233)
            break;

        // free input pixel data
        {
            unsigned char *pixeldata = (unsigned char *)v.inimage.data;

            if (v.webp == 1)
            {
                //    free(pixeldata);
            }
            else
            {
#if _WIN32
                //     free(pixeldata);
#else
                //   stbi_image_free(pixeldata);
#endif
            }
        }

        int success = 0;

        // path_t ext = get_file_extension(v.outpath);

        // if (ext == PATHSTR("webp") || ext == PATHSTR("WEBP"))
        // {
        //     success = webp_save(v.outpath.c_str(), v.outimage.w, v.outimage.h, v.outimage.elempack, (const unsigned char *)v.outimage.data);
        // }
        // else if (1)
        // {
        //  success = wic_encode_image(v.outpath.c_str(), v.outimage.w, v.outimage.h, v.outimage.elempack, v.outimage.data);
        //  success = stbi_write_png(v.outpath.c_str(), v.outimage.w, v.outimage.h, v.outimage.elempack, v.outimage.data, 0);
        if (pipe_to_ffmpeg == 1)
        {
            if (debug_verbose == 1 && upscale_only == 0)
                printf("%s Piping interpolated upscaled frame %d\n", log0, frame_counter);
            else if (debug_verbose == 1)
                printf("%s Piping upscaled frame %d\n", log0, frame_counter);

            write_pipe(v.outimage.data, v.outimage.w, v.outimage.h, lp_save, "b");

            for (int b = 0; b < signals[1] - 1; b++) //if (signals[1] == 2)
            {                                        // smart fill is on for this frame, repeat each frame
                write_pipe(v.outimage.data, v.outimage.w, v.outimage.h, lp_save, "b");
                if (debug_verbose == 1)
                    printf("%s Piping interpolated upscaled frame for smart fill %d\n", log0, b);
            }

            frame_counter++;

            if (last_frame_of_part == 1 && frame_counter == interpolation_frames_nb || last_frame_of_part && upscale_only == 1)
            {
                if (debug_verbose == 1)

                    printf("%s last frame of the part\n", log0);
                close_ffmpeg_pipe(fd2, part_counter);
                part_counter += 2;
                usleep(200 * 1000);
                write(fd1, "1", 1);
                fd2 = open_ffmpeg_pipe(fd2, part_counter);
            }
            upscaler_busy = 0;
            if (frame_counter == interpolation_frames_nb)
                frame_counter = 0;
        }
        lp_save++;
    }

    return 0;
}

#if _WIN32
int wmain(int argc, wchar_t **argv)
#else
int main(int argc, char **argv)
#endif
{

    path_t inputpath;

    path_t outputpath;
    int noise = 0;
    int scale = 2;
    std::vector<int> tilesize;
    path_t model = PATHSTR("models-cunet");
    std::vector<int> gpuid;
    int jobs_load = 1;
    std::vector<int> jobs_proc;
    int jobs_save = 2;
    int verbose = 0;
    int tta_mode = 0;
    path_t format = PATHSTR("png");

#if _WIN32
    setlocale(LC_ALL, "");
    wchar_t opt;
    while ((opt = getopt(argc, argv, L"i:o:n:s:t:m:g:j:f:vxh")) != (wchar_t)-1)
    {
        switch (opt)
        {
        case L'i':
            inputpath = optarg;
            break;
        case L'o':
            outputpath = optarg;
            break;
        case L'n':
            noise = _wtoi(optarg);
            break;
        case L's':
            scale = _wtoi(optarg);
            break;
        case L't':
            tilesize = parse_optarg_int_array(optarg);
            break;
        case L'm':
            model = optarg;
            break;
        case L'g':
            gpuid = parse_optarg_int_array(optarg);
            break;
        case L'j':
            swscanf(optarg, L"%d:%*[^:]:%d", &jobs_load, &jobs_save);
            jobs_proc = parse_optarg_int_array(wcschr(optarg, L':') + 1);
            break;
        case L'f':
            format = optarg;
            break;
        case L'v':
            verbose = 1;
            break;
        case L'x':
            tta_mode = 1;
            break;
        case L'h':
        default:
            print_usage();
            return -1;
        }
    }
#else  // _WIN32
    int opt;
    while ((opt = getopt(argc, argv, "i:o:n:s:t:m:g:j:f:p:d:b:z:vxh")) != -1)
    {
        switch (opt)
        {
        case 'i':
            inputpath = optarg;
            break;
        case 'o':
            outputpath = optarg;
            break;
        case 'n':
            noise = atoi(optarg);
            break;
        case 's':
            scale = atoi(optarg);
            break;
        case 't':
            tilesize = parse_optarg_int_array(optarg);
            break;
        case 'm':
            model = optarg;
            break;
        case 'g':
            gpuid = parse_optarg_int_array(optarg);
            break;
        case 'j':
            sscanf(optarg, "%d:%*[^:]:%d", &jobs_load, &jobs_save);
            jobs_proc = parse_optarg_int_array(strchr(optarg, ':') + 1);
            break;
        case 'f':
            format = optarg;
            break;
        case 'p':
            interpolation_frames_nb = atoi(optarg);
            break;
        case 'd':
            instance_id = atoi(optarg);
            break;
        case 'b':
            debug_verbose = atoi(optarg);
            break;
        case 'z':
            upscale_only = atoi(optarg);
            break;
        case 'v':
            verbose = 1;
            break;
        case 'x':
            tta_mode = 1;
            break;
        case 'h':
        default:
            print_usage();
            return -1;
        }
    }
#endif // _WIN32

    if (upscale_only == 1)
        printf("%s Upscale only mode\n", log0);
    if (dain.compare(inputpath) == 0)
    {
        printf("%s Piping from Python\n", log0);
    }

    else if (inputpath.empty() || outputpath.empty())
    {
        print_usage();
        return -1;
    }

    if (noise < -1 || noise > 3)
    {
        fprintf(stderr, "invalid noise argument\n");
        return -1;
    }
    if (interpolation_frames_nb == 0)
    {
        fprintf(stderr, "invalid interpolation_frames_nb argument\n");
        return -1;
    }

    if (!(scale == 1 || scale == 2 || scale == 4 || scale == 8 || scale == 16 || scale == 32))
    {
        fprintf(stderr, "invalid scale argument\n");
        return -1;
    }

    if (tilesize.size() != (gpuid.empty() ? 1 : gpuid.size()) && !tilesize.empty())
    {
        fprintf(stderr, "invalid tilesize argument\n");
        return -1;
    }

    for (int i = 0; i < (int)tilesize.size(); i++)
    {
        if (tilesize[i] != 0 && tilesize[i] < 32)
        {
            fprintf(stderr, "invalid tilesize argument\n");
            return -1;
        }
    }
    if (jobs_load < 1 || jobs_save < 1)
    {
        fprintf(stderr, "invalid thread count argument\n");
        return -1;
    }

    if (jobs_proc.size() != (gpuid.empty() ? 1 : gpuid.size()) && !jobs_proc.empty())
    {
        fprintf(stderr, "invalid jobs_proc thread count argument\n");
        return -1;
    }

    for (int i = 0; i < (int)jobs_proc.size(); i++)
    {
        if (jobs_proc[i] < 1)
        {
            fprintf(stderr, "invalid jobs_proc thread count argument\n");
            return -1;
        }
    }

    // if (!path_is_directory(outputpath))
    // {
    //     // guess format from outputpath no matter what format argument specified
    //     path_t ext = get_file_extension(outputpath);
    //     if (ext == PATHSTR("png") || ext == PATHSTR("PNG"))
    //     {
    //         format = PATHSTR("png");
    //     }
    //     else if (ext == PATHSTR("webp") || ext == PATHSTR("WEBP"))
    //     {
    //         format = PATHSTR("webp");
    //     }
    //     else if (ext == PATHSTR("jpg") || ext == PATHSTR("JPG") || ext == PATHSTR("jpeg") || ext == PATHSTR("JPEG"))
    //     {
    //         format = PATHSTR("jpg");
    //     }
    //     else
    //     {
    //         fprintf(stderr, "invalid outputpath extension type\n");
    //         return -1;
    //     }
    // }
    format = PATHSTR("png");

    if (format != PATHSTR("png") && format != PATHSTR("webp") && format != PATHSTR("jpg"))
    {
        fprintf(stderr, "invalid format argument\n");
        return -1;
    }
    start_pipes();
    printf("%s rgb_mult: %d\n", log0, rgb_mult);
    receive_signals();
    int ret2 = read(fd0, initial_image_size, 4 * sizeof(unsigned char));
    write(fd1, "1", 1);
    filedata2 = (unsigned char *)malloc(initial_image_size[0]);
    read_pipe(filedata2, initial_image_size);
    write(fd1, "1", 1);

    // collect input and output filepath
    std::vector<path_t> input_files;
    std::vector<path_t> output_files;
    {
        if (filedata2)
        {
            std::vector<path_t> filenames;
            int lr = 0; //list_directory(inputpath, filenames);
            if (lr != 0)
                return -1;

            const int count = 1;
            input_files.resize(count);
            output_files.resize(count);

            path_t last_filename;
            path_t last_filename_noext;
            for (int i = 0; i < count; i++)
            {
                path_t filename = dain;
                path_t filename_noext = dain;
                path_t output_filename = dain;

                // filename list is sorted, check if output image path conflicts
                if (filename_noext == last_filename_noext)

                    last_filename = dain;
                last_filename_noext = dain;

                input_files[i] = dain;
                output_files[i] = dain;
            }
        }
        else if (!path_is_directory(inputpath) && !path_is_directory(outputpath))
        {
            input_files.push_back(inputpath);
            output_files.push_back(outputpath);
        }
        else
        {
            fprintf(stderr, "inputpath and outputpath must be either file or directory at the same time\n");
            return -1;
        }
    }

    int prepadding = 0;

    if (model.find(PATHSTR("models-cunet")) != path_t::npos)
    {
        if (noise == -1)
        {
            prepadding = 18;
        }
        else if (scale == 1)
        {
            prepadding = 28;
        }
        else if (scale == 2 || scale == 4 || scale == 8 || scale == 16 || scale == 32)
        {
            prepadding = 18;
        }
    }
    else if (model.find(PATHSTR("models-upconv_7_anime_style_art_rgb")) != path_t::npos)
    {
        prepadding = 7;
    }
    else if (model.find(PATHSTR("models-upconv_7_photo")) != path_t::npos)
    {
        prepadding = 7;
    }
    else
    {
        fprintf(stderr, "unknown model dir type\n");
        return -1;
    }

#if _WIN32
    wchar_t parampath[256];
    wchar_t modelpath[256];
    if (noise == -1)
    {
        swprintf(parampath, 256, L"%s/scale2.0x_model.param", model.c_str());
        swprintf(modelpath, 256, L"%s/scale2.0x_model.bin", model.c_str());
    }
    else if (scale == 1)
    {
        swprintf(parampath, 256, L"%s/noise%d_model.param", model.c_str(), noise);
        swprintf(modelpath, 256, L"%s/noise%d_model.bin", model.c_str(), noise);
    }
    else if (scale == 2 || scale == 4 || scale == 8 || scale == 16 || scale == 32)
    {
        swprintf(parampath, 256, L"%s/noise%d_scale2.0x_model.param", model.c_str(), noise);
        swprintf(modelpath, 256, L"%s/noise%d_scale2.0x_model.bin", model.c_str(), noise);
    }
#else
    char parampath[256];
    char modelpath[256];
    if (noise == -1)
    {
        sprintf(parampath, "%s/scale2.0x_model.param", model.c_str());
        sprintf(modelpath, "%s/scale2.0x_model.bin", model.c_str());
    }
    else if (scale == 1)
    {
        sprintf(parampath, "%s/noise%d_model.param", model.c_str(), noise);
        sprintf(modelpath, "%s/noise%d_model.bin", model.c_str(), noise);
    }
    else if (scale == 2 || scale == 4 || scale == 8 || scale == 16 || scale == 32)
    {
        sprintf(parampath, "%s/noise%d_scale2.0x_model.param", model.c_str(), noise);
        sprintf(modelpath, "%s/noise%d_scale2.0x_model.bin", model.c_str(), noise);
    }
#endif

    path_t paramfullpath = sanitize_filepath(parampath);
    path_t modelfullpath = sanitize_filepath(modelpath);

#if _WIN32
    CoInitializeEx(NULL, COINIT_MULTITHREADED);
#endif

    ncnn::create_gpu_instance();

    if (gpuid.empty())
    {
        gpuid.push_back(ncnn::get_default_gpu_index());
    }

    const int use_gpu_count = (int)gpuid.size();

    if (jobs_proc.empty())
    {
        jobs_proc.resize(use_gpu_count, 2);
    }

    if (tilesize.empty())
    {
        tilesize.resize(use_gpu_count, 0);
    }

    int cpu_count = std::max(1, ncnn::get_cpu_count());
    jobs_load = std::min(jobs_load, cpu_count);
    jobs_save = std::min(jobs_save, cpu_count);

    int gpu_count = ncnn::get_gpu_count();
    for (int i = 0; i < use_gpu_count; i++)
    {
        if (gpuid[i] < -1 || gpuid[i] >= gpu_count)
        {
            fprintf(stderr, "invalid gpu device\n");

            ncnn::destroy_gpu_instance();
            return -1;
        }
    }

    int total_jobs_proc = 0;
    for (int i = 0; i < use_gpu_count; i++)
    {
        if (gpuid[i] == -1)
        {
            jobs_proc[i] = std::min(jobs_proc[i], cpu_count);
            total_jobs_proc += 1;
        }
        else
        {
            int gpu_queue_count = ncnn::get_gpu_info(gpuid[i]).compute_queue_count();
            jobs_proc[i] = std::min(jobs_proc[i], gpu_queue_count);
            total_jobs_proc += jobs_proc[i];
        }
    }
    std::vector<ncnn::Thread *> proc_threads(total_jobs_proc);
    std::vector<ncnn::Thread *> save_threads(jobs_save);

    for (int i = 0; i < use_gpu_count; i++)
    {
        if (tilesize[i] != 0)
            continue;

        if (gpuid[i] == -1)
        {
            // cpu only
            tilesize[i] = 4000;
            continue;
        }

        uint32_t heap_budget = ncnn::get_gpu_device(gpuid[i])->get_heap_budget();

        // more fine-grained tilesize policy here
        if (model.find(PATHSTR("models-cunet")) != path_t::npos)
        {
            if (heap_budget > 2600)
                tilesize[i] = 400;
            else if (heap_budget > 740)
                tilesize[i] = 200;
            else if (heap_budget > 250)
                tilesize[i] = 100;
            else
                tilesize[i] = 32;
        }
        else if (model.find(PATHSTR("models-upconv_7_anime_style_art_rgb")) != path_t::npos || model.find(PATHSTR("models-upconv_7_photo")) != path_t::npos)
        {
            if (heap_budget > 1900)
                tilesize[i] = 400;
            else if (heap_budget > 550)
                tilesize[i] = 200;
            else if (heap_budget > 190)
                tilesize[i] = 100;
            else
                tilesize[i] = 32;
        }
    }

    {
        std::vector<Waifu2x *> waifu2x(use_gpu_count);

        for (int i = 0; i < use_gpu_count; i++)
        {
            int num_threads = gpuid[i] == -1 ? jobs_proc[i] : 1;

            waifu2x[i] = new Waifu2x(gpuid[i], tta_mode, num_threads);

            waifu2x[i]->load(paramfullpath, modelfullpath);

            waifu2x[i]->noise = noise;
            waifu2x[i]->scale = (scale >= 2) ? 2 : scale;
            waifu2x[i]->tilesize = tilesize[i];
            waifu2x[i]->prepadding = prepadding;
        }

        // main routine
        {
            // load image
            LoadThreadParams ltp;
            ltp.scale = scale;
            ltp.jobs_load = jobs_load;
            ltp.input_files = input_files;
            ltp.output_files = output_files;

            ncnn::Thread load_thread(load, (void *)&ltp);

            // waifu2x proc
            std::vector<ProcThreadParams> ptp(use_gpu_count);
            for (int i = 0; i < use_gpu_count; i++)
            {
                ptp[i].waifu2x = waifu2x[i];
                if (exiting == 1999999)
                    goto exit;
            }

            std::vector<ncnn::Thread *> proc_threads(total_jobs_proc);
            {
                int total_jobs_proc_id = 0;
                for (int i = 0; i < use_gpu_count; i++)
                {
                    if (gpuid[i] == -1)
                    {
                        proc_threads[total_jobs_proc_id++] = new ncnn::Thread(proc, (void *)&ptp[i]);
                    }
                    else
                    {
                        for (int j = 0; j < jobs_proc[i]; j++)
                        {
                            proc_threads[total_jobs_proc_id++] = new ncnn::Thread(proc, (void *)&ptp[i]);
                        }
                    }
                }
            }

            // save image
            SaveThreadParams stp;
            stp.verbose = verbose;

            std::vector<ncnn::Thread *> save_threads(jobs_save);
            for (int i = 0; i < jobs_save; i++)
            {
                save_threads[i] = new ncnn::Thread(save, (void *)&stp);
            }

            // end
            load_thread.join();

            Task end;
            end.id = -233;
            for (int i = 0; i < total_jobs_proc; i++)
            {
                toproc.put(end);
            }

            for (int i = 0; i < total_jobs_proc; i++)
            {
                proc_threads[i]->join();
                delete proc_threads[i];
            }

            for (int i = 0; i < jobs_save; i++)
            {
                tosave.put(end);
            }

            for (int i = 0; i < jobs_save; i++)
            {
                save_threads[i]->join();
                delete save_threads[i];
            }
        }
    exit:
        // load_thread.join();

        Task end;
        end.id = -233;
        for (int i = 0; i < total_jobs_proc; i++)
        {
            toproc.put(end);
        }

        for (int i = 0; i < total_jobs_proc; i++)
        {
            proc_threads[i]->join();
            delete proc_threads[i];
        }

        for (int i = 0; i < jobs_save; i++)
        {
            tosave.put(end);
        }

        for (int i = 0; i < jobs_save; i++)
        {
            save_threads[i]->join();
            delete save_threads[i];
        }
        for (int i = 0; i < use_gpu_count; i++)
        {
            delete waifu2x[i];
        }
        waifu2x.clear();
    }

    ncnn::destroy_gpu_instance();

    return 0;
}
