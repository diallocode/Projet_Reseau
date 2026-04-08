#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include "cJSON.h"
//#include <cjson/cJSON.h>




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


    while(1){
        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(sock, &fds);       // écoute local (pour le Python) 
        FD_SET(reseau_fd, &fds);  // écoute sur le Réseau 

        int max_fd = (sock > reseau_fd ? sock : reseau_fd) + 1;

        int ret = select(max_fd, &fds, NULL, NULL, NULL);
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
                //Parser le json reçu et traiter 

                cJSON *msg = cJSON_Parse(buffer);
                if (msg == NULL) {
                    printf("JSON malformé, on ignore\n");//juste pour tester
                    continue;
                    // ne pas crasher, juste ignorer
                }
    
                char *type = cJSON_GetObjectItem(msg, "type")->valuestring;
                if (strcmp(type, "move") == 0) {
                    printf("ACTION : diffuser un mouvement\n"); //en attendant la fonction qui envoie à tous 
                } else if (strcmp(type, "damage") == 0) {
                    printf("ACTION : diffuser des dégâts\n");
                }else if (strcmp(type, "init") == 0) {
                    int player_id = cJSON_GetObjectItem(msg, "player_id")->valueint;
                    printf("ACTION : nouveau joueur %d\n", player_id);

                }else if (strcmp(type, "handshake") == 0) {
                    printf("ACTION : diffuser le snapshot initial\n");

                } else if (strcmp(type, "player_disconnected") == 0) {
                    int player_id = cJSON_GetObjectItem(msg, "player_id")->valueint;
                    printf("ACTION : joueur %d déconnecté\n", player_id);

                } else {
                    printf("Type inconnu : %s\n", type);}

                cJSON_Delete(msg); //liberer la memoire
    
            }
        }

        // Reseau->Python
        if (FD_ISSET(reseau_fd, &fds)) {
            char *json_propre = diffusion_message_sens2(reseau_fd);
            if(json_propre != NULL){
                // Transmettre à Python sur le port 5003
                int ret = sendto(sock, buffer, strlen(json_propre), 0, (struct sockaddr*)&python_send_addr, sizeof(python_send_addr));
                if (ret < 0) {
                    perror("Erreur envoi vers Python");
                } else {
                    printf("[RÉSEAU→PYTHON] Transmis !\n");
                }
            } 
        }


        }

    return 0;
}
    


           