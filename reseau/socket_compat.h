#ifndef SOCKET_COMPAT_H
#define SOCKET_COMPAT_H

#include <stdint.h>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #include <windows.h>
    typedef int socklen_t;
    typedef SOCKET SOCKET_T;
    #define INVALID_SOCKET_T INVALID_SOCKET
    #define CLOSE_SOCKET(s) closesocket(s)
#else
    #include <sys/socket.h>
    #include <sys/select.h>
    #include <netinet/in.h>
    #include <arpa/inet.h>
    #include <unistd.h>
    #include <netdb.h>
    typedef int SOCKET_T;
    #define INVALID_SOCKET_T -1
    #define CLOSE_SOCKET(s) close(s)
#endif

// On déclare juste les fonctions ici (le code est dans socket_compat.c)
int network_init();
void network_cleanup();

#endif