// Correct C Code for wipeEngine.c

#include <windows.h>
#include <stdio.h>
#include <wchar.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <process.h>
#include <winioctl.h>
#include <io.h>
#include <fcntl.h>

#define BUFFER_SIZE 1048576

// Helper to write to the log file
void write_log(FILE* log_file, const wchar_t* format, ...) {
    if (log_file) {
        va_list args;
        va_start(args, format);
        vfwprintf(log_file, format, args);
        va_end(args);
        fflush(log_file);
    }
}

void file_overwrite_pass(FILE* f, long long file_size, int pass_num, int total_passes, char pattern, FILE* log_file) {
    rewind(f);
    char *buffer = (char*)malloc(BUFFER_SIZE);
    if (!buffer) {
        write_log(log_file, L"  ERROR: Failed to allocate memory for wipe buffer.\n");
        return;
    }
    long long total_written = 0;
    wchar_t pass_desc[50];

    if (pattern == 0x00) { memset(buffer, 0x00, BUFFER_SIZE); swprintf(pass_desc, 50, L"Writing zeros (0x00)..."); }
    else if (pattern == 0xFF) { memset(buffer, 0xFF, BUFFER_SIZE); swprintf(pass_desc, 50, L"Writing ones (0xFF)..."); }
    else { swprintf(pass_desc, 50, L"Writing random data..."); }

    write_log(log_file, L"  Pass %d of %d: %s\n", pass_num, total_passes, pass_desc);

    if (pattern != 0x00 && pattern != 0xFF) {
        for (size_t i = 0; i < BUFFER_SIZE; i++) buffer[i] = rand() % 256;
    }

    while (total_written < file_size) {
        size_t to_write = BUFFER_SIZE;
        if (file_size - total_written < BUFFER_SIZE) to_write = (size_t)(file_size - total_written);
        fwrite(buffer, 1, to_write, f);
        total_written += to_write;
    }
    fflush(f);
    free(buffer);
}

int wipe_file(const wchar_t *filepath, const wchar_t *method, FILE* log_file) {
    write_log(log_file, L"Zero Leaks Wiping Engine v2.0 (File Log)\n------------------------------------\nTarget: %s\n------------------------------------\n", filepath);

    FILE *f = _wfopen(filepath, L"r+b");
    if (!f) {
        write_log(log_file, L"  ERROR: Cannot open file '%s'. Skipping.\n", filepath);
        return 1;
    }

    _fseeki64(f, 0, SEEK_END);
    long long file_size = _ftelli64(f);
    write_log(log_file, L"  File size: %lld bytes.\n", file_size);

    if (file_size > 0) {
        if (wcscmp(method, L"--clear") == 0) {
            file_overwrite_pass(f, file_size, 1, 1, 0x00, log_file);
        } else if (wcscmp(method, L"--purge") == 0) {
            file_overwrite_pass(f, file_size, 1, 3, 0x00, log_file);
            file_overwrite_pass(f, file_size, 2, 3, 0xFF, log_file);
            file_overwrite_pass(f, file_size, 3, 3, 'R', log_file);
        }
    }

    fclose(f);
    if (_wremove(filepath) == 0) {
        write_log(log_file, L"  SUCCESS: File securely wiped and deleted.\n");
    } else {
        write_log(log_file, L"  ERROR: File overwritten but could not be deleted.\n");
        return 1;
    }
    return 0;
}

int wmain(int argc, wchar_t *argv[]) {
    if (argc != 5) {
        return 1;
    }

    wchar_t *log_path = argv[1];
    wchar_t *type = argv[2];
    wchar_t *path = argv[3];
    wchar_t *method = argv[4];

    FILE* log_file = _wfopen(log_path, L"w, ccs=UTF-16LE");
    if (!log_file) {
        return 1;
    }
    
    srand((unsigned int)time(NULL));
    int result = 1;

    // This simplified version only handles the --file type for now
    if (wcscmp(type, L"--file") == 0) {
        result = wipe_file(path, method, log_file);
    } else {
        write_log(log_file, L"ERROR: This version only supports --file wiping.\n");
        result = 1;
    }
    
    fclose(log_file);
    return result;
}