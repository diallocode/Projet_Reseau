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
//#include <cjson/cJSON.h>

// Fonction utilitaire pour traduire le type texte en type réseau
uint8_t obtenir_type_message(const char *donnee_json) {
    uint8_t type_numerique = 0; // 0 par défaut 
    cJSON *json = cJSON_Parse(donnee_json);
    if (json != NULL) {
        cJSON *type_item = cJSON_GetObjectItemCaseSensitive(json, "type");
        
        if (cJSON_IsString(type_item)) {
            if (strcmp(type_item->valuestring, "handshake") == 0) {
                type_numerique = 0; // Type 0 pour l'initialisation
            } 
            else if (strcmp(type_item->valuestring, "update") == 0) {
                type_numerique = 0; // Type 0 pour les mouvements
            }else if (strcmp(type_item->valuestring, "acknowledgment") == 0) {
                type_numerique = 0; // Type 0 pour les damage
            }
            //else if (strcmp(type_item->valuestring, "shoot") == 0) {
                type_numerique = 0; // Type 0 pour les tirs
            //else if (strcmp(type_item->valuestring, "connected") == 0) {
                //type_numerique = 3;
            //}
            //  ajouter d'autres types ici plus tard
        }
        
        // on libère la mémoire avant de quitter !
        cJSON_Delete(json); 
    }
    
    return type_numerique;
}



int main() {
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        perror("Erreur création socket");
        exit(1);
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    addr.sin_port = htons(5001);

    if (bind(sock, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        perror("Erreur bind");
        exit(1);
    }

    printf("Processus C en écoute sur 127.0.0.1:5001\n");
    
    char buffer[4096];
    struct sockaddr_in python_addr;
    socklen_t python_addr_len = sizeof(python_addr);

    // Socket de reception reseau 
    int reseau_fd = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in reseau_addr;
    memset(&reseau_addr, 0, sizeof(reseau_addr));
    reseau_addr.sin_family = AF_INET;
    reseau_addr.sin_addr.s_addr = INADDR_ANY;
    reseau_addr.sin_port = htons(5002); 
    bind(reseau_fd, (struct sockaddr*)&reseau_addr, sizeof(reseau_addr)); 

    // Socket d'envoi
    struct sockaddr_in python_send_addr;
    memset(&python_send_addr, 0, sizeof(python_send_addr));
    python_send_addr.sin_family = AF_INET;
    python_send_addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    python_send_addr.sin_port = htons(5003);


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

        printf("[CONNECT] Lancement de la recherche d'ID...\n");
    } else {
        //set_mon_id(1);
        printf("[INFO] Vous êtes le joueur 1.\n");

        
    }

    printf("Processus C prêt !\n");

    long dernier_ping_envoye = get_time();

    while(1){
        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(sock, &fds);       // écoute local (pour le Python) 
        FD_SET(reseau_fd, &fds);  // écoute sur le Réseau 

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
            int n = recvfrom(sock, buffer, sizeof(buffer) - 1, 0, (struct sockaddr*)&python_addr, &python_addr_len);
            if (n > 0) {
                buffer[n] = '\0';
                printf("[PYTHON] Reçu : %s\n", buffer);

            

                // INTERCEPTION DE L'ID EN DUR
               cJSON *json = cJSON_Parse(buffer);
               if (json != NULL) {
                   cJSON *type_item = cJSON_GetObjectItemCaseSensitive(json, "type");
                  
                   // Si Python nous envoie son message de bienvenue ("init")
                   if (cJSON_IsString(type_item) && strcmp(type_item->valuestring, "connected") == 0) {
                       cJSON *id_item = cJSON_GetObjectItemCaseSensitive(json, "player_id");
                       if (cJSON_IsNumber(id_item)) {
                           set_mon_id((uint32_t)id_item->valueint);     // Mise a jour de l'id
                           printf("[SYSTÈME] Mon ID a été configuré en dur à : %d\n", id_item->valueint);
                       }
                   }
                   cJSON_Delete(json);
               }

               else {
                    uint8_t type_message = obtenir_type_message(buffer);
                    // Tous les autres messages → diffusion normale
                    diffusion_message_sens1(buffer, reseau_fd, type_message);
                    printf("[SYSTEME] Message Python diffusé sur le réseau.\n");

               }
              

                /*if (type_message == 3) {
                    // Python nous donne son ID → vérifier s'il est libre
                    cJSON *json = cJSON_Parse(buffer);
                    cJSON *id_item = cJSON_GetObjectItem(json, "player_id");

                    if (id_item != NULL) {
                        int id_propose = id_item->valueint;

                       // Vérifier si cet ID est déjà pris dans le carnet
                        int id_deja_pris = 0;
                        int nb_pairs = 0;
                        struct paire *pairs = get_connected_peers(&nb_pairs);

                        for (int i = 0; i < nb_pairs; i++) {
                            if (pairs[i].id == id_propose) {
                               id_deja_pris = 1;
                            break;
                            }
                        }

                    if (id_deja_pris) {
                        // ID pris → signaler à Python
                        char json_conflit[64];
                        sprintf(json_conflit, "{\"type\":\"id_conflit\",\"player_id\":%d}", id_propose);
                        sendto(sock, json_conflit, strlen(json_conflit), 0,
                           (struct sockaddr*)&python_send_addr, sizeof(python_send_addr));
                        printf("[CONFLIT] ID %d déjà pris ! Python doit choisir un autre.\n", id_propose);

                    } else {
                        // ID libre → accepter et diffuser aux autres
                        set_mon_id(id_propose);
                        printf("[CONNECT] ID %d accepté.\n", id_propose);
                        diffusion_message_sens1(buffer, reseau_fd, 3);
                        printf("[CONNECT] Annonce aux autres joueurs faite.\n");
                    }
                }
                cJSON_Delete(json);

            } else {
                // Tous les autres messages → diffusion normale
                diffusion_message_sens1(buffer, reseau_fd, type_message);
                printf("[SYSTEME] Message Python diffusé sur le réseau.\n");
            }*/
        }
    }

        

        // Reseau->Python
        if (FD_ISSET(reseau_fd, &fds)) {
            char *json_propre = diffusion_message_sens2(reseau_fd); // Reception de la chaine json
           
            if(json_propre != NULL){
                // Transmettre à Python sur le port 5003
                int ret = sendto(sock, json_propre, strlen(json_propre), 0, (struct sockaddr*)&python_send_addr, sizeof(python_send_addr));
                if (ret < 0) {
                    perror("Erreur envoi vers Python");
                    return -1;
                } else {
                    printf("[RÉSEAU→PYTHON] JSON transmis au jeu !\n");
                }
            } 

            free(json_propre);
        }

        verifier_retransmissions(reseau_fd);

        // ==========================================
        // ENVOI DU HEARTBEAT (PING)
        // ==========================================
        long temps_actuel = get_time();
        if (temps_actuel - dernier_ping_envoye > 3000) { // Toutes les 3 secondes (3000 ms)
            
            int nb_joueurs_ping = 0;
            struct paire *joueurs_a_ping = get_connected_peers(&nb_joueurs_ping);

            for (int i = 0; i < nb_joueurs_ping; i++) {
                // On envoie un message système de Type 2 (Ping) à chaque joueur
                // Le paramètre num_seq est à 0 car ce n'est pas un message vital à retransmettre
                message_systeme(reseau_fd, 2, 0, joueurs_a_ping[i].addr);
            }
            
            // Affichage de contrôle toutes les 3 secondes
            afficher_liste_joueurs();
            dernier_ping_envoye = temps_actuel; // On redémarre le chrono !
        }
        //Gestion des deconnexions 
        struct sockaddr_in addr_fantome;
        int id_deconnecte = check_and_get_inactive_paire(10, &addr_fantome);
        if (id_deconnecte != -1) {
            printf("[ALERTE] Le joueur ID %d déconnecté pour inactivité.\n", id_deconnecte);

            disconnect_paire_by_addr(addr_fantome);

            // Nettoyer la file d'attente 
            nettoyer_file_joueur_parti(addr_fantome);

            // Prévenir Python
            if (id_deconnecte > 0) { 
            char json_deco[128];
            sprintf(json_deco, "{\"type\": \"disconnect\", \"player_id\": %d}", id_deconnecte);
            sendto(sock, json_deco, strlen(json_deco), 0, (struct sockaddr*)&python_send_addr, sizeof(python_send_addr));
            printf("[DÉCO] Envoyé à Python : %s\n", json_deco);
        } else {
        printf("[INFO] Pair jamais identifié, pas de notification Python.\n");
        }
    }
}

    return 0;   
}
    


           