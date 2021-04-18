#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <inttypes.h>
#include <iostream>
#include <stdlib.h>
#include <time.h>
#include <fstream>


u_int32_t getTick()
{
    struct timespec ts;
    unsigned theTick = 0U;
    clock_gettime(CLOCK_REALTIME, &ts);
    theTick = ts.tv_nsec / 1000000;
    theTick += ts.tv_sec * 1000;
    return theTick;
}
void array_to_file(void *array, int nb_bytes_to_write, const char *path, const char *filename, int k)
{
    char buffer[250];
    sprintf(buffer, "%s/%s%d", path, filename, k);
    FILE *f3 = fopen(buffer, "wb");
    fwrite(array, sizeof(char), nb_bytes_to_write, f3);
    fflush(f3);
    fclose(f3);
}
void file_to_array(char array[], int array_size, int file_size, const char *path, const char *filename, int k)
{
    char buffer[250];
    sprintf(buffer, "%s%s", path, filename);
    //array =  (char*)malloc( array_size * sizeof(char));
    std::string inFileName = buffer;
    std::ifstream inFile(inFileName, std::ios::binary);
    int begin = inFile.tellg();
    inFile.seekg(0, std::ios::end);
    int end = inFile.tellg();
    inFile.seekg(0, std::ios::beg);
    inFile.read(array, file_size);
    inFile.close();
}

