#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>

#define BUFFER_SIZE 4096

// Forward declaration
int wipe_file(const char *filepath, const char *method, int is_part_of_folder);

void overwrite_pass(FILE *f, long long file_size, int pass_num, int total_passes, char pattern) {
    rewind(f);
    char buffer[BUFFER_SIZE];
    long long total_written = 0;
    char pass_desc[50];

    if (pattern == 0x00) {
        memset(buffer, 0x00, BUFFER_SIZE);
        snprintf(pass_desc, 50, "Writing zeros (0x00)...");
    } else if (pattern == 0xFF) {
        memset(buffer, 0xFF, BUFFER_SIZE);
        snprintf(pass_desc, 50, "Writing ones (0xFF)...");
    } else if ((unsigned char)pattern == 0x55) {
        memset(buffer, 0x55, BUFFER_SIZE);
        snprintf(pass_desc, 50, "Writing pattern 0x55...");
    } else if ((unsigned char)pattern == 0xAA) {
        memset(buffer, 0xAA, BUFFER_SIZE);
        snprintf(pass_desc, 50, "Writing pattern 0xAA...");
    } else {
        snprintf(pass_desc, 50, "Writing random data...");
    }
    
    printf("  Pass %d of %d: %s\n", pass_num, total_passes, pass_desc);

    while (total_written < file_size) {
        size_t to_write = BUFFER_SIZE;
        if (file_size - total_written < BUFFER_SIZE) to_write = (size_t)(file_size - total_written);
        
        if (strcmp(pass_desc, "Writing random data...") == 0) {
            for (size_t i = 0; i < to_write; i++) buffer[i] = rand() % 256;
        }
        
        fwrite(buffer, 1, to_write, f);
        total_written += to_write;
    }
    fflush(f);
}

int wipe_folder_recursive(const char *basePath, const char *method) {
    WIN32_FIND_DATA findFileData;
    char searchPath[MAX_PATH];
    snprintf(searchPath, MAX_PATH, "%s\\*", basePath);
    HANDLE hFind = FindFirstFile(searchPath, &findFileData);

    if (hFind == INVALID_HANDLE_VALUE) {
        fprintf(stderr, "ERROR: Cannot access folder '%s'.\n", basePath);
        return 1;
    }

    do {
        if (strcmp(findFileData.cFileName, ".") != 0 && strcmp(findFileData.cFileName, "..") != 0) {
            char fullPath[MAX_PATH];
            snprintf(fullPath, MAX_PATH, "%s\\%s", basePath, findFileData.cFileName);

            if (findFileData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
                wipe_folder_recursive(fullPath, method);
            } else {
                wipe_file(fullPath, method, 1);
            }
        }
    } while (FindNextFile(hFind, &findFileData) != 0);

    FindClose(hFind);
    
    // **NEW**: Remove read-only attribute from the folder itself before trying to delete it.
    SetFileAttributes(basePath, FILE_ATTRIBUTE_NORMAL);
    
    if (RemoveDirectory(basePath)) {
        printf("[Folder] Deleted empty directory: %s\n", basePath);
    } else {
        // We can ignore this error for the root drive (e.g., "E:\") as it can't be deleted.
        if (strlen(basePath) > 3) { 
             printf("[Folder] Could not delete directory (might be in use): %s\n", basePath);
        }
    }
    return 0;
}

int wipe_file(const char *filepath, const char *method, int is_part_of_folder) {
    if (!is_part_of_folder) {
        printf("Zero Leaks Wiping Engine v0.5\n");
        printf("------------------------------------\n");
        printf("Target: %s\n", filepath);
        printf("------------------------------------\n");
    } else {
        printf("[File] Wiping: %s\n", filepath);
    }
    
    // **NEW**: Forcefully remove protected attributes (Read-Only, Hidden, System) from the file.
    DWORD attrs = GetFileAttributes(filepath);
    if (attrs != INVALID_FILE_ATTRIBUTES && (attrs & (FILE_ATTRIBUTE_READONLY | FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM))) {
        printf("  NOTE: Removing protected attributes from file.\n");
        SetFileAttributes(filepath, FILE_ATTRIBUTE_NORMAL);
    }

    FILE *f = fopen(filepath, "r+b");
    if (!f) {
        fprintf(stderr, "  ERROR: Cannot open file '%s'. Skipping.\n", filepath);
        return 1;
    }

    fseek(f, 0, SEEK_END);
    long long file_size = _ftelli64(f);
    printf("  File size: %lld bytes.\n", file_size);

    if (file_size > 0) { // Only wipe files that have content
        if (strcmp(method, "--clear") == 0) {
            overwrite_pass(f, file_size, 1, 1, 0x00);
        } else if (strcmp(method, "--purge") == 0) {
            overwrite_pass(f, file_size, 1, 3, 0x00);
            overwrite_pass(f, file_size, 2, 3, 0xFF);
            overwrite_pass(f, file_size, 3, 3, 'R');
        } else if (strcmp(method, "--destroy-sw") == 0) {
            overwrite_pass(f, file_size, 1, 7, 0x00);
            overwrite_pass(f, file_size, 2, 7, 0xFF);
            overwrite_pass(f, file_size, 3, 7, 'R');
            overwrite_pass(f, file_size, 4, 7, 0x55);
            overwrite_pass(f, file_size, 5, 7, 0xAA);
            overwrite_pass(f, file_size, 6, 7, 'R');
            overwrite_pass(f, file_size, 7, 7, 'R');
        }
    }

    fclose(f);
    if (remove(filepath) == 0) {
        printf("  SUCCESS: File securely wiped and deleted.\n");
    } else {
        fprintf(stderr, "  ERROR: File overwritten but could not be deleted.\n");
        return 1;
    }
    return 0;
}

int main(int argc, char *argv[]) {
    if (argc != 4) {
        fprintf(stderr, "Usage: %s <--file|--folder> <\"path\"> <method>\n", argv[0]);
        return 1;
    }

    char *type = argv[1];
    char *path = argv[2];
    char *method = argv[3];
    srand((unsigned int)time(NULL));

    if (strcmp(type, "--file") == 0) {
        return wipe_file(path, method, 0);
    } else if (strcmp(type, "--folder") == 0) {
        printf("Zero Leaks Wiping Engine v0.5\n");
        printf("------------------------------------\n");
        printf("Target Folder: %s\n", path);
        printf("------------------------------------\n");
        return wipe_folder_recursive(path, method);
    } else {
        fprintf(stderr, "ERROR: Invalid type specified. Use --file or --folder.\n");
        return 1;
    }
    return 0;
}