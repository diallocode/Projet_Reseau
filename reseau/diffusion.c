#include "diffusion.h"
#include "cJSON.h"
#include "connexion_multi.h"
#include "socket_compat.h"

#ifdef _WIN32
    #include <windows.h> 
#else
    #include <sys/time.h>
    #include <unistd.h>
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// File d'attente pour la fiabilité
NoeudAttente *file_attente = NULL;

static uint32_t mon_id_joueur = 0; 
static uint32_t compteur_sequence = 0;

// --- GESTION DU TEMPS PORTABLE ---
long get_time() {
#ifdef _WIN32
    return (long)GetTickCount(); 
#else
    struct timeval temps;
    gettimeofday(&temps, NULL);
    return (temps.tv_sec * 1000) + (temps.tv_usec / 1000);
#endif
}

// --- ENVOI PYTHON -> RÉSEAU ---
int diffusion_message_sens1(const char *donnee_json, SOCKET_T mon_socket_udp, uint8_t type_msg){
    // Récupération dynamique de l'ID si pas encore défini
    if (mon_id_joueur == 0) {
        cJSON *json_obj = cJSON_Parse(donnee_json);
        if (json_obj != NULL) {
            cJSON *pid_item = cJSON_GetObjectItemCaseSensitive(json_obj, "player_id");
            if (cJSON_IsNumber(pid_item)) {
                mon_id_joueur = pid_item->valueint;
                printf("[SYSTÈME] ID local mis à jour : %u\n", mon_id_joueur);
            }
            cJSON_Delete(json_obj);
        }
    }

    EnteteUDP enveloppe;        
    enveloppe.taille_payload = htons((uint16_t)strlen(donnee_json));
    enveloppe.type_message = type_msg;
    enveloppe.id_expediteur = htonl(mon_id_joueur);
    enveloppe.num_sequence = htonl(compteur_sequence++);

    int nb_joueurs = 0;
    struct paire *players = get_connected_peers(&nb_joueurs);

    // Extraction du destinataire (Unicast vs Broadcast)
    int cible_id = -1;
    cJSON *json_obj = cJSON_Parse(donnee_json);
    if (json_obj != NULL) {
        cJSON *dest_item = cJSON_GetObjectItemCaseSensitive(json_obj, "network_owner"); 
        if (cJSON_IsNumber(dest_item)) cible_id = dest_item->valueint; 
        cJSON_Delete(json_obj); 
    }

    int TAILLE_PAQUET = (int)strlen(donnee_json) + sizeof(EnteteUDP); 
    char *Buffer = malloc(TAILLE_PAQUET);
    if(!Buffer) return -1;

    memcpy(Buffer, &enveloppe, sizeof(EnteteUDP));
    memcpy(Buffer + sizeof(EnteteUDP), donnee_json, strlen(donnee_json));

    for (int i = 0; i < nb_joueurs; i++) {
        if(cible_id == -1 || players[i].id == (uint32_t)cible_id){
            sendto(mon_socket_udp, Buffer, TAILLE_PAQUET, 0, (struct sockaddr*)&players[i].addr, sizeof(struct sockaddr_in));

            // Ajouter à la file de retransmission (sauf handshake simple)
            if (type_msg != 5){
                NoeudAttente *nouveau = (NoeudAttente*)malloc(sizeof(NoeudAttente));
                if (nouveau) {
                    nouveau->entete = enveloppe;
                    strncpy(nouveau->payload, donnee_json, sizeof(nouveau->payload) - 1);
                    nouveau->payload[sizeof(nouveau->payload) - 1] = '\0';
                    nouveau->temps_envoi = get_time();
                    nouveau->dest = players[i].addr; 
                    nouveau->suivant = file_attente;
                    file_attente = nouveau;
                }
            }
            if(cible_id != -1) break;
        }
    }
    free(Buffer);
    return 0;
}

// --- MESSAGES SYSTÈME (ACK/PING) ---
void message_systeme(SOCKET_T mon_socket_udp, uint8_t type_msg, uint32_t num_seq, struct sockaddr_in dest) {
    EnteteUDP env;
    env.taille_payload = htons(0); 
    env.type_message = type_msg;
    env.id_expediteur = htonl(mon_id_joueur);
    env.num_sequence = htonl(num_seq);

    sendto(mon_socket_udp, (const char*)&env, sizeof(EnteteUDP), 0, (struct sockaddr*)&dest, sizeof(struct sockaddr));
}

// --- RÉCEPTION RÉSEAU -> PYTHON ---
char *diffusion_message_sens2(SOCKET_T reseau_fd){
    struct sockaddr_in addr_distant;
    socklen_t addr_len = sizeof(addr_distant);      
    char *Buffer = malloc(12288);
    if(!Buffer) return NULL;

    int n = recvfrom(reseau_fd, Buffer, 12288, 0, (struct sockaddr*)&addr_distant, &addr_len);
    if(n < (int)sizeof(EnteteUDP)){
        free(Buffer);
        return NULL;
    }

    EnteteUDP *env = (EnteteUDP *)Buffer;
    uint32_t id_exp = ntohl(env->id_expediteur);
    if (id_exp == mon_id_joueur) { free(Buffer); return NULL; } // Ignorer mes propres messages

    add_peer_if_new(addr_distant);
    actualiser_activite(addr_distant, id_exp);

    uint32_t seq = ntohl(env->num_sequence);
    uint16_t len_json = ntohs(env->taille_payload);

    switch (env->type_message) {
        case 1: // ACK
            supprimer_de_la_file(seq, addr_distant);
            free(Buffer);
            return NULL;
        case 2: // PING
            free(Buffer);
            return NULL;
        case 5:
        case 0: // GAME DATA
            message_systeme(reseau_fd, 1, seq, addr_distant); // Répondre ACK
            char *json = malloc(len_json + 1);
            memcpy(json, Buffer + sizeof(EnteteUDP), len_json);
            json[len_json] = '\0';
            free(Buffer);
            return json;
        default: // Autres types (relais...) : on renvoie le JSON brut pour traitement dans ipc.c
            if (len_json > 0) {
                char *json_sys = malloc(len_json + 1);
                memcpy(json_sys, Buffer + sizeof(EnteteUDP), len_json);
                json_sys[len_json] = '\0';
                free(Buffer);
                return json_sys;
            }
            free(Buffer);
            return NULL;
    }
}

// --- FIABILITÉ : RETRANSMISSION ---
void verifier_retransmissions(SOCKET_T mon_socket_udp) {
    long maintenant = get_time();
    long DELAI_RETRANSMISSION = 1000; // AUGMENTÉ À 1s POUR ÉVITER LA SATURATION HP
    
    NoeudAttente *actuel = file_attente;
    while (actuel != NULL) {
        if (maintenant - actuel->temps_envoi > DELAI_RETRANSMISSION) {
            int len_p = (int)strlen(actuel->payload);
            int total = (int)sizeof(EnteteUDP) + len_p;
            char *buf = malloc(total);
            if (buf) {
                memcpy(buf, &actuel->entete, sizeof(EnteteUDP));
                memcpy(buf + sizeof(EnteteUDP), actuel->payload, len_p);
                sendto(mon_socket_udp, buf, total, 0, (struct sockaddr*)&actuel->dest, sizeof(struct sockaddr));
                free(buf);
                printf("[RETRANSMISSION] Renvoi message %u\n", ntohl(actuel->entete.num_sequence));
            }
            actuel->temps_envoi = maintenant;
        }
        actuel = actuel->suivant;
    }
}

void supprimer_de_la_file(uint32_t seq, struct sockaddr_in exp) {
    NoeudAttente *actuel = file_attente, *prec = NULL;
    while (actuel) {
        if (ntohl(actuel->entete.num_sequence) == seq && 
            actuel->dest.sin_addr.s_addr == exp.sin_addr.s_addr) {
            if (!prec) file_attente = actuel->suivant;
            else prec->suivant = actuel->suivant;
            free(actuel);
            printf("[FIABILITÉ] Message %u confirmé.\n", seq);
            return;
        }
        prec = actuel; actuel = actuel->suivant;
    }
}

void nettoyer_file_joueur_parti(struct sockaddr_in jp) {
    NoeudAttente *actuel = file_attente, *prec = NULL;
    while (actuel) {
        if (actuel->dest.sin_addr.s_addr == jp.sin_addr.s_addr) {
            NoeudAttente *tmp = actuel;
            if (!prec) file_attente = actuel = actuel->suivant;
            else { prec->suivant = actuel->suivant; actuel = actuel->suivant; }
            free(tmp);
        } else { prec = actuel; actuel = actuel->suivant; }
    }
}

void set_mon_id(uint32_t id) { mon_id_joueur = id; }