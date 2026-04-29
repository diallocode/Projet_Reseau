#ifndef SOCKET_COMPAT_H
#define SOCKET_COMPAT_H

// 1. Détection de l'OS
#ifdef _WIN32
    /* Configuration spécifique à Windows */
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #include <time.h>
    // On définit les types qui manquent sous Windows
    typedef int socklen_t;
    #define CLOSE_SOCKET(s) closesocket(s)
    #define SOCKET_T SOCKET
    #define INVALID_SOCKET_T INVALID_SOCKET
#else
    /* Configuration pour Debian (Unix) */
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <arpa/inet.h>
    #include <unistd.h>
    #include <errno.h>
    #include <netdb.h>
    // Sous Unix, un socket est juste un entier (int)
    typedef int SOCKET_T;
    #define INVALID_SOCKET_T -1
    #define CLOSE_SOCKET(s) close(s)
#endif

// 2. Fonction d'initialisation universelle
// À appeler une seule fois au début du main()
static inline int network_init() {
#ifdef _WIN32
    WSADATA wsaData;
    // Initialise la bibliothèque Winsock 2.2
    return WSAStartup(MAKEWORD(2, 2), &wsaData);
#else
    return 0; // Rien à faire sur Debian
#endif
}

// 3. Fonction de nettoyage universelle
static inline void network_cleanup() {
#ifdef _WIN32
    WSACleanup();
#endif
}

#endif