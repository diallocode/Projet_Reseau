#include "socket_compat.h"  // Doit être en premier
#include "connexion_multi.h"
#include <stdio.h>
#include <string.h>


#ifndef _WIN32
    #include <ifaddrs.h> 
#endif

#define NB_JOUEUR_MAX 5

struct paire paire_connected[NB_JOUEUR_MAX];
int nb_joueur_connecte = 0;

void add_peer_if_new(struct sockaddr_in new_peer_addr) {
    printf("[DEBUG] Tentative ajout pair : %s:%d\n",
           inet_ntoa(new_peer_addr.sin_addr),
           ntohs(new_peer_addr.sin_port)); 

    for (int i = 0; i < nb_joueur_connecte; i++) {
        if (paire_connected[i].addr.sin_addr.s_addr == new_peer_addr.sin_addr.s_addr &&
            paire_connected[i].addr.sin_port == new_peer_addr.sin_port) {
            return; 
        }
    }
    if (nb_joueur_connecte < NB_JOUEUR_MAX) {
        paire_connected[nb_joueur_connecte].addr = new_peer_addr;
        paire_connected[nb_joueur_connecte].dernier_vu = time(NULL);
        paire_connected[nb_joueur_connecte].id = 0;
        nb_joueur_connecte++;
        printf("[CARNET] Nouveau pair ajouté ! Total : %d\n", nb_joueur_connecte);
    }
}

struct paire* get_connected_peers(int *count) {
    *count = nb_joueur_connecte;
    return paire_connected;
}

void afficher_mes_ips() {
    printf("--- MES ADRESSES IP POUR JOUER ---\n");
#ifndef _WIN32
    struct ifaddrs *ifaddrp, *ifad;
    if (getifaddrs(&ifaddrp) == -1) return;
    for(ifad = ifaddrp; ifad != NULL; ifad = ifad->ifa_next){
        if(ifad->ifa_addr && ifad->ifa_addr->sa_family == AF_INET){
            char *addr = inet_ntoa(((struct sockaddr_in *)ifad->ifa_addr)->sin_addr);
            if(strcmp(addr,"127.0.0.1") != 0){      
                printf("-> %s\n", addr);
            }
        }
    }
    freeifaddrs(ifaddrp);
#else
    char szHostName[255];
    if (gethostname(szHostName, 255) == 0) {
        struct hostent *host_entry = gethostbyname(szHostName);
        if (host_entry != NULL) {
            int i = 0;
            while (host_entry->h_addr_list[i] != NULL) {
                struct in_addr addr;
                memcpy(&addr, host_entry->h_addr_list[i], sizeof(struct in_addr));
                char *ip = inet_ntoa(addr);
                if (strcmp(ip, "127.0.0.1") != 0) {
                    printf("-> %s\n", ip);
                }
                i++;
            }
        }
    }
#endif
    printf("----------------------------------\n");
}

int  close_socket(SOCKET_T sockfd) {
     return CLOSE_SOCKET(sockfd);
}

int check_and_get_inactive_paire(int timeout_sec, struct sockaddr_in *addr_out) {
    time_t now = time(NULL);
    for (int i = 0; i < nb_joueur_connecte; i++) {
        if (difftime(now, paire_connected[i].dernier_vu) > (double)timeout_sec) {
            if (addr_out != NULL) {
                *addr_out = paire_connected[i].addr;
            }
            return paire_connected[i].id;
        }
    }
    return -1;
}

void disconnect_paire_by_addr(struct sockaddr_in addr) {
    for (int i = 0; i < nb_joueur_connecte; i++) {
        if (paire_connected[i].addr.sin_addr.s_addr == addr.sin_addr.s_addr &&
            paire_connected[i].addr.sin_port == addr.sin_port) {
            remove_peer(i);
            printf("[INFO] Déconnexion volontaire réussie.\n");
            return;
        }
    }
}

int remove_peer(int index) {
    if (index < 0 || index >= nb_joueur_connecte) return -1;
    int id_supprime = paire_connected[index].id;
    for (int i = index; i < nb_joueur_connecte - 1; i++) {
        paire_connected[i] = paire_connected[i + 1];
    }
    nb_joueur_connecte--;
    return id_supprime;
}

void actualiser_activite(struct sockaddr_in addr, uint32_t vrai_id_joueur) {
    for (int i = 0; i < nb_joueur_connecte; i++) {
        if (paire_connected[i].addr.sin_addr.s_addr == addr.sin_addr.s_addr &&
            paire_connected[i].addr.sin_port == addr.sin_port) {
            paire_connected[i].dernier_vu = time(NULL);
            paire_connected[i].id = vrai_id_joueur;
            return;
        }
    }
}

void afficher_liste_joueurs() {
    int nb_joueurs = 0;
    struct paire *joueurs = get_connected_peers(&nb_joueurs);
    printf("\n=== LISTE DES JOUEURS CONNECTÉS (%d) ===\n", nb_joueurs);
    if (nb_joueurs == 0) {
        printf(" -> Aucun joueur distant.\n");
    } else {
        long temps_actuel = (long)time(NULL);
        for (int i = 0; i < nb_joueurs; i++) {
            printf(" [%d] Joueur ID : %u | IP : %s | Port : %d | Inactif depuis : %lds\n", 
                   i, joueurs[i].id, inet_ntoa(joueurs[i].addr.sin_addr), 
                   ntohs(joueurs[i].addr.sin_port), temps_actuel - (long)joueurs[i].dernier_vu);
        }
    }
    printf("==========================================\n\n");
}
SOCKET_T initialiser_ma_connexion() {
    SOCKET_T sock;
    struct sockaddr_in mon_addr;

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == INVALID_SOCKET_T) return INVALID_SOCKET_T;

    memset(&mon_addr, 0, sizeof(mon_addr));
    mon_addr.sin_family = AF_INET;
    mon_addr.sin_addr.s_addr = INADDR_ANY; 
    mon_addr.sin_port = htons(0); // L'OS choisit un port libre

    if (bind(sock, (struct sockaddr *)&mon_addr, sizeof(mon_addr)) < 0) {
        CLOSE_SOCKET(sock);
        return INVALID_SOCKET_T;
    }

    // Récupération du port choisi par l'OS
    struct sockaddr_in adr_reelle;
    socklen_t len = sizeof(adr_reelle);
    getsockname(sock, (struct sockaddr *)&adr_reelle, &len);
    // ... après le getsockname ...
    printf("\n==========================================");
    printf("\n[PORT RÉSEAU] : %d", ntohs(adr_reelle.sin_port));
    printf("\n[INFO] Donne ce port à ton ami pour qu'il te rejoigne.");
    printf("\n==========================================\n");
    fflush(stdout);

    printf("\n[INFO] Ton port de jeu dynamique est : %d\n", ntohs(adr_reelle.sin_port));
    return sock;
}