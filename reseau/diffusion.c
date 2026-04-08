#include "diffusion.h"
#include "cJSON.h"



// Le point de départ de ta file d'attente
NoeudAttente *file_attente = NULL;


// Python->Reseau
int diffusion_message_sens1(const char *donnee_json, int mon_socket_udp){

    // CREATION DE L'ENVELOPPE
    // enveloppe du message
    EnteteUDP enveloppe;        
    enveloppe.taille_payload = htons((uint16_t)strlen(donnee_json));        // taille
    enveloppe.type_message = 0;
    static uint32_t compteur_sequence = 0;          // sequence
    enveloppe.num_sequence = htonl(compteur_sequence);
    compteur_sequence++;

    // Recuperation de la liste des destinateurs
    struct sockaddr_in *dest_addr = NULL;   //

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
    while (dest_addr != NULL)
    {
        /* diffusion vers tous les players */
        if(sendto(mon_socket_udp, Buffer, TAILLE_PAQUET, MSG_CONFIRM, (struct sockaddr*)dest_addr, sizeof(struct sockaddr_in)) < 0){
            printf("erreur-sendto");
        }
        //dest_addr = dest_addr->suivant; // avancement
    }
    
    /*Gestion de la file d'attente*/
    NoeudAttente *nouveau_colis = (NoeudAttente*)malloc(sizeof(NoeudAttente));

    if (nouveau_colis == NULL) {
        perror("Erreur critique : Plus de mémoire pour archiver le colis");
        return 1;
    }

    // ajout de l'enveloppe
    nouveau_colis->entete = enveloppe;

    // ajout du json
    strncpy(nouveau_colis->payload, donnee_json, sizeof(nouveau_colis->payload) - 1);   // copie
    nouveau_colis->payload[sizeof(nouveau_colis->payload) - 1] = '\0';

    // ajout du temp
    nouveau_colis->temps_envoi = get_time(); // a definir plus tard

    //
    nouveau_colis->suivant = file_attente;
    file_attente = nouveau_colis;


    free(Buffer);
    return 0;
}





// Reseau->Python
char *diffusion_message_sens2(int reseau_fd){
    /*Paquets entrant*/
    struct sockaddr_in addr_distant; // La boîte
    socklen_t addr_len = sizeof(addr_distant);      

    // Buffer de reception du paquet
    int size_chaine_json = 2049;
    int TAILLE_PAQUET = size_chaine_json + sizeof(EnteteUDP); 
    char *Buffer = malloc(TAILLE_PAQUET);
    if(Buffer == NULL){
        printf("erreur d'allocation du buffer");
        return -1;
    }

    // Reception
    if(recvfrom(reseau_fd, Buffer, TAILLE_PAQUET, MSG_CONFIRM, (struct sockaddr*)&addr_distant, &addr_len) < 0){
        printf("echec de reception du paquet");
        return NULL;
    }

    // recuperation de l'enveloppe
    EnteteUDP *enveloppe_recue = (EnteteUDP *)Buffer;

    // Conversion dans le bon format
    uint32_t seq_recu = ntohl(enveloppe_recue->num_sequence);
    uint16_t taille_json = ntohs(enveloppe_recue->taille_payload);

    // Verfication du type 
    switch (enveloppe_recue->type_message)
    {
        case 0: /* communication normale, envoi vers ipc */
            char *donnee_json = malloc(taille_json+1);
            memcpy(donnee_json, Buffer + sizeof(EnteteUDP), taille_json);
            donnee_json[taille_json] = '\0';    // fermeture correcte de la chaine

            free(Buffer);   // libere le buffer
            return donnee_json;

        case 1: /* Nettoyage de la file d'attente */
            printf("ACK recu pour le message %u\n", seq_recu);

            // suppression dans la file d'attente
            uint32_t seq_confirmee = ntohl(enveloppe_recue->num_sequence);
            supprimer_de_la_file(seq_confirmee);

            free(Buffer);
            return NULL;

        case 2: /* detection de la deconnexion */
            printf("[SYSTEME] Ping reçu de l'expéditeur.\n");
            signaler_presence_a_oumar(addr_distant);  // On signale la presence du joeur

            free(Buffer);
            return NULL;

    default:    /*Message inconnu*/
        printf("[ALERTE] Type de message inconnu reçu.\n");
        free(Buffer);
        return NULL;
    }

}




// Fonction utilitaire pour avoir le temps en millisecondes
long get_time() {
    struct timeval temps;
    gettimeofday(&temps, NULL);
    return (temps.tv_sec * 1000) + (temps.tv_usec / 1000);
}



void supprimer_de_la_file(uint32_t seq_a_supprimer) {
    NoeudAttente *actuel = file_attente;
    NoeudAttente *precedent = NULL;

    while (actuel != NULL) {
        // On compare les numéros de séquence (déjà convertis en host-byte-order)
        if (ntohl(actuel->entete.num_sequence) == seq_a_supprimer) {
            
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