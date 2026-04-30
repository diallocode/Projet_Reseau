#include "socket_compat.h"
#include <stdio.h>

int network_init() {
#ifdef _WIN32
    WSADATA wsaData;
    return WSAStartup(MAKEWORD(2, 2), &wsaData);
#endif
    return 0;
}

void network_cleanup() {
#ifdef _WIN32
    WSACleanup();
#endif
}