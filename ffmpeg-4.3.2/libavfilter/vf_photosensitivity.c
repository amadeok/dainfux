/*
 * Copyright (c) 2019 Vladimir Panteleev
 *
 * This file is part of FFmpeg.
 *
 * FFmpeg is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * FFmpeg is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with FFmpeg; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 */

#include <float.h>

#include "libavutil/imgutils.h"
#include "libavutil/opt.h"
#include "libavutil/pixdesc.h"
#include "avfilter.h"

#include "formats.h"
#include "internal.h"
#include "video.h"
#include <sys/types.h>
#include <sys/stat.h>
#include <stdlib.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>

#define MAX_FRAMES 240
#define GRID_SIZE 8
#define NUM_CHANNELS 3
int i2 = 1;
int i3 = 0;
int i5 = 0;
int i8 = 0;
int i9 = 0;
int stop_frame = 0;

int stop_frame2 = 0;
int previousBel;
int previousSur;
int deltaBel;
int deltaSur;
int array[1294400];
int array2[1000];
int counter = 0;
int inter_frame_threshold = 0;
int block_to_interpolate = 0;
double globalSlowSpeed;
double globalIspeed;
int Globalnb_framesi2;
int globalNewBadness = 0;
int globalThreshold = 5;
int globalPhBypass = 1;
int goneBelowThreshold = 0;
int thresholdSurpassed = 0;
int globalLog;
int globalTSS;
int globalBadness;
int globalFpsfix60;
int wtinterpolate = 0;
int wtinterpolate_frame = 0;
FILE *fptr1;
FILE *fptr2;
FILE *fptr3;

FILE *fd;
FILE *fd2;
FILE *fd3;

int val = 0;
int val2 = 0;
int counterUp = 0;
int counterBel = 0;
int totFrames = 0;
int fd7;
int index = 0;
int new_part = 0;
int part_start_frame = 0;
int part_end_frame = 0;
int part_number = 0;
int block_frame_counter = 0;
int current_frame;
int part[1000][60000];
int wtinterpolateArray[60000];

int frame_for_block = 0;
int new_part_registered = 0;
int end_frame_set = 0;
int start_frame_set = 1;
int actual_start_frame = 0;
int actual_end_frame = 0;
int block_counter = -24;
int delta_frames = 0;
// FIFO file path
char *myfifo = "/tmp/ffmpeg_pipe";
int arr1[30000], arr2[80];
int array_frame_counter = 0;
int wtinterpolate_counter = 0;
int wtinterpolate_counter_part = 0;

int delta_frames_block = 0;

int current_part_start = 0;
int intro_start;
int intro_end;
int outro_start;
int outro_end;

typedef struct PhotosensitivityFrame
{
    uint8_t grid[GRID_SIZE][GRID_SIZE][4];
} PhotosensitivityFrame;

typedef struct PhotosensitivityContext
{
    const AVClass *class;
    int log;
    double SlowSpeed;
    double Ispeed;
    int nb_framesi2;
    int nb_frames;
    int TSS;
    int export_data;
    int skip;
    float threshold_multiplier;
    int bypass;
    int fpsfix60;
    int block_threshold;
    int badness_threshold;
    char *target_dir;
    int is;
    int ie;
    int os;
    int oe;
    int this_badness_thres;
    int use_newbadness;
    /* Circular buffer */
    int history[MAX_FRAMES];
    int history_pos;

    PhotosensitivityFrame last_frame_e;
    AVFrame *last_frame_av;
} PhotosensitivityContext;

#define OFFSET(x) offsetof(PhotosensitivityContext, x)
#define FLAGS AV_OPT_FLAG_VIDEO_PARAM | AV_OPT_FLAG_FILTERING_PARAM

static const AVOption photosensitivity_options[] = {
    {"frames", "set how many frames to use", OFFSET(nb_frames), AV_OPT_TYPE_INT, {.i64 = 30}, 2, MAX_FRAMES, FLAGS},
    {"f", "set how many frames to use", OFFSET(nb_frames), AV_OPT_TYPE_INT, {.i64 = 30}, 2, MAX_FRAMES, FLAGS},
    {"threshold", "set detection threshold factor (lower is stricter)", OFFSET(threshold_multiplier), AV_OPT_TYPE_FLOAT, {.dbl = 1}, 0.1, FLT_MAX, FLAGS},
    {"t", "set detection threshold factor (lower is stricter)", OFFSET(threshold_multiplier), AV_OPT_TYPE_FLOAT, {.dbl = 1}, 0.1, FLT_MAX, FLAGS},
    {"skip", "set pixels to skip when sampling frames", OFFSET(skip), AV_OPT_TYPE_INT, {.i64 = 1}, 1, 1024, FLAGS},
    {"bypass", "leave frames unchanged", OFFSET(bypass), AV_OPT_TYPE_BOOL, {.i64 = 0}, 0, 1, FLAGS},
    {"frames2", "set the number of frames to buffer for slowdown speed", OFFSET(nb_framesi2), AV_OPT_TYPE_INT, {.i64 = 96}, 2, 480, FLAGS},
    {"block_threshold", "threshold for the frame block", OFFSET(block_threshold), AV_OPT_TYPE_INT, {.i64 = 5}, 0, 24, FLAGS},
    {"is", "start time of intro", OFFSET(is), AV_OPT_TYPE_INT, {.i64 = 0}, 0, 1000000, FLAGS},
    {"ie", "end time of intro", OFFSET(ie), AV_OPT_TYPE_INT, {.i64 = 0}, 0, 1000000, FLAGS},
    {"os", "start time of outro", OFFSET(os), AV_OPT_TYPE_INT, {.i64 = 0}, 0, 1000000, FLAGS},
    {"oe", "end time of outro", OFFSET(oe), AV_OPT_TYPE_INT, {.i64 = 0}, 0, 1000000, FLAGS},
    {"TSS", "threshold for secondary slow speed", OFFSET(TSS), AV_OPT_TYPE_INT, {.i64 = 40000}, 1, 500000, FLAGS},
    {"export_data", "export data for DAIN interpolation", OFFSET(export_data), AV_OPT_TYPE_INT, {.i64 = 0}, 0, 100, FLAGS},
    {"slowspeed", "set slow speed", OFFSET(SlowSpeed), AV_OPT_TYPE_DOUBLE, {.dbl = 0.6}, 0.1, 1, FLAGS},
    {"ispeed", "set intermediate speed", OFFSET(Ispeed), AV_OPT_TYPE_DOUBLE, {.dbl = 1}, 0.1, 3, FLAGS},
    {"log", "turn on log or not", OFFSET(log), AV_OPT_TYPE_INT, {.i64 = 0}, 0, 50, FLAGS},
    {"this_badness_thres", "threshold for this_badness", OFFSET(this_badness_thres), AV_OPT_TYPE_BOOL, {.i64 = 100}, 0, 10000, FLAGS},
    {"use_newbadness", "use newbadness instead of thisbadness", OFFSET(use_newbadness), AV_OPT_TYPE_BOOL, {.i64 = 100}, 0, 1, FLAGS},

    {"fpsfix60", "fix for duplicated frames in 60fps videos", OFFSET(fpsfix60), AV_OPT_TYPE_BOOL, {.i64 = 0}, 0, 1, FLAGS},

    {"target_dir", "where to save parts", OFFSET(target_dir), AV_OPT_TYPE_STRING, {.str = "/home/"}, .flags = FLAGS},
    {NULL}};

AVFILTER_DEFINE_CLASS(photosensitivity);

static int query_formats(AVFilterContext *ctx)
{
    static const enum AVPixelFormat pixel_fmts[] = {
        AV_PIX_FMT_RGB24,
        AV_PIX_FMT_BGR24,
        AV_PIX_FMT_NONE};
    AVFilterFormats *formats = ff_make_format_list(pixel_fmts);
    if (!formats)
        return AVERROR(ENOMEM);
    return ff_set_common_formats(ctx, formats);
}

typedef struct ThreadData_convert_frame
{
    AVFrame *in;
    PhotosensitivityFrame *out;
    int skip;
} ThreadData_convert_frame;

#define NUM_CELLS (GRID_SIZE * GRID_SIZE)

static int convert_frame_partial(AVFilterContext *ctx, void *arg, int jobnr, int nb_jobs)
{
    int cell, gx, gy, x0, x1, y0, y1, x, y, c, area;
    int sum[NUM_CHANNELS];
    const uint8_t *p;

    ThreadData_convert_frame *td = arg;

    const int slice_start = (NUM_CELLS * jobnr) / nb_jobs;
    const int slice_end = (NUM_CELLS * (jobnr + 1)) / nb_jobs;

    int width = td->in->width, height = td->in->height, linesize = td->in->linesize[0], skip = td->skip;
    const uint8_t *data = td->in->data[0];

    for (cell = slice_start; cell < slice_end; cell++)
    {
        gx = cell % GRID_SIZE;
        gy = cell / GRID_SIZE;

        x0 = width * gx / GRID_SIZE;
        x1 = width * (gx + 1) / GRID_SIZE;
        y0 = height * gy / GRID_SIZE;
        y1 = height * (gy + 1) / GRID_SIZE;

        for (c = 0; c < NUM_CHANNELS; c++)
        {
            sum[c] = 0;
        }
        for (y = y0; y < y1; y += skip)
        {
            p = data + y * linesize + x0 * NUM_CHANNELS;
            for (x = x0; x < x1; x += skip)
            {
                //av_log(NULL, AV_LOG_VERBOSE, "%d %d %d : (%d,%d) (%d,%d) -> %d,%d | *%d\n", c, gx, gy, x0, y0, x1, y1, x, y, (int)row);
                sum[0] += p[0];
                sum[1] += p[1];
                sum[2] += p[2];
                p += NUM_CHANNELS * skip;
                // TODO: variable size
            }
        }

        area = ((x1 - x0 + skip - 1) / skip) * ((y1 - y0 + skip - 1) / skip);
        for (c = 0; c < NUM_CHANNELS; c++)
        {
            if (area)
                sum[c] /= area;
            td->out->grid[gy][gx][c] = sum[c];
        }
    }
    return 0;
}

static void convert_frame(AVFilterContext *ctx, AVFrame *in, PhotosensitivityFrame *out, int skip)
{
    ThreadData_convert_frame td;
    td.in = in;
    td.out = out;
    td.skip = skip;
    ctx->internal->execute(ctx, convert_frame_partial, &td, NULL, FFMIN(NUM_CELLS, ff_filter_get_nb_threads(ctx)));
}

typedef struct ThreadData_blend_frame
{
    AVFrame *target;
    AVFrame *source;
    uint16_t s_mul;
} ThreadData_blend_frame;

static int blend_frame_partial(AVFilterContext *ctx, void *arg, int jobnr, int nb_jobs)
{
    int x, y;
    uint8_t *t, *s;

    ThreadData_blend_frame *td = arg;
    const uint16_t s_mul = td->s_mul;
    const uint16_t t_mul = 0x100 - s_mul;
    const int slice_start = (td->target->height * jobnr) / nb_jobs;
    const int slice_end = (td->target->height * (jobnr + 1)) / nb_jobs;
    const int linesize = td->target->linesize[0];

    for (y = slice_start; y < slice_end; y++)
    {
        t = td->target->data[0] + y * td->target->linesize[0];
        s = td->source->data[0] + y * td->source->linesize[0];
        for (x = 0; x < linesize; x++)
        {
            *t = (*t * t_mul + *s * s_mul) >> 8;
            t++;
            s++;
        }
    }
    return 0;
}

static void blend_frame(AVFilterContext *ctx, AVFrame *target, AVFrame *source, float factor)
{
    ThreadData_blend_frame td;
    td.target = target;
    td.source = source;
    td.s_mul = (uint16_t)(factor * 0x100);
    ctx->internal->execute(ctx, blend_frame_partial, &td, NULL, FFMIN(ctx->outputs[0]->h, ff_filter_get_nb_threads(ctx)));
}

static int get_badness(PhotosensitivityFrame *a, PhotosensitivityFrame *b)
{
    int badness, x, y, c;
    badness = 0;
    for (c = 0; c < NUM_CHANNELS; c++)
    {
        for (y = 0; y < GRID_SIZE; y++)
        {
            for (x = 0; x < GRID_SIZE; x++)
            {
                badness += abs((int)a->grid[y][x][c] - (int)b->grid[y][x][c]);
                //av_log(NULL, AV_LOG_VERBOSE, "%d - %d -> %d \n", a->grid[y][x], b->grid[y][x], badness);
                //av_log(NULL, AV_LOG_VERBOSE, "%d -> %d \n", abs((int)a->grid[y][x] - (int)b->grid[y][x]), badness);
            }
        }
    }
    return badness;
}

void *wtinterpolateT()
{
    sleep(3);
    i9 = 1;
    printf("thread\n");
    while (1)
    {

        while (totFrames - i8 <= 100)
        {
            int st = 300 * 1000;
            usleep(st);
            //   printf("sleeping");
        }
        //printf("%d / %d / %d / \n", totFrames, i8, wtinterpolateArray[i8]);

        fprintf(fd2, "%d ", wtinterpolateArray[i8]);
        stop_frame = part[i9][2];

        if (i8 == stop_frame && stop_frame != 0)
        {
            fprintf(fd2, "\n");
            i9++;
        }
        fflush(fd2);

        //printf("%6d ", part[1][1]);
        i8++;
    }
    return NULL;
}

static int config_input(AVFilterLink *inlink)
{
    /* const AVPixFmtDescriptor *desc = av_pix_fmt_desc_get(inlink->format); */
    AVFilterContext *ctx = inlink->dst;
    PhotosensitivityContext *s = ctx->priv;
    Globalnb_framesi2 = s->nb_framesi2;
    globalIspeed = s->Ispeed;
    globalSlowSpeed = s->SlowSpeed;
    globalLog = s->log;
    globalPhBypass = s->bypass;
    globalTSS = s->TSS;
    globalFpsfix60 = s->fpsfix60;

    mkdir(s->target_dir, 0777);
    if (s->export_data == 1)
    {
        fptr1 = fopen("/content/data1.txt", "w+");
    }
    else if (s->export_data == 2)
    {
        fptr2 = fopen("/content/data2.txt", "w+");
    }
    else if (s->export_data == 3)
    {
        fptr3 = fopen("/content/data3.txt", "w+");
    }
    s->badness_threshold = (int)(GRID_SIZE * GRID_SIZE * 4 * 256 * s->nb_frames * s->threshold_multiplier / 128);
    globalThreshold = s->badness_threshold;
    part[part_number][5] = 24;

    // mkfifo(myfifo, 0666);
    // sigaction(SIGPIPE, &(struct sigaction){SIG_IGN}, NULL);
    if (s->export_data == 4)
    {
        printf("target_dir %s\n", s->target_dir);
        intro_start = s->is * s->nb_frames;
        intro_end = s->ie * s->nb_frames;
        outro_start = s->os * s->nb_frames;
        outro_end = s->oe * s->nb_frames;

        char parts_dir[200];
        char wtinterpolate_dir[200];

        char working_dir[200];
        char conf_file[200];

        // getcwd(working_dir, sizeof(working_dir));
        // sprintf(conf_file, "%s/%s", working_dir,  "conf_file.txt");
        // printf("conf_file %s\n", conf_file );

        // FILE *in_file  = fopen(conf_file, "r"); // read only
        // fgets(target_dir, 255, (FILE*)in_file);
        // target_dir[strcspn(target_dir, "\n")] = 0;

        // printf("target_dir %s\n", target_dir );
        // fclose(in_file);

        sprintf(parts_dir, "%s/%s", s->target_dir, "parts.txt");
        printf("parts_dir %s\n", parts_dir);
        sprintf(wtinterpolate_dir, "%s/%s", s->target_dir, "wtinterpolate.txt");
        printf("wtinterpolate_dir %s\n", wtinterpolate_dir);

        fd = fopen(parts_dir, "w+");
        fd2 = fopen(wtinterpolate_dir, "w+");
        //  fd3 = fopen("/content/misc.txt", "w+");
    }
    //  pthread_t inter;
    //  pthread_create(&inter, NULL, wtinterpolateT, NULL);

    return 0;
}

static int filter_frame(AVFilterLink *inlink, AVFrame *in)
{
    int this_badness, current_badness, fixed_badness, new_badness, i, res;
    PhotosensitivityFrame ef;
    AVFrame *src, *out;
    int free_in = 0;
    float factor;
    AVDictionary **metadata;

    AVFilterContext *ctx = inlink->dst;
    AVFilterLink *outlink = ctx->outputs[0];
    PhotosensitivityContext *s = ctx->priv;
    int current_this_badness, previous_this_badness;

    /* weighted moving average */
    current_badness = 0;
    for (i = 1; i < s->nb_frames; i++)
        current_badness += i * s->history[(s->history_pos + i) % s->nb_frames];
    current_badness /= s->nb_frames;

    convert_frame(ctx, in, &ef, s->skip);
    this_badness = get_badness(&ef, &s->last_frame_e);
    new_badness = current_badness + this_badness;

    current_this_badness = this_badness;

    av_log(s, AV_LOG_VERBOSE, "badness: %6d -> %6d / %6d (%3d%% - %s)\n",
           current_badness, new_badness, s->badness_threshold,
           100 * new_badness / s->badness_threshold, new_badness < s->badness_threshold ? "OK" : "EXCEEDED");
    /*
        i5++;
    if (i5 == 1294399)
        i5 = 0;
    if (i5 % 2 == 0)
    {
        array2[i5] = this_badness;
    }
    else if (i5 % 2 != 0)
    {
        array2[i5] = this_badness;
    }
    if (globalFpsfix60)
    {

        if (array2[i5 - 1] > 150 && array2[i5] < 25)
        {
            printf("1'");
            this_badness = array2[i5 - 1] * 0.17;
        }

        if (array2[i5 - 2] > 150 && array2[i5] < 25 && array2[i5 - 1] < 25)
        {
            printf("2'");
            this_badness = array2[i5 - 2] * 0.17;
        }

        if (array2[i5 - 3] > 150 && array2[i5] < 25 && array2[i5 - 1] < 25 && array2[i5 - 2] < 25)
        {
            printf("3'");
            this_badness = array2[i5 - 3] * 0.17;
        }

        if (array2[i5 - 4] > 150 && array2[i5] < 25 && array2[i5 - 1] < 25 && array2[i5 - 2] < 25 && array2[i5 - 3] < 25)

        {
            printf("4'");
            this_badness = array2[i5 - 4] * 0.17;
        }
        if (array2[i5 - 5] > 150 && array2[i5] < 25 && array2[i5 - 1] < 25 && array2[i5 - 2] < 25 && array2[i5 - 3] < 25 && array2[i5 - 4] < 25)
        {
            printf("5'");
            this_badness = array2[i5 - 5] * 0.17;
        }
    }
        if (globalLog >= 4)
    {

        printf("%i / ", i5);
        printf("[%d ", array2[i5]);
        printf(" %d ", array2[i5 - 1]);
        printf(" %d", array2[i5 - 2]);
        printf(" %d]", array2[i5 - 3]);

        printf(" ** %d ** \n", this_badness);
    }
    // globalCurrentBadness = current_badness;
    globalNewBadness = new_badness;
    */
    if (s->export_data == 4)
    {
        if (s->use_newbadness == 0)
        {
            if (totFrames > intro_start && totFrames < intro_end || totFrames > outro_start && totFrames < outro_end || this_badness < s->this_badness_thres)
                wtinterpolate_frame = 0;
            else
                wtinterpolate_frame = 1;
        }
        else
        {
            if (totFrames > intro_start && totFrames < intro_end || totFrames > outro_start && totFrames < outro_end || new_badness < s->badness_threshold)
                wtinterpolate_frame = 0;
            else if (current_this_badness > s->this_badness_thres)
                wtinterpolate_frame = 1;
            else
                wtinterpolate_frame = 0;
        }
        array_frame_counter++;
        wtinterpolateArray[array_frame_counter] = wtinterpolate_frame;
        if (block_frame_counter == 24)
        {
            inter_frame_threshold = 5;
            i = totFrames - 24;
            for (i; i < totFrames; i++)
                if (wtinterpolateArray[i] == 1)
                    wtinterpolate_counter = wtinterpolate_counter + 1;

            if (wtinterpolate_counter >= s->block_threshold)
                block_to_interpolate = 1;
            else if (part_number == 0)
                block_to_interpolate = 1;
            else
                block_to_interpolate = 0;
            wtinterpolate_counter = 0;

            block_counter += 24;
            block_frame_counter = 0;
        }
        block_frame_counter++;

        if (arr1[i2] != arr1[i2 - 1])
        {
            int added_to_end_part = 0;

            part_end_frame = block_counter;
            part[part_number][2] = part_end_frame;

            index = part_number - 1;
            part[part_number][0] = index;
            added_to_end_part = block_counter;

            delta_frames_block = part[part_number][2] - part[part_number][1];

            i = part[part_number][1];
            for (i; i < part_end_frame; i++)
            {
                if (wtinterpolateArray[i] == 1)
                    wtinterpolate_counter_part = wtinterpolate_counter_part + 1;
            }
            part[part_number][4] = delta_frames_block;
            part[part_number][5] = wtinterpolate_counter_part;
            wtinterpolate_counter_part = 0;
            if (block_to_interpolate == 0)
                added_to_end_part = added_to_end_part + 1;
            current_part_start = part[part_number][1];
            fprintf(fd, "%6d ", part[part_number][0]); //index
            fprintf(fd, "%6d ", part[part_number][1]); //start frame
            fprintf(fd, "%6d ", added_to_end_part);    //end frame
            fprintf(fd, "%6d ", part[part_number][3]); //whether to interpolate
            fprintf(fd, "%6d ", part[part_number][4]); //delta
            fprintf(fd, "%6d ", part[part_number][5]); //nb of freames to interpoalte

            // fprintf(fd, "%6d ", part[part_number][4]); // actual start frame
            // fprintf(fd, "%6d ", part[part_number][5]); //actual end frame
            fprintf(fd, "\n");
            //  fflush(fd);
            //    delta_frames = part[part_number][2] - part[part_number[1];

            for (current_part_start; current_part_start < part_end_frame; current_part_start++)
                fprintf(fd2, "%d ", wtinterpolateArray[current_part_start]);
            fprintf(fd2, "\n");
            // fflush(fd2);

            part_number++;
            part[part_number][1] = part[part_number - 1][2];

            part[part_number][3] = block_to_interpolate;
        }
    }

    i2++;
    if (i2 == 1294399)
        i2 = 0;
    if (i2 % 2 == 0)
    {
        array[i2] = new_badness;
        arr1[i2] = block_to_interpolate;
    }
    else if (i2 % 2 != 0)
    {
        array[i2] = new_badness;
        arr1[i2] = block_to_interpolate;
    }

    //printf("%i / ", i2);
    //printf("%i / ", i2 - 1);
    int val = i2 - 1;
    //printf("%d ", array[i2]);
    //printf("%d \n", array[i2 -1]);
    if (array[i2 - 1] <= s->badness_threshold && array[i2] > s->badness_threshold)
    {
        thresholdSurpassed = 1;
        if (s->log)
            printf("up /");
    }
    else
        thresholdSurpassed = 0;

    if (array[i2 - 1] >= s->badness_threshold && array[i2] < s->badness_threshold)
    {
        goneBelowThreshold = 1;
        if (s->log)
            printf("dw /");
    }
    else
        goneBelowThreshold = 0;
    /*
    deltaBel = (i2 - previousBel);
    if (deltaBel > s->nb_framesi2 && goneBelowThreshold == 1)
    {
        previousBel = i2;
        // printf("i printed");
    } 
    deltaSur = (i2 - previousSur);
    if (deltaSur > 12 && thresholdSurpassed == 1)
    {
        previousSur = i2;
        // printf("i printed");
    }
    */
    if (s->export_data != 4 && new_badness > s->badness_threshold)
        counterUp++;
    else if (s->export_data == 4 && wtinterpolate_frame == 1)
        counterUp++;
    else
        counterBel++;
    totFrames++;

    if (s->log == 6)
    {
        printf("frames up: %i \n", counterUp);
        printf("frames below: %i \n", counterBel);
    }

    if (s->log <= 2 && s->log > 0)
    {
        if (s->log == 5)
        {
            fprintf(fptr2, "frame: %i /", totFrames);
            fprintf(fptr2, "%d /", this_badness);
        }
        printf("frame: %i / ", totFrames);
        // printf("%f/", totFrames / 2.5);

        //  printf("%d /", globalBadness);
        if (s->log >= 15)
        {

            printf("%i /", deltaBel);
            printf("%i /", deltaSur);
        }
        //   printf("%i /", current_badness);
        //  if (log == 4)
        printf("%i /", current_this_badness);

        printf("%i / %i \n", new_badness, wtinterpolate_frame);
        //   else
        //       printf("%i /", new_badness);
        //     printf("%i /", s->nb_framesi2);
        //     printf("%i  \n", goneBelowThreshold);
    }

    // if (thresholdSurpassed == 1 || goneBelowThreshold == 1)
    // {
    //     current_frame = totFrames;
    //     actual_end_frame = totFrames;
    //     if (wtinterpolate == 1)
    //     {
    //         part_end_frame = 24 * (current_frame / 24 + 1);
    //     }
    //     else if (wtinterpolate == 0)
    //     {
    //         part_end_frame = current_frame - current_frame % 24;
    //     }
    //     part[part_number][2] = part_end_frame;
    //     part[part_number][5] = actual_end_frame;
    //     //    if (part[part_number][1] != part[part_number][2])
    //     index = part_number;
    //     part[part_number][0] = index;
    //     if (part[part_number][5] - part[part_number][4] >= 24)
    //     {
    //         fprintf(fd, "%6d ", part[part_number][0]); //index
    //         fprintf(fd, "%6d ", part[part_number][1]); //start frame
    //         fprintf(fd, "%6d ", part[part_number][2]); //end frame
    //         fprintf(fd, "%6d ", part[part_number][3]); //whether to interpolate
    //         fprintf(fd, "%6d ", part[part_number][4]); // actual start frame
    //         fprintf(fd, "%6d ", part[part_number][5]); //actual end frame
    //         fprintf(fd, "\n");
    //         fflush(fd);
    //         part_number++;
    //         new_part = 1;
    //     }
    //     part[part_number][1] = part[part_number - 1][2]; // set start frame same as previous part's end frame
    //     part[part_number][4] = actual_end_frame;         // ""
    //     if (thresholdSurpassed == 1)
    //         wtinterpolate = 1;
    //     else if (goneBelowThreshold == 1)
    //         wtinterpolate = 0;
    //     part[part_number][3] = wtinterpolate;
    // }
    // fprintf(fd, " %d", wtinterpolate_frame);
    //fflush(fd);
    //     part_end_frame = current_frame - current_frame % 24; // start frame is equal to current frame minus it's remainder of division by 24
    //    part[part_number][2] = part_end_frame;
    //  new_part_registered = 1;
    //   part_start_frame = current_frame - current_frame % 24;
    //  part[part_number][1] = part_start_frame;

    if (new_part_registered)
    {
        part_start_frame = current_frame - current_frame % 24;
        part[part_number][1] = part_start_frame;
        new_part_registered = 0;
    }

    if (s->export_data == 1)
    {
        if (new_badness > s->badness_threshold)
            wtinterpolate = 1;
        else
            wtinterpolate = 0;
        //fprintf(fptr1, "%i %i\n", totFrames, wtinterpolate);
        fprintf(fptr1, "%i\n", wtinterpolate);

        fflush(fptr1);
        //printf("checkpoint");
    }
    else if (s->export_data == 2)
    {
        if (new_badness > s->badness_threshold)
            wtinterpolate = 1;
        else
            wtinterpolate = 0;
        fprintf(fptr2, "%i", totFrames);
        rewind(fptr2);
        fflush(fptr2);
        //printf("checkpoint");
    }

    fixed_badness = new_badness;
    if (new_badness < s->badness_threshold || !s->last_frame_av || s->bypass)
    {
        factor = 1; /* for metadata */
        av_frame_free(&s->last_frame_av);
        s->last_frame_av = src = in;
        s->last_frame_e = ef;
        s->history[s->history_pos] = this_badness;
    }
    else
    {
        factor = (float)(s->badness_threshold - current_badness) / (new_badness - current_badness);
        if (factor <= 0)
        {
            /* just duplicate the frame */
            s->history[s->history_pos] = 0; /* frame was duplicated, thus, delta is zero */
        }
        else
        {
            res = av_frame_make_writable(s->last_frame_av);
            if (res)
            {
                av_frame_free(&in);
                return res;
            }
            blend_frame(ctx, s->last_frame_av, in, factor);

            convert_frame(ctx, s->last_frame_av, &ef, s->skip);
            this_badness = get_badness(&ef, &s->last_frame_e);
            fixed_badness = current_badness + this_badness;
            av_log(s, AV_LOG_VERBOSE, "  fixed: %6d -> %6d / %6d (%3d%%) factor=%5.3f\n",
                   current_badness, fixed_badness, s->badness_threshold,
                   100 * new_badness / s->badness_threshold, factor);
            s->last_frame_e = ef;
            s->history[s->history_pos] = this_badness;
        }
        src = s->last_frame_av;
        free_in = 1;
    }
    s->history_pos = (s->history_pos + 1) % s->nb_frames;

    out = ff_get_video_buffer(outlink, in->width, in->height);
    if (!out)
    {
        if (free_in == 1)
            av_frame_free(&in);
        return AVERROR(ENOMEM);
    }
    av_frame_copy_props(out, in);
    metadata = &out->metadata;
    if (metadata)
    {
        char value[128];

        snprintf(value, sizeof(value), "%f", (float)new_badness / s->badness_threshold);
        av_dict_set(metadata, "lavfi.photosensitivity.badness", value, 0);

        snprintf(value, sizeof(value), "%f", (float)fixed_badness / s->badness_threshold);
        av_dict_set(metadata, "lavfi.photosensitivity.fixed-badness", value, 0);

        snprintf(value, sizeof(value), "%f", (float)this_badness / s->badness_threshold);
        av_dict_set(metadata, "lavfi.photosensitivity.frame-badness", value, 0);

        snprintf(value, sizeof(value), "%f", factor);
        av_dict_set(metadata, "lavfi.photosensitivity.factor", value, 0);
    }
    av_frame_copy(out, src);
    if (free_in == 1)
        av_frame_free(&in);
    return ff_filter_frame(outlink, out);
}

static av_cold void uninit(AVFilterContext *ctx)
{
    PhotosensitivityContext *s = ctx->priv;

    if (s->export_data == 1)
    {
        fptr1 = fopen("/content/data1.txt", "w+");
    }
    else if (s->export_data == 2)
    {
        fptr2 = fopen("/content/data2.txt", "w+");
    }
    if (s->export_data == 4)
    {
        int i;
        block_counter += 24;
        current_frame = totFrames;

        part_end_frame = totFrames;
        part[part_number][2] = part_end_frame;

        index = part_number - 1;
        part[part_number][0] = index;
        current_part_start = part[part_number][1];

        i = part[part_number][1];
        for (i; i < part_end_frame; i++)
        {
            if (wtinterpolateArray[i] == 1)
                wtinterpolate_counter_part = wtinterpolate_counter_part + 1;
        }

        delta_frames_block = part[part_number][2] - part[part_number][1];
        part[part_number][4] = delta_frames_block;
        part[part_number][5] = wtinterpolate_counter_part;

        fprintf(fd, "%6d ", part[part_number][0]); //index
        fprintf(fd, "%6d ", part[part_number][1]); //start frame
        fprintf(fd, "%6d ", part[part_number][2]); //end frame
        fprintf(fd, "%6d ", part[part_number][3]); //whether to interpolate
        fprintf(fd, "%6d ", part[part_number][4]); //delta
        fprintf(fd, "%6d ", part[part_number][5]); //nb of freames to interpoalte

        fprintf(fd, "\n");
        fflush(fd);
        for (current_part_start; current_part_start < part_end_frame; current_part_start++)
            fprintf(fd2, "%d ", wtinterpolateArray[current_part_start]);
        fprintf(fd2, "\n");
        fflush(fd2);

        // fprintf(fd3, "total frames: %d, ", totFrames);
        // fprintf(fd3, "total frames to interpolate: %d", counterUp);
        //printf("checkpoint");
    }
    av_frame_free(&s->last_frame_av);
}

static const AVFilterPad inputs[] = {
    {
        .name = "default",
        .type = AVMEDIA_TYPE_VIDEO,
        .filter_frame = filter_frame,
        .config_props = config_input,
    },
    {NULL}};

static const AVFilterPad outputs[] = {
    {
        .name = "default",
        .type = AVMEDIA_TYPE_VIDEO,
    },
    {NULL}};

AVFilter ff_vf_photosensitivity = {
    .name = "photosensitivity",
    .description = NULL_IF_CONFIG_SMALL("Filter out photosensitive epilepsy seizure-inducing flashes."),
    .priv_size = sizeof(PhotosensitivityContext),
    .priv_class = &photosensitivity_class,
    .uninit = uninit,
    .query_formats = query_formats,
    .inputs = inputs,
    .outputs = outputs,
};
