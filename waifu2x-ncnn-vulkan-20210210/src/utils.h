#include <stdlib.h>
#include <inttypes.h>
u_int32_t getTick();

//Write an array to a file
void  array_to_file(void *array, int nb_bytes_to_write, const char *path, const char *filename, int k); 

//Read a file into an array in memory
void file_to_array(char array[], int array_size, int file_size, const char *path, const char *filename, int k); 

