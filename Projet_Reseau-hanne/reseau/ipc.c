#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "socket_compat.h"

#ifndef _WIN32
    #include <sys/socket.h>
    #include <sys/select.h>
    #include <arpa/inet.h>
    #include <unistd.h>
#endif

#include "cJSON.h"
#include "diffusion.h"
#include "connexion_multi.h"

// Fonction utilitaire pour traduire le type texte en type réseau
uint32_t obtenir_type_message(const char *donnee_json) {
    uint32_t type_numerique = 0; 
    cJSON *json = cJSON_Parse(donnee_json);
    if (json != NULL) {
        cJSON *type_item = cJSON_GetObjectItemCaseSensitive(json, "type");
        if (cJSON_IsString(type_item)) {
            if (strcmp(type_item->valuestring, "handshake") == 0) {
                type_numerique = 5; 
            } 
            else if (strcmp(type_item->valuestring, "update") == 0) {
                type_numerique = 0; 
            } else if (strcmp(type_item->valuestring, "acknowledgment") == 0) {
                type_numerique = 0; 
            }
        }
        cJSON_Delete(json); 
    }
    return type_numerique;
}

int main(int argc, char *argv[]) {
    // --- INITIALISATION MULTIPLATEFORME ---
    if (network_init() != 0) {
        fprintf(stderr, "Erreur : Impossible d'initialiser la pile réseau.\n");
        return 1;
    }

    int port_python_recv = (argc > 2) ? atoi(argv[2]) : 55001;
    int port_python_send = (argc > 3) ? atoi(argv[3]) : 55003;

    // --- SOCKET LOCAL (COMMUNICATION AVEC PYTHON) ---
    SOCKET_T sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == INVALID_SOCKET_T) {
        perror("Erreur création socket local");
        network_cleanup();
        exit(1);
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    addr.sin_port = htons(port_python_recv);

    if (bind(sock, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        #ifdef _WIN32
            printf("Erreur bind local : %d\n", WSAGetLastError());
        #else
    perror("Erreur bind local"); // La version Linux standard
        #endif
    }

    printf("Processus C en écoute pour Python sur 127.0.0.1:%d\n", port_python_recv);
    // --- SOCKET RÉSEAU (COMMUNICATION AVEC LES AUTRES JOUEURS) ---
    // On utilise ta nouvelle fonction qui gère le port dynamique (Port 0)
    SOCKET_T reseau_fd = initialiser_ma_connexion(); 
    if (reseau_fd == INVALID_SOCKET_T) {
        network_cleanup();
        exit(1); 
    }

    // --- ADRESSE D'ENVOI VERS PYTHON ---
    struct sockaddr_in python_send_addr;
    memset(&python_send_addr, 0, sizeof(python_send_addr));
    python_send_addr.sin_family = AF_INET;
    python_send_addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    python_send_addr.sin_port = htons(port_python_send);

    afficher_mes_ips();

    // --- REJOINDRE UNE PARTIE ---
    printf("Voulez-vous rejoindre une partie existante ? (o/n) : ");
    char reponse[4];
    fgets(reponse, sizeof(reponse), stdin);

    if (reponse[0] == 'o' || reponse[0] == 'O') {
        char ip_pair[64];
        int port_pair;
        printf("Entrez l'IP du pair : ");
        fgets(ip_pair, sizeof(ip_pair), stdin);
        ip_pair[strcspn(ip_pair, "\n")] = '\0';

        printf("Entrez le PORT du pair (affiché sur son écran) : ");
        scanf("%d", &port_pair);
        getchar(); // Consomme le retour à la ligne

        struct sockaddr_in addr_pair;
        memset(&addr_pair, 0, sizeof(addr_pair));
        addr_pair.sin_family = AF_INET;
        addr_pair.sin_addr.s_addr = inet_addr(ip_pair);
        addr_pair.sin_port = htons(port_pair);

        add_peer_if_new(addr_pair);
        printf("[INFO] Pair %s:%d ajouté au carnet.\n", ip_pair, port_pair);
    } else {
        printf("[INFO] Vous êtes le joueur 1.\n");
    }

    printf("Processus C prêt !\n");
    char buffer[4096];
    struct sockaddr_in python_addr;
    socklen_t python_addr_len = sizeof(python_addr);
    long dernier_ping_envoye = get_time();

    while(1){
        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(sock, &fds);       
        FD_SET(reseau_fd, &fds);  

        int max_fd = (sock > reseau_fd ? sock : reseau_fd) + 1;
        struct timeval timeout = {1, 0};

        int ret = select(max_fd, &fds, NULL, NULL, &timeout);
        if (ret < 0) {
            perror("Erreur select");
            break;
        }

        // --- DE PYTHON VERS LE RÉSEAU ---
        if (FD_ISSET(sock, &fds)) {
            int n = recvfrom(sock, buffer, sizeof(buffer) - 1, 0, (struct sockaddr*)&python_addr, &python_addr_len);
            if (n > 0) {
                buffer[n] = '\0';
                cJSON *json = cJSON_Parse(buffer);
                if (json != NULL) {
                    cJSON *type_item = cJSON_GetObjectItemCaseSensitive(json, "type");
                    if (cJSON_IsString(type_item) && strcmp(type_item->valuestring, "connected") == 0) {
                        cJSON *id_item = cJSON_GetObjectItemCaseSensitive(json, "player_id");
                        if (cJSON_IsNumber(id_item)) {
                            set_mon_id((uint32_t)id_item->valueint);
                            printf("[SYSTÈME] Mon ID configuré à : %d\n", id_item->valueint);
                        }
                    } else {
                        uint32_t type_message = obtenir_type_message(buffer);
                        diffusion_message_sens1(buffer, reseau_fd, type_message);
                    }
                    cJSON_Delete(json);
                }
            }
        }

        // --- DU RÉSEAU VERS PYTHON ---
        if (FD_ISSET(reseau_fd, &fds)) {
            char *json_propre = diffusion_message_sens2(reseau_fd);
            if(json_propre != NULL){
                sendto(sock, json_propre, strlen(json_propre), 0, (struct sockaddr*)&python_send_addr, sizeof(python_send_addr));
                printf("[RÉSEAU→PYTHON] Message transmis au jeu.\n");
                free(json_propre);
            } 
        }

        verifier_retransmissions(reseau_fd);

        // --- GESTION HEARTBEAT ET DÉCONNEXION ---
        long temps_actuel = get_time();
        if (temps_actuel - dernier_ping_envoye > 3000) {
            int nb_joueurs_ping = 0;
            struct paire *joueurs_a_ping = get_connected_peers(&nb_joueurs_ping);
            for (int i = 0; i < nb_joueurs_ping; i++) {
                message_systeme(reseau_fd, 2, 0, joueurs_a_ping[i].addr);
            }
            afficher_liste_joueurs();
            dernier_ping_envoye = temps_actuel;
        }

        struct sockaddr_in addr_fantome;
        int id_deconnecte = check_and_get_inactive_paire(10, &addr_fantome);
        if (id_deconnecte != -1) {
            disconnect_paire_by_addr(addr_fantome);
            nettoyer_file_joueur_parti(addr_fantome);
            if (id_deconnecte > 0) { 
                char json_deco[128];
                sprintf(json_deco, "{\"type\": \"disconnect\", \"player_id\": %d}", id_deconnecte);
                sendto(sock, json_deco, strlen(json_deco), 0, (struct sockaddr*)&python_send_addr, sizeof(python_send_addr));
            }
        }
    }

    network_cleanup();
    return 0;   
}