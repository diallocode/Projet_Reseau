/**
 * @file diffusion.c
 * @brief Implémentation du routage P2P (Unicast/Broadcast) et des ACKs.
 */

#include "diffusion.h"
#include "cJSON.h"
#include "connexion_multi.h"


/** * @brief Tête de la liste chaînée contenant les messages envoyés en attente d'acquittement (ACK). 
 * Utilisée pour garantir la livraison (Reliable UDP).
 */
NoeudAttente *file_attente = NULL;


/** * @brief Identifiant unique de cette instance du jeu. 
 * Assigné par Python, il est inséré dans chaque en-tête UDP sortant (`id_expediteur`).
 */
static uint32_t mon_id_joueur = 0;


/** * @brief Compteur global garantissant que chaque message envoyé possède un identifiant unique. 
 * Incrémenté après chaque envoi.
 */
static uint32_t compteur_sequence = 0;



/**
 * @brief Envoie un message JSON au réseau (vers un ou tous les joueurs).
 * @details Analyse le JSON pour trouver "network_owner" afin de router le message de manière ciblée.
 * @param donnee_json Chaîne JSON fournie par Python.
 * @param mon_socket_udp Socket UDP ouvert.
 * @param type_msg Type du message (update, Handshake, etc.).
 * @return 0 en cas de succès, -1 sinon.
 */
int diffusion_message_sens1(const char *donnee_json, int mon_socket_udp, uint8_t type_msg){

    EnteteUDP enveloppe;        
    enveloppe.taille_payload = htons((uint16_t)strlen(donnee_json));
    enveloppe.type_message = type_msg;
    enveloppe.id_expediteur = htonl(mon_id_joueur);
    enveloppe.num_sequence = htonl(compteur_sequence);
    compteur_sequence++;

    int nombre_de_joueurs = 0;
    struct paire *players = get_connected_peers(&nombre_de_joueurs);

    // On trouve l'id du destinateur
    int cible_id = -1;
    cJSON *json_obj = cJSON_Parse(donnee_json);
    if (json_obj != NULL) {
        cJSON *dest_item = cJSON_GetObjectItemCaseSensitive(json_obj, "network_owner"); 
        
        if (cJSON_IsNumber(dest_item)) {
            cible_id = dest_item->valueint; 
        }
        cJSON_Delete(json_obj); 
    }

    int TAILLE_PAQUET = strlen(donnee_json) + sizeof(EnteteUDP); 
    char *Buffer = malloc(TAILLE_PAQUET);
    if(Buffer == NULL){
        printf("erreur d'allocation du buffer");
        return -1;
    }

    memcpy(Buffer, &enveloppe, sizeof(EnteteUDP));
    memcpy(Buffer + sizeof(EnteteUDP), donnee_json, strlen(donnee_json));

    for (int i = 0; i < nombre_de_joueurs; i++) {

        // On verifie si on doit envoyer a ce joueur
        if(cible_id == -1 || players[i].id == cible_id){
            // --- AJOUT DES LOGS DE PREUVE ---
            if (cible_id == -1) {
                printf("[ROUTAGE] BROADCAST : Envoi à tout le monde -> IP: %s (ID: %u)\n", 
                       inet_ntoa(players[i].addr.sin_addr), players[i].id);
            } else {
                printf("[ROUTAGE] UNICAST : Message privé ciblé -> IP: %s (ID: %u)\n", 
                       inet_ntoa(players[i].addr.sin_addr), players[i].id);
            }
            
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
            // C'est un message cible et on a trouve la cible, on s'arrete
            if(cible_id != -1){
                printf("[CIBLE] : Network_owner -> %d\n", cible_id);
                break;
            }

        }
    }

    free(Buffer);
    return 0;
}

/**
 * @brief Envoie un message système court (sans payload JSON) sur le réseau.
 * @details Utilisée exclusivement pour la signalisation interne du protocole (ACK, PING).
 * L'enveloppe UDP générée indique une taille de payload de 0.
 * * @param mon_socket_udp Le descripteur du socket UDP local utilisé pour l'envoi.
 * @param type_msg Le type de message réseau (ex: 1 pour ACK, 2 pour Ping).
 * @param num_seq Le numéro de séquence auquel ce message fait référence (vital pour valider un ACK).
 * @param dest L'adresse IP et le port du destinataire.
 */
void message_systeme(int mon_socket_udp, uint8_t type_msg, uint32_t num_seq, struct sockaddr_in dest) {
    EnteteUDP enveloppe;
    enveloppe.taille_payload = htons(0); 
    enveloppe.type_message = type_msg;
    enveloppe.id_expediteur = htonl(mon_id_joueur);
    enveloppe.num_sequence = htonl(num_seq);

    if(sendto(mon_socket_udp, &enveloppe, sizeof(EnteteUDP), 0,
              (struct sockaddr*)&dest, sizeof(struct sockaddr_in)) < 0) {
        printf("[ERREUR] Impossible d'envoyer le message système (Type %d)\n", type_msg);
    } else {
        printf("[RÉSEAU] Message système (Type %d) envoyé avec succès.\n", type_msg);
    }
}




/**
 * @brief Réceptionne et traite les messages entrants du réseau.
 * @details Gère les cas système (ACK, Ping, liste des pairs) et transmet les données de jeu à Python.
 * @param reseau_fd Descripteur du socket UDP.
 * @return Le payload JSON si destiné à Python, NULL sinon.
 */
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
    uint32_t vrai_id_expediteur = ntohl(enveloppe_recue->id_expediteur);

    // Verification pour l'id interne
    if (vrai_id_expediteur == mon_id_joueur) {
        printf("[ALERTE] COLLISION D'ID ! Un paquet reçu (IP: %s) tente d'utiliser mon identifiant local (%d). Paquet détruit.\n", 
               inet_ntoa(addr_distant.sin_addr), mon_id_joueur);
        free(Buffer);
        return NULL; // On jette le paquet avant même qu'il ne pollue le système
    }

    actualiser_activite(addr_distant, vrai_id_expediteur);

    uint32_t seq_recu = ntohl(enveloppe_recue->num_sequence);
    uint16_t taille_json = ntohs(enveloppe_recue->taille_payload);

    switch (enveloppe_recue->type_message)
    {
        case 3: /* un nouveau joueur arrivant qui demande la liste des pairs */
            printf("[P2P] Demande de liste reçue de %s\n", inet_ntoa(addr_distant.sin_addr));

            // Construction de la liste des pairs connus
            int nb = 0;
            struct paire *pairs = get_connected_peers(&nb);

            cJSON *reponse_json = cJSON_CreateObject();
            cJSON_AddStringToObject(reponse_json, "type", "liste_pairs");
            cJSON *liste = cJSON_CreateArray();

            for (int i = 0; i < nb; i++) {
                // On exclu l'expéditeur de la liste
                if (pairs[i].addr.sin_addr.s_addr == addr_distant.sin_addr.s_addr) continue;
                cJSON *pair_obj = cJSON_CreateObject();
                cJSON_AddStringToObject(pair_obj, "ip", inet_ntoa(pairs[i].addr.sin_addr));
                cJSON_AddItemToArray(liste, pair_obj);
            }
            cJSON_AddItemToObject(reponse_json, "pairs", liste);
            char *json_liste = cJSON_PrintUnformatted(reponse_json);
            cJSON_Delete(reponse_json);

            // Envoi de la liste au nouveau joueur
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

            // Informer les autres pairs de l'arrivée du nouveau joueur
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

        case 4: /* liste_pairs reçu par le nouveau joueur */
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
            usleep(500000);       // gestion de l'incoherence

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

        case 6: /* nouveau_pair reçu par les pairs existants */
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


/**
 * @brief Vérifie les messages en attente et retransmet ceux qui n'ont pas reçu d'ACK.
 * @details Parcourt la liste chaînée `file_attente`. Si le temps écoulé depuis le dernier 
 * envoi d'un message dépasse le délai de tolérance (fixé à 300 ms), le paquet UDP complet 
 * (en-tête + JSON) est reconstruit et renvoyé au destinataire. Le compteur de temps du 
 * message est alors réinitialisé. C'est le moteur principal de la fiabilité réseau.
 *
 * @param mon_socket_udp Le descripteur du socket UDP local utilisé pour renvoyer les paquets.
 */
void verifier_retransmissions(int mon_socket_udp) {
    long maintenant = get_time();
    long DELAI_RETRANSMISSION = 300; // Fixer
    
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



/**
 * @brief Récupère l'heure actuelle du système avec une précision en millisecondes.
 * @details Fonction utilitaire critique utilisée pour calculer les timeouts d'inactivité (Heartbeat)
 * et mesurer le délai d'attente avant retransmission d'un paquet.
 * * @return Le temps écoulé (timestamp) depuis l'époque UNIX, converti en millisecondes.
 */
long get_time() {
    struct timeval temps;
    gettimeofday(&temps, NULL);
    return (temps.tv_sec * 1000) + (temps.tv_usec / 1000);
}


/**
 * @brief Retire un message de la file d'attente suite à la réception de son accusé de réception (ACK).
 * @details Parcourt la liste chaînée `file_attente`. Si un nœud correspond exactement au numéro de 
 * séquence et à l'adresse de l'expéditeur de l'ACK, il est retiré de la liste et libéré de la mémoire.
 * * @param seq_a_supprimer Le numéro de séquence (num_sequence) confirmé par le destinataire.
 * @param expediteur L'adresse (IP et Port) du pair qui vient de valider la réception.
 */
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


/**
 * @brief Purge la file d'attente de tous les messages destinés à un joueur déconnecté.
 * @details Lorsqu'un pair quitte la partie (timeout ou déconnexion volontaire), cette fonction 
 * évite que le programme ne tente de lui retransmettre indéfiniment des messages dans le vide.
 * * @param joueur_parti L'adresse réseau (IP et Port) du joueur banni ou déconnecté.
 */
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


/**
 * @brief Enregistre l'identifiant local du joueur fourni par l'application Python.
 * @details Cette fonction est appelée via IPC au démarrage du jeu. L'ID stocké sera 
 * utilisé comme signature (id_expediteur) pour tous les paquets UDP générés par la suite.
 * * @param id L'identifiant attribué à ce client.
 */
void set_mon_id(uint32_t id) {
    mon_id_joueur = id;
}