#include "socket_compat.h"
#include <stdio.h>

int network_init() {
#ifdef _WIN32
    WSADATA wsaData;
    int res = WSAStartup(MAKEWORD(2, 2), &wsaData);
    if (res != 0) {
        printf("Échec de l'initialisation de Winsock : %d\n", res);
        return -1;
    }
#endif
    return 0;
}

void network_cleanup() {
#ifdef _WIN32
    WSACleanup();
#endif
}