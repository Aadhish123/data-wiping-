#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define BUFFER_SIZE 4096

// Fill buffer with zeros
void fill_zeros(char *buffer, size_t size) {
    for (size_t i = 0; i < size; i++) {
        buffer[i] = 0x00;
    }
}

// Fill buffer with random bytes
void fill_random(char *buffer, size_t size) {
    for (size_t i = 0; i < size; i++) {
        buffer[i] = rand() % 256;
    }
}

// Overwrite the entire file with chosen pattern
int overwrite_file_with_pattern(const char *filename, int pattern) {
    FILE *f = fopen(filename, "r+b"); // open file for reading and writing in binary
    if (!f) {
        perror("Failed to open file");
        return 1;
    }

    // Get file size
    fseek(f, 0, SEEK_END);
    size_t file_size = ftell(f);
    rewind(f);

    char buffer[BUFFER_SIZE];
    size_t total_written = 0;

    while (total_written < file_size) {
        size_t to_write = BUFFER_SIZE;
        if (file_size - total_written < BUFFER_SIZE) {
            to_write = file_size - total_written;
        }

        if (pattern == 0) {
            fill_zeros(buffer, to_write);
        } else if (pattern == 1) {
            fill_random(buffer, to_write);
        } else {
            fprintf(stderr, "Unknown pattern\n");
            fclose(f);
            return 1;
        }

        size_t written = fwrite(buffer, 1, to_write, f);
        if (written != to_write) {
            perror("Write error");
            fclose(f);
            return 1;
        }
        total_written += written;
    }

    fflush(f);
    fclose(f);
    return 0;
}

int main(int argc, char *argv[]) {
    if (argc < 3) {
        printf("Usage: %s <filename> <pattern: 0=zero, 1=random>\n", argv[0]);
        return 1;
    }

    srand((unsigned int)time(NULL)); // seed random number generator

    if (overwrite_file_with_pattern(argv[1], atoi(argv[2])) == 0) {
        printf("Successfully overwritten '%s'\n", argv[1]);
        if(remove(argv[1])==0){
            printf("%s deleted successfully",argv[1]);
        }
        else{
            perror("file not found");
        }
    } 
    else {
        printf("Failed to overwrite '%s'\n", argv[1]);
    }

    return 0;
}

