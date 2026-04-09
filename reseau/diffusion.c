#include "diffusion.h"
#include "cJSON.h"
#include "connexion_multi.h"


/*static int ids_deja_pris[10] = {0}; // Tableau rempli de 0
static long temps_debut_recherche = 0; // Chronomètre*/


// Le point de départ de ta file d'attente
NoeudAttente *file_attente = NULL;

static uint8_t mon_id_joueur = 0; // identifiant du joueur
static uint32_t compteur_sequence = 0;   // sequence

// Python->Reseau
int diffusion_message_sens1(const char *donnee_json, int mon_socket_udp, uint8_t type_msg){

    // CREATION DE L'ENVELOPPE
    EnteteUDP enveloppe;        
    enveloppe.taille_payload = htons((uint16_t)strlen(donnee_json));        // taille
    enveloppe.type_message = type_msg;
    enveloppe.id_expediteur = mon_id_joueur;
    enveloppe.num_sequence = htonl(compteur_sequence);
    compteur_sequence++;

    // Recuperation de la liste des destinateurs
    int nombre_de_joueurs = 0;
    struct paire *players = get_connected_peers(&nombre_de_joueurs);   //

    /* TRANSMISSION DU PAQUET  */
    // Le buffer
    int TAILLE_PAQUET = strlen(donnee_json) + sizeof(EnteteUDP); 
    char *Buffer = malloc(TAILLE_PAQUET);
    if(Buffer == NULL){
        printf("erreur d'allocation du buffer");
        return -1;
    }

    // Remplissage du buffer
    char *tmp = memcpy(Buffer, &enveloppe, sizeof(EnteteUDP));
    char *tmp2 = memcpy(Buffer + sizeof(EnteteUDP), donnee_json, strlen(donnee_json));


    // Boucle principale (sur la liste chainee)
    for (int i = 0; i < nombre_de_joueurs; i++)
    {
        /* code */
        struct sockaddr_in dest_addr = players[i].addr;

        /* diffusion vers tous les players */
        if(sendto(mon_socket_udp, Buffer, TAILLE_PAQUET, 0, (struct sockaddr*)&dest_addr, sizeof(struct sockaddr_in)) < 0){
            printf("erreur-sendto");
        }

        NoeudAttente *nouveau_colis = (NoeudAttente*)malloc(sizeof(NoeudAttente));
        if (nouveau_colis != NULL) {
            // en tete
            nouveau_colis->entete = enveloppe;

            // donnee-json
            strncpy(nouveau_colis->payload, donnee_json, sizeof(nouveau_colis->payload) - 1);
            nouveau_colis->payload[sizeof(nouveau_colis->payload) - 1] = '\0';
            nouveau_colis->temps_envoi = get_time();    // temps
            
            // On sauvegarde l'adresse exacte de la cible !
            nouveau_colis->dest = dest_addr; 

            nouveau_colis->suivant = file_attente;
            file_attente = nouveau_colis;
        }
    }

    free(Buffer);
    return 0;
}



//  ACK et PING
void message_systeme(int mon_socket_udp, uint8_t type_msg, uint32_t num_seq, struct sockaddr_in dest) {
    
    EnteteUDP enveloppe;
    
    // La taille du payload est de ZERO car pas de JSON
    enveloppe.taille_payload = htons(0); 
    
    enveloppe.type_message = type_msg;
    enveloppe.id_expediteur = mon_id_joueur;
    enveloppe.num_sequence = htonl(num_seq);

    //  On envoie DIRECTEMENT la structure, sans malloc, sans Buffer !
    if(sendto(mon_socket_udp, &enveloppe, sizeof(EnteteUDP), 0, (struct sockaddr*)&dest, sizeof(struct sockaddr_in)) < 0) {
        printf("[ERREUR] Impossible d'envoyer le message système (Type %d)\n", type_msg);
    } else {
        printf("[RÉSEAU] Message système (Type %d) envoyé avec succès.\n", type_msg);
    }
}




// Reseau->Python
char *diffusion_message_sens2(int reseau_fd){
    /*Paquets entrant*/
    struct sockaddr_in addr_distant; // La boîte
    socklen_t addr_len = sizeof(addr_distant);      

    // Buffer de reception du paquet
    int size_chaine_json = 10049;
    int TAILLE_PAQUET = size_chaine_json + sizeof(EnteteUDP); 
    char *Buffer = malloc(TAILLE_PAQUET);
    if(Buffer == NULL){
        printf("erreur d'allocation du buffer");
        return NULL;
    }

    // Reception
    if(recvfrom(reseau_fd, Buffer, TAILLE_PAQUET, 0, (struct sockaddr*)&addr_distant, &addr_len) < 0){
        printf("echec de reception du paquet");
        free(Buffer);
        return NULL;
    }

    add_peer_if_new(addr_distant); // ajoute a la liste de diffusion
    //actualiser_activite(addr_distant);  // On remet son temps a 0
    // recuperation de l'enveloppe
    EnteteUDP *enveloppe_recue = (EnteteUDP *)Buffer;
    actualiser_activite(addr_distant, enveloppe_recue->id_expediteur);

    // Conversion dans le bon format
    uint32_t seq_recu = ntohl(enveloppe_recue->num_sequence);
    uint16_t taille_json = ntohs(enveloppe_recue->taille_payload);

    // Verfication du type 
    switch (enveloppe_recue->type_message)
    {
        
        case 0: /* MOVE INIT ATTACK etc.... */
            printf("Message Reçu");
            // Pour indiquer qu'on a recu le paquet (ACK)
            message_systeme(reseau_fd, 1, seq_recu, addr_distant);    

            char *donnee_json = malloc(taille_json+1);
            memcpy(donnee_json, Buffer + sizeof(EnteteUDP), taille_json);
            donnee_json[taille_json] = '\0';    // fermeture correcte de la chaine

            free(Buffer);   // libere le buffer
            return donnee_json;

        case 1: /* Nettoyage de la file d'attente */
            printf("[NOUVEAU] ACK recu pour le message %u\n", seq_recu);

            // suppression dans la file d'attente
            uint32_t seq_confirmee = ntohl(enveloppe_recue->num_sequence);
            supprimer_de_la_file(seq_confirmee, addr_distant);

            free(Buffer);
            return NULL;

        case 2: /* detection de la deconnexion */
            printf("[SYSTEME] Ping reçu de l'expéditeur.\n");
            //signaler_presence_a_oumar(addr_distant);  // On signale la presence du joeur

            free(Buffer);
            return NULL;

        /*case 3: // Premiere tentative de connexion (connect)
            printf("[P2P] Requête de découverte reçue de %s:%d\n", inet_ntoa(addr_distant.sin_addr), ntohs(addr_distant.sin_port));
            if (mon_id_joueur > 0) {
                // Je renvoie un Type 6 à l'expéditeur. Mon ID se mettra automatiquement dans l'en-tête.
                message_systeme(reseau_fd, 4, 0, addr_distant);
            }
            free(Buffer);
            return NULL;*/

    default:    /*Message inconnu*/
        printf("[ALERTE] Type de message inconnu reçu.\n");
        free(Buffer);
        return NULL;
    }

}





/*// Fonction pour lancer la recherche d'ID
void demarrer_recherche_id(int mon_socket_udp) {
    printf("[P2P] Démarrage de la recherche d'ID\n");
    
    // On remet le tableau des ID à zéro
    for(int i = 0; i < 10; i++) {
        ids_deja_pris[i] = 0;
    }
    
    // On lance le chronomètre
    temps_debut_recherche = get_time();

    // On envoie la question (Type 5) à tous les amis dans le carnet d'Oumar
    int nombre_de_joueurs = 0;
    struct paire *players = get_connected_peers(&nombre_de_joueurs);
    
    for (int i = 0; i < nombre_de_joueurs; i++) {
        // Attention : on passe un num_seq à 0 car ce n'est pas un message vital à retransmettre
        message_systeme(mon_socket_udp, 5, 0, players[i].addr);
    }
}

// Fonction pour vérifier si le chrono est écoulé et s'attribuer un ID (plus necessaire)
int verifier_fin_recherche_id() {
    // Si on cherche un ID et que 500ms se sont écoulées...
    if (temps_debut_recherche > 0 && (get_time() - temps_debut_recherche > 500)) {
        
        // On cherche le premier ID libre (en commençant à 1)
        uint8_t nouvel_id = 1;
        while (nouvel_id < 10 && ids_deja_pris[nouvel_id] == 1) {
            nouvel_id++;
        }

        // On se l'attribue
        set_mon_id(nouvel_id);
        temps_debut_recherche = 0; // On arrête la recherche
        
        printf(">>>> [SUCCÈS] MON NOUVEL ID EST %d <<<<\n", nouvel_id);
        return nouvel_id; // On retourne l'ID pour que ipc.c prévienne Python
    }
    
    return -1; // La recherche tourne encore
}*/






void verifier_retransmissions(int mon_socket_udp) {
    long maintenant = get_time();
    long DELAI_RETRANSMISSION = 300; // 300ms avant de considérer le paquet perdu
    
    // On récupère la liste des destinations (via Oumar)
    struct sockaddr_in *dest_addr = NULL; 

    NoeudAttente *actuel = file_attente;

    // On fait une boucle sur tes cibles
    while (actuel != NULL) {
        if (maintenant - actuel->temps_envoi > DELAI_RETRANSMISSION) {
            
            // On recalcule la taille totale (En-tête + JSON)
            int taille_json = strlen(actuel->payload);
            int taille_totale = sizeof(EnteteUDP) + taille_json;

            // On prépare le buffer de renvoi
            char *BufferRelance = malloc(taille_totale);
            if (BufferRelance != NULL) {
                memcpy(BufferRelance, &actuel->entete, sizeof(EnteteUDP));
                memcpy(BufferRelance + sizeof(EnteteUDP), actuel->payload, taille_json);

                // On utilise actuel->dest qui est l'adresse spécifique du joueur en retard
                sendto(mon_socket_udp, 
                    BufferRelance, 
                    taille_totale, 
                    0, 
                    (struct sockaddr*)&(actuel->dest), 
                    sizeof(struct sockaddr_in));

                free(BufferRelance);
                
                printf("[RETRANSMISSION] Renvoi du message %u vers %s:%d\n", 
                        ntohl(actuel->entete.num_sequence),
                        inet_ntoa(actuel->dest.sin_addr), 
                        ntohs(actuel->dest.sin_port));
            }

            // On réinitialise le chrono pour lui laisser une nouvelle chance de 300ms
            actuel->temps_envoi = maintenant;
        }
        actuel = actuel->suivant;
    }
}



// Fonction utilitaire pour avoir le temps en millisecondes
long get_time() {
    struct timeval temps;
    gettimeofday(&temps, NULL);
    return (temps.tv_sec * 1000) + (temps.tv_usec / 1000);
}



void supprimer_de_la_file(uint32_t seq_a_supprimer, struct sockaddr_in expediteur) {
    NoeudAttente *actuel = file_attente;
    NoeudAttente *precedent = NULL;

    while (actuel != NULL) {
        // On compare les numéros de séquence (déjà convertis en host-byte-order)
        if (ntohl(actuel->entete.num_sequence) == seq_a_supprimer &&
            actuel->dest.sin_addr.s_addr == expediteur.sin_addr.s_addr &&
            actuel->dest.sin_port == expediteur.sin_port) {
            
            // Si c'est le premier nœud de la liste
            if (precedent == NULL) {
                file_attente = actuel->suivant;
            } else {
                // On saute le nœud actuel dans la chaîne
                precedent->suivant = actuel->suivant;
            }

            // Libération de la mémoire
            free(actuel);
            printf("[FIABILITÉ] Message %u supprimé de la file d'attente.\n", seq_a_supprimer);
            return; // On sort de la fonction
        }

        // On avance dans la liste
        precedent = actuel;
        actuel = actuel->suivant;
    }
    
    printf("[INFO] ACK reçu pour %u, mais message déjà supprimé ou inconnu.\n", seq_a_supprimer);
}




// Sera appeler par Oumar quand un joueur se deconnecte
void nettoyer_file_joueur_parti(struct sockaddr_in joueur_parti) {
    NoeudAttente *actuel = file_attente;
    NoeudAttente *precedent = NULL;
    int compteur = 0;

    while (actuel != NULL) {
        // On compare l'IP et le Port pour identifier le joueur qui vient de partir
        if (actuel->dest.sin_addr.s_addr == joueur_parti.sin_addr.s_addr &&
            actuel->dest.sin_port == joueur_parti.sin_port) {
            
            // On mémorise le nœud à supprimer
            NoeudAttente *a_supprimer = actuel;

            // On ajuste les pointeurs de la liste
            if (precedent == NULL) {
                file_attente = actuel->suivant;
                actuel = file_attente; // On avance au suivant
            } else {
                precedent->suivant = actuel->suivant;
                actuel = actuel->suivant; // On avance au suivant
            }

            free(a_supprimer);
            compteur++;
          
        } else {
            // Si ce n'est pas le joueur concerné, on avance normalement
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

