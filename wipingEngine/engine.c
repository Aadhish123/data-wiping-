#include <windows.h>
#include <stdio.h>
#include<string.h>
#include<ctype.h>

void listFilesAndFolders(char *directory) {
    WIN32_FIND_DATA findFileData;
    HANDLE hFind;

    char searchPath[MAX_PATH];
    snprintf(searchPath, MAX_PATH, "%s\\*", directory);

    hFind = FindFirstFile(searchPath, &findFileData);

    if (hFind == INVALID_HANDLE_VALUE) {
        printf("No files found in %s\n", directory);
        return;
    }

    do {
        // Skip "." and ".." entries
        if (strcmp(findFileData.cFileName, ".") != 0 && strcmp(findFileData.cFileName, "..") != 0) {
            if (findFileData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
                printf("[DIR]  %s\n", findFileData.cFileName);
                char subDir[MAX_PATH];
                snprintf(subDir, MAX_PATH,"%s\\%s",directory,findFileData.cFileName);
                listFilesAndFolders(subDir);
               
            } else {
                printf("[FILE] %s\n", findFileData.cFileName);
            }
        }
    } while (FindNextFile(hFind, &findFileData) != 0);

    FindClose(hFind);
}

int main() {
    char *dir;  // Change to desired directory
    printf("Enter the partition of Disk:");
    scanf("%s",dir);
    printf("Listing files and folders in %s:\n", dir);
   //toupper(dir);
    strcat(dir,":\\");
    listFilesAndFolders(dir);
    return 0;
}
