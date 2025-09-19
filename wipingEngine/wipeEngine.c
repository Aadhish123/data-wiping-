#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>

#define BUFFER_SIZE 4096

// --- Secure wipe functions ---
void fill_zeros(char *buffer, size_t size) {
    for (size_t i = 0; i < size; i++) {
        buffer[i] = 0x00;
    }
}

void fill_random(char *buffer, size_t size) {
    for (size_t i = 0; i < size; i++) {
        buffer[i] = rand() % 256;
    }
}

int overwrite_file_with_pattern(const char *filename, int pattern) {
    FILE *f = fopen(filename, "r+b"); 
    if (!f) {
        return 1; // skip if can't open
    }

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
        } else {
            fill_random(buffer, to_write);
        }

        size_t written = fwrite(buffer, 1, to_write, f);
        if (written != to_write) {
            fclose(f);
            return 1;
        }
        total_written += written;
    }

    fflush(f);
    fclose(f);
    return remove(filename);  // delete after overwrite
}

// --- Directory traversal ---
void listFilesAndFolders(char *directory, int deleteMode, int pattern) {
    WIN32_FIND_DATA findFileData;
    HANDLE hFind;

    char searchPath[MAX_PATH];
    snprintf(searchPath, MAX_PATH, "%s\\*", directory);

    hFind = FindFirstFile(searchPath, &findFileData);

    if (hFind == INVALID_HANDLE_VALUE) {
        return;
    }

    do {
        if (strcmp(findFileData.cFileName, ".") != 0 && strcmp(findFileData.cFileName, "..") != 0) {
            char fullPath[MAX_PATH];
            snprintf(fullPath, MAX_PATH, "%s\\%s", directory, findFileData.cFileName);

            if (findFileData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
                printf("[DIR]  %s\n", fullPath);
                listFilesAndFolders(fullPath, deleteMode, pattern);
            } else {
                if (deleteMode == 0) {
                    // Listing only
                    printf("[FILE] %s\n", fullPath);
                } else {
                    // Wiping & deleting
                    printf("[FILE] %s -> wiping... ", fullPath);
                    if (overwrite_file_with_pattern(fullPath, pattern) == 0) {
                        printf("Deleted\n");
                    } else {
                        printf("Failed\n");
                    }
                }
            }
        }
    } while (FindNextFile(hFind, &findFileData) != 0);

    FindClose(hFind);
}

// --- Main ---
int main() {
    char dir[260];
    int pattern;
    char choice;

    printf("Enter the partition of Disk (e.g., C): ");
    scanf("%259s", dir);
    strcat(dir, ":\\");

    printf("\nListing all files in %s ...\n", dir);
    listFilesAndFolders(dir, 0, 0); // just list, no delete

     printf("\nDo you want to delete ALL these files? (y/n): ");
    scanf(" %c", &choice);

    if (choice == 'y' || choice == 'Y') {
        printf("Enter wipe pattern (0 = zeros, 1 = random): ");
        scanf("%d", &pattern);

        srand((unsigned int)time(NULL));
        printf("\nWiping files in %s ...\n", dir);
        listFilesAndFolders(dir, 1, pattern);
        printf("\nCompleted.\n");
    } else {
        printf("\nAborted. No files were deleted.\n");
    }

    return 0;
}
