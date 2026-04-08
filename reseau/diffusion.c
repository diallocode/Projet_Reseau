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
        if(sendto(mon_socket_udp, Buffer, TAILLE_PAQUET, MSG_CONFIRM, (struct sockaddr*)dest_addr, sizeof(dest_addr)) < 0){
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
    strncpy(nouveau_colis->payload, donnee_json, sizeof(nouveau_colis->payload) - 1);   // copi
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
int diffusion_message_sens2(){};




// Fonction utilitaire pour avoir le temps en millisecondes
long get_time() {
    struct timeval temps;
    gettimeofday(&temps, NULL);
    return (temps.tv_sec * 1000) + (temps.tv_usec / 1000);
}