#include "diffusion.h"
#include "cJSON.h"
#include "connexion_multi.h"

// Le point de départ de la file d'attente
NoeudAttente *file_attente = NULL;

static uint8_t mon_id_joueur = 0;
static uint32_t compteur_sequence = 0;

// Python->Reseau
int diffusion_message_sens1(const char *donnee_json, int mon_socket_udp, uint8_t type_msg){

    EnteteUDP enveloppe;        
    enveloppe.taille_payload = htons((uint16_t)strlen(donnee_json));
    enveloppe.type_message = type_msg;
    enveloppe.id_expediteur = mon_id_joueur;
    enveloppe.num_sequence = htonl(compteur_sequence);
    compteur_sequence++;

    int nombre_de_joueurs = 0;
    struct paire *players = get_connected_peers(&nombre_de_joueurs);

    int TAILLE_PAQUET = strlen(donnee_json) + sizeof(EnteteUDP); 
    char *Buffer = malloc(TAILLE_PAQUET);
    if(Buffer == NULL){
        printf("erreur d'allocation du buffer");
        return -1;
    }

    memcpy(Buffer, &enveloppe, sizeof(EnteteUDP));
    memcpy(Buffer + sizeof(EnteteUDP), donnee_json, strlen(donnee_json));

    for (int i = 0; i < nombre_de_joueurs; i++) {
        struct sockaddr_in dest_addr = players[i].addr;

        if(sendto(mon_socket_udp, Buffer, TAILLE_PAQUET, 0,
                  (struct sockaddr*)&dest_addr, sizeof(struct sockaddr_in)) < 0){
            printf("erreur-sendto");
        }

        if (type_msg != 5){
            NoeudAttente *nouveau_colis = (NoeudAttente*)malloc(sizeof(NoeudAttente));
            if (nouveau_colis != NULL) {
                nouveau_colis->entete = enveloppe;
                strncpy(nouveau_colis->payload, donnee_json, sizeof(nouveau_colis->payload) - 1);
                nouveau_colis->payload[sizeof(nouveau_colis->payload) - 1] = '\0';
                nouveau_colis->temps_envoi = get_time();
                nouveau_colis->dest = dest_addr; 
                nouveau_colis->suivant = file_attente;
                file_attente = nouveau_colis;
            }
        }
    }

    free(Buffer);
    return 0;
}

// ACK et PING
void message_systeme(int mon_socket_udp, uint8_t type_msg, uint32_t num_seq, struct sockaddr_in dest) {
    EnteteUDP enveloppe;
    enveloppe.taille_payload = htons(0); 
    enveloppe.type_message = type_msg;
    enveloppe.id_expediteur = mon_id_joueur;
    enveloppe.num_sequence = htonl(num_seq);

    if(sendto(mon_socket_udp, &enveloppe, sizeof(EnteteUDP), 0,
              (struct sockaddr*)&dest, sizeof(struct sockaddr_in)) < 0) {
        printf("[ERREUR] Impossible d'envoyer le message système (Type %d)\n", type_msg);
    } else {
        printf("[RÉSEAU] Message système (Type %d) envoyé avec succès.\n", type_msg);
    }
}

// Reseau->Python
char *diffusion_message_sens2(int reseau_fd){
    struct sockaddr_in addr_distant;
    socklen_t addr_len = sizeof(addr_distant);      

    int size_chaine_json = 10049;
    int TAILLE_PAQUET = size_chaine_json + sizeof(EnteteUDP); 
    char *Buffer = malloc(TAILLE_PAQUET);
    if(Buffer == NULL){
        printf("erreur d'allocation du buffer");
        return NULL;
    }

    if(recvfrom(reseau_fd, Buffer, TAILLE_PAQUET, 0,
                (struct sockaddr*)&addr_distant, &addr_len) < 0){
        printf("echec de reception du paquet");
        free(Buffer);
        return NULL;
    }

    add_peer_if_new(addr_distant);
   
    EnteteUDP *enveloppe_recue = (EnteteUDP *)Buffer;
    actualiser_activite(addr_distant, enveloppe_recue->id_expediteur);

    uint32_t seq_recu = ntohl(enveloppe_recue->num_sequence);
    uint16_t taille_json = ntohs(enveloppe_recue->taille_payload);

    switch (enveloppe_recue->type_message)
    {
        case 3: /* demande_pairs — un nouveau joueur demande la liste des pairs */
            printf("[P2P] Demande de liste reçue de %s\n", inet_ntoa(addr_distant.sin_addr));

            // 1. Construire la liste des pairs connus
            int nb = 0;
            struct paire *pairs = get_connected_peers(&nb);

            cJSON *reponse_json = cJSON_CreateObject();
            cJSON_AddStringToObject(reponse_json, "type", "liste_pairs");
            cJSON *liste = cJSON_CreateArray();

            for (int i = 0; i < nb; i++) {
                // Ne pas inclure l'expéditeur dans la liste
                if (pairs[i].addr.sin_addr.s_addr == addr_distant.sin_addr.s_addr) continue;
                cJSON *pair_obj = cJSON_CreateObject();
                cJSON_AddStringToObject(pair_obj, "ip", inet_ntoa(pairs[i].addr.sin_addr));
                cJSON_AddItemToArray(liste, pair_obj);
            }
            cJSON_AddItemToObject(reponse_json, "pairs", liste);
            char *json_liste = cJSON_PrintUnformatted(reponse_json);
            cJSON_Delete(reponse_json);

            // 2. Envoyer la liste au nouveau joueur
            EnteteUDP env_liste;
            memset(&env_liste, 0, sizeof(env_liste));
            env_liste.taille_payload = htons(strlen(json_liste));
            env_liste.type_message = 4;
            env_liste.id_expediteur = mon_id_joueur;
            env_liste.num_sequence = htonl(compteur_sequence++);

            int taille_liste = strlen(json_liste) + sizeof(EnteteUDP);
            char *buf_liste = malloc(taille_liste);
            if (buf_liste != NULL) {
                memcpy(buf_liste, &env_liste, sizeof(EnteteUDP));
                memcpy(buf_liste + sizeof(EnteteUDP), json_liste, strlen(json_liste));
                sendto(reseau_fd, buf_liste, taille_liste, 0,
                       (struct sockaddr*)&addr_distant, sizeof(addr_distant));
                free(buf_liste);
                printf("[P2P] Liste des pairs envoyée à %s\n", inet_ntoa(addr_distant.sin_addr));
            }
            free(json_liste);

            // 3. Informer les autres pairs de l'arrivée du nouveau joueur
            char json_nouveau[256];
            sprintf(json_nouveau, "{\"type\":\"nouveau_pair\",\"ip\":\"%s\"}",
                    inet_ntoa(addr_distant.sin_addr));

            for (int i = 0; i < nb; i++) {
                if (pairs[i].addr.sin_addr.s_addr == addr_distant.sin_addr.s_addr) continue;

                EnteteUDP env_nouveau;
                memset(&env_nouveau, 0, sizeof(env_nouveau));
                env_nouveau.taille_payload = htons(strlen(json_nouveau));
                env_nouveau.type_message = 6;
                env_nouveau.id_expediteur = mon_id_joueur;
                env_nouveau.num_sequence = htonl(compteur_sequence++);

                int taille_nouveau = strlen(json_nouveau) + sizeof(EnteteUDP);
                char *buf_nouveau = malloc(taille_nouveau);
                if (buf_nouveau != NULL) {
                    memcpy(buf_nouveau, &env_nouveau, sizeof(EnteteUDP));
                    memcpy(buf_nouveau + sizeof(EnteteUDP), json_nouveau, strlen(json_nouveau));
                    sendto(reseau_fd, buf_nouveau, taille_nouveau, 0,
                           (struct sockaddr*)&pairs[i].addr, sizeof(pairs[i].addr));
                    free(buf_nouveau);
                    printf("[RELAY] Informé %s de l'arrivée de %s\n",
                           inet_ntoa(pairs[i].addr.sin_addr),
                           inet_ntoa(addr_distant.sin_addr));
                }
            }

            free(Buffer);
            return NULL;

        case 4: /* liste_pairs — reçu par le nouveau joueur */
            printf("[P2P] Liste des pairs reçue !\n");
            {
                char *json_liste_recu = malloc(taille_json + 1);
                if (!json_liste_recu) { free(Buffer); return NULL; }
                memcpy(json_liste_recu, Buffer + sizeof(EnteteUDP), taille_json);
                json_liste_recu[taille_json] = '\0';
                free(Buffer);
                return json_liste_recu;
            }

        case 5:
        case 0: /* MOVE, UPDATE, HANDSHAKE etc. */
            printf("Message Reçu\n");
            usleep(5000);

            message_systeme(reseau_fd, 1, seq_recu, addr_distant);

            char *donnee_json = malloc(taille_json + 1);
            if (!donnee_json) { free(Buffer); return NULL; }
            memcpy(donnee_json, Buffer + sizeof(EnteteUDP), taille_json);
            donnee_json[taille_json] = '\0';
            free(Buffer);
            return donnee_json;

        case 1: /* ACK — nettoyage de la file d'attente */
            printf("[NOUVEAU] ACK recu pour le message %u\n", seq_recu);
            {
                uint32_t seq_confirmee = ntohl(enveloppe_recue->num_sequence);
                supprimer_de_la_file(seq_confirmee, addr_distant);
            }
            free(Buffer);
            return NULL;

        case 2: /* PING */
            printf("[SYSTEME] Ping reçu de l'expéditeur.\n");
            free(Buffer);
            return NULL;

        case 6: /* nouveau_pair — reçu par les pairs existants */
            printf("[P2P] Nouveau pair signalé !\n");
            {
                char *json_nouveau_recu = malloc(taille_json + 1);
                if (!json_nouveau_recu) { free(Buffer); return NULL; }
                memcpy(json_nouveau_recu, Buffer + sizeof(EnteteUDP), taille_json);
                json_nouveau_recu[taille_json] = '\0';
                free(Buffer);
                return json_nouveau_recu;
            }

        default:
            printf("[ALERTE] Type de message inconnu reçu.\n");
            free(Buffer);
            return NULL;
    }
}

void verifier_retransmissions(int mon_socket_udp) {
    long maintenant = get_time();
    long DELAI_RETRANSMISSION = 300;
    
    NoeudAttente *actuel = file_attente;

    while (actuel != NULL) {
        if (maintenant - actuel->temps_envoi > DELAI_RETRANSMISSION) {
            int taille_json = strlen(actuel->payload);
            int taille_totale = sizeof(EnteteUDP) + taille_json;

            char *BufferRelance = malloc(taille_totale);
            if (BufferRelance != NULL) {
                memcpy(BufferRelance, &actuel->entete, sizeof(EnteteUDP));
                memcpy(BufferRelance + sizeof(EnteteUDP), actuel->payload, taille_json);

                sendto(mon_socket_udp, BufferRelance, taille_totale, 0, 
                       (struct sockaddr*)&(actuel->dest), sizeof(struct sockaddr_in));
                free(BufferRelance);
                
                printf("[RETRANSMISSION] Renvoi du message %u vers %s:%d\n", 
                       ntohl(actuel->entete.num_sequence),
                       inet_ntoa(actuel->dest.sin_addr), 
                       ntohs(actuel->dest.sin_port));
            }
            actuel->temps_envoi = maintenant;
        }
        actuel = actuel->suivant;
    }
}

long get_time() {
    struct timeval temps;
    gettimeofday(&temps, NULL);
    return (temps.tv_sec * 1000) + (temps.tv_usec / 1000);
}

void supprimer_de_la_file(uint32_t seq_a_supprimer, struct sockaddr_in expediteur) {
    NoeudAttente *actuel = file_attente;
    NoeudAttente *precedent = NULL;

    while (actuel != NULL) {
        if (ntohl(actuel->entete.num_sequence) == seq_a_supprimer &&
            actuel->dest.sin_addr.s_addr == expediteur.sin_addr.s_addr &&
            actuel->dest.sin_port == expediteur.sin_port) {
            
            if (precedent == NULL) {
                file_attente = actuel->suivant;
            } else {
                precedent->suivant = actuel->suivant;
            }
            free(actuel);
            printf("[FIABILITÉ] Message %u supprimé de la file d'attente.\n", seq_a_supprimer);
            return;
        }
        precedent = actuel;
        actuel = actuel->suivant;
    }
    printf("[INFO] ACK reçu pour %u, mais message déjà supprimé ou inconnu.\n", seq_a_supprimer);
}

void nettoyer_file_joueur_parti(struct sockaddr_in joueur_parti) {
    NoeudAttente *actuel = file_attente;
    NoeudAttente *precedent = NULL;
    int compteur = 0;

    while (actuel != NULL) {
        if (actuel->dest.sin_addr.s_addr == joueur_parti.sin_addr.s_addr &&
            actuel->dest.sin_port == joueur_parti.sin_port) {
            
            NoeudAttente *a_supprimer = actuel;
            if (precedent == NULL) {
                file_attente = actuel->suivant;
                actuel = file_attente;
            } else {
                precedent->suivant = actuel->suivant;
                actuel = actuel->suivant;
            }
            free(a_supprimer);
            compteur++;
        } else {
            precedent = actuel;
            actuel = actuel->suivant;
        }
    }

    if (compteur > 0) {
        printf("[SYSTEME] Nettoyage : %d messages supprimés pour le joueur %s:%d (déconnecté).\n", 
               compteur, inet_ntoa(joueur_parti.sin_addr), ntohs(joueur_parti.sin_port));
    }
}

void set_mon_id(uint8_t id) {
    mon_id_joueur = id;
}