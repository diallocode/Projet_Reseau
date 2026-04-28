#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include "cJSON.h"
#include "diffusion.h"
#include "connexion_multi.h"

// Sauvegarde du dernier handshake reçu de Python
char dernier_handshake[12288] = {0};

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

// Fonction pour envoyer demande_pairs à un pair
void envoyer_demande_pairs(int reseau_fd, struct sockaddr_in addr_pair) {
    char json_demande[] = "{\"type\":\"demande_pairs\"}";
    
    EnteteUDP env;
    memset(&env, 0, sizeof(env));
    env.taille_payload = htons(strlen(json_demande));
    env.type_message = 3;
    env.id_expediteur = 0;
    env.num_sequence = 0;

    int taille = strlen(json_demande) + sizeof(EnteteUDP);
    char *buf = malloc(taille);
    if (buf != NULL) {
        memcpy(buf, &env, sizeof(EnteteUDP));
        memcpy(buf + sizeof(EnteteUDP), json_demande, strlen(json_demande));
        sendto(reseau_fd, buf, taille, 0,
               (struct sockaddr*)&addr_pair, sizeof(addr_pair));
        free(buf);
        printf("[CONNECT] Demande de la liste des pairs envoyée à %s\n",
               inet_ntoa(addr_pair.sin_addr));
    }
}

int main(int argc, char *argv[]) {

    int mon_port         = (argc > 1) ? atoi(argv[1]) : 5002;
    int port_python_recv = (argc > 2) ? atoi(argv[2]) : 5001;
    int port_python_send = (argc > 3) ? atoi(argv[3]) : 5003;

    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        perror("Erreur création socket");
        exit(1);
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    addr.sin_port = htons(port_python_recv);

    if (bind(sock, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        perror("Erreur bind");
        exit(1);
    }

    printf("Processus C en écoute sur 127.0.0.1:%d\n", port_python_recv);
    
    char buffer[12288];
    struct sockaddr_in python_addr;
    socklen_t python_addr_len = sizeof(python_addr);

    // Socket de reception reseau 
    int reseau_fd = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in reseau_addr;
    memset(&reseau_addr, 0, sizeof(reseau_addr));
    reseau_addr.sin_family = AF_INET;
    reseau_addr.sin_addr.s_addr = INADDR_ANY;
    reseau_addr.sin_port = htons(mon_port); 
    bind(reseau_fd, (struct sockaddr*)&reseau_addr, sizeof(reseau_addr)); 

    // Socket d'envoi vers Python
    struct sockaddr_in python_send_addr;
    memset(&python_send_addr, 0, sizeof(python_send_addr));
    python_send_addr.sin_family = AF_INET;
    python_send_addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    python_send_addr.sin_port = htons(port_python_send);

    afficher_mes_ips();

    printf("Voulez-vous rejoindre une partie existante ? (o/n) : ");
    char reponse[4];
    fgets(reponse, sizeof(reponse), stdin);

    if (reponse[0] == 'o' || reponse[0] == 'O') {
        char ip_pair[64];
        printf("Entrez l'IP du pair : ");
        fgets(ip_pair, sizeof(ip_pair), stdin);
        ip_pair[strcspn(ip_pair, "\n")] = '\0';

        struct sockaddr_in addr_pair;
        memset(&addr_pair, 0, sizeof(addr_pair));
        addr_pair.sin_family = AF_INET;
        addr_pair.sin_addr.s_addr = inet_addr(ip_pair);
        addr_pair.sin_port = htons(5002);

        add_peer_if_new(addr_pair);
        printf("[INFO] Pair %s:5002 ajouté au carnet.\n", ip_pair);

        // NOUVEAU : demander la liste des pairs à A
        envoyer_demande_pairs(reseau_fd, addr_pair);

    } else {
        printf("[INFO] Vous êtes le joueur 1.\n");
    }

    printf("Processus C prêt !\n");

    long dernier_ping_envoye = get_time();

    while(1){
        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(sock, &fds);
        FD_SET(reseau_fd, &fds);

        int max_fd = (sock > reseau_fd ? sock : reseau_fd) + 1;

        struct timeval timeout;
        timeout.tv_sec = 1;
        timeout.tv_usec = 0;

        int ret = select(max_fd, &fds, NULL, NULL, &timeout);
        if (ret < 0) {
            perror("Erreur select");
            break;
        }

        // Python -> Reseau
        if (FD_ISSET(sock, &fds)) {
            int n = recvfrom(sock, buffer, sizeof(buffer) - 1, 0,
                            (struct sockaddr*)&python_addr, &python_addr_len);
            if (n > 0) {
                buffer[n] = '\0';
                printf("[PYTHON] Reçu : %s\n", buffer);

                cJSON *json = cJSON_Parse(buffer);
                if (json != NULL) {
                    cJSON *type_item = cJSON_GetObjectItemCaseSensitive(json, "type");
                  
                    if (cJSON_IsString(type_item) && strcmp(type_item->valuestring, "connected") == 0) {
                        // Python nous donne son ID
                        cJSON *id_item = cJSON_GetObjectItemCaseSensitive(json, "player_id");
                        if (cJSON_IsNumber(id_item)) {
                            set_mon_id((uint32_t)id_item->valueint);
                            printf("[SYSTÈME] Mon ID configuré : %d\n", id_item->valueint);
                        }
                    } else {
                        // Sauvegarder le handshake pour pouvoir le renvoyer aux nouveaux pairs
                        if (cJSON_IsString(type_item) && strcmp(type_item->valuestring, "handshake") == 0) {
                            strncpy(dernier_handshake, buffer, sizeof(dernier_handshake) - 1);
                            printf("[SAUVEGARDE] Handshake local sauvegardé.\n");
                        }
                        // Diffusion normale sur le réseau
                        uint32_t type_message = obtenir_type_message(buffer);
                        diffusion_message_sens1(buffer, reseau_fd, type_message);
                        printf("[SYSTEME] Message Python diffusé sur le réseau.\n");
                    }
                    cJSON_Delete(json);
                }
            }
        }

        // Reseau -> Python
        if (FD_ISSET(reseau_fd, &fds)) {
            char *json_propre = diffusion_message_sens2(reseau_fd);
           
            if (json_propre != NULL) {
                // Vérifier le type avant de transmettre à Python
                cJSON *msg = cJSON_Parse(json_propre);
                if (msg != NULL) {
                    cJSON *type_item = cJSON_GetObjectItem(msg, "type");

                    if (type_item != NULL &&
                        strcmp(type_item->valuestring, "liste_pairs") == 0) {
                        // C reçoit la liste des pairs de A → les ajouter au carnet
                        cJSON *pairs_array = cJSON_GetObjectItem(msg, "pairs");
                        if (pairs_array != NULL) {
                            int nb = cJSON_GetArraySize(pairs_array);
                            for (int i = 0; i < nb; i++) {
                                cJSON *pair = cJSON_GetArrayItem(pairs_array, i);
                                cJSON *ip = cJSON_GetObjectItem(pair, "ip");
                                if (ip != NULL) {
                                    struct sockaddr_in nouveau;
                                    memset(&nouveau, 0, sizeof(nouveau));
                                    nouveau.sin_family = AF_INET;
                                    nouveau.sin_addr.s_addr = inet_addr(ip->valuestring);
                                    nouveau.sin_port = htons(5002);
                                    add_peer_if_new(nouveau);
                                    printf("[LISTE] Pair ajouté depuis liste : %s\n",
                                           ip->valuestring);
                                }
                            }
                        }
                        // Ne pas transmettre ce message à Python
                        cJSON_Delete(msg);
                        free(json_propre);
                        json_propre = NULL;

                    } else if (type_item != NULL &&
                               strcmp(type_item->valuestring, "nouveau_pair") == 0) {
                        // B reçoit l'arrivée de C → ajouter C au carnet
                        cJSON *ip_item = cJSON_GetObjectItem(msg, "ip");
                        if (ip_item != NULL) {
                            struct sockaddr_in nouveau;
                            memset(&nouveau, 0, sizeof(nouveau));
                            nouveau.sin_family = AF_INET;
                            nouveau.sin_addr.s_addr = inet_addr(ip_item->valuestring);
                            nouveau.sin_port = htons(5002);
                            add_peer_if_new(nouveau);
                            printf("[RELAY] Nouveau pair ajouté : %s\n",
                                   ip_item->valuestring);

                            // Envoyer notre handshake au nouveau pair
                            if (strlen(dernier_handshake) > 0) {
                                diffusion_message_sens1(dernier_handshake, reseau_fd, 5);
                                printf("[RELAY] Notre handshake envoyé au nouveau pair.\n");
                            }
                        }
                        // Ne pas transmettre ce message à Python
                        cJSON_Delete(msg);
                        free(json_propre);
                        json_propre = NULL;

                    } else {
                        // Message normal → transmettre à Python
                        int ret = sendto(sock, json_propre, strlen(json_propre), 0,
                                        (struct sockaddr*)&python_send_addr,
                                        sizeof(python_send_addr));
                        if (ret < 0) {
                            perror("Erreur envoi vers Python");
                        } else {
                            printf("Message Recu : %s\n", json_propre);
                            printf("[RÉSEAU→PYTHON] JSON transmis au jeu !\n");
                        }
                        cJSON_Delete(msg);
                        free(json_propre);
                        json_propre = NULL;
                    }
                } else {
                    free(json_propre);
                    json_propre = NULL;
                }
            }
        }

        verifier_retransmissions(reseau_fd);

        // ENVOI DU HEARTBEAT (PING)
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

        // Gestion des déconnexions 
        struct sockaddr_in addr_fantome;
        int id_deconnecte = check_and_get_inactive_paire(60, &addr_fantome);
        if (id_deconnecte != -1) {
            printf("[ALERTE] Le joueur ID %d déconnecté pour inactivité.\n", id_deconnecte);
            disconnect_paire_by_addr(addr_fantome);
            nettoyer_file_joueur_parti(addr_fantome);
            if (id_deconnecte > 0) {
                char json_deco[128];
                sprintf(json_deco, "{\"type\": \"disconnect\", \"player_id\": %d}", id_deconnecte);
                sendto(sock, json_deco, strlen(json_deco), 0,
                       (struct sockaddr*)&python_send_addr, sizeof(python_send_addr));
                printf("[DÉCO] Envoyé à Python : %s\n", json_deco);
            } else {
                printf("[INFO] Pair jamais identifié, pas de notification Python.\n");
            }
        }
    }

    return 0;   
}