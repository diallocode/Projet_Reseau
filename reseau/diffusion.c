#include "diffusion.h"
#include "cJSON.h"



// Le point de départ de ta file d'attente
NoeudAttente *file_attente = NULL;


// Fonction qui fait tout le traitement, prend en parametre le JSON recu
int diffusion_message_sens1(const char *donnee_json){

    // CREATION DE L'ENVELOPPE
    cJSON *json_obj = cJSON_Parse(donnee_json);     // parsing du json
    if(json_obj == NULL){
        printf("Erreur : echec du parsing\n");
        return 1;
    }

    // enveloppe du message
    EnteteUDP enveloppe;        
    enveloppe.taille_payload = htons((uint16_t)strlen(donnee_json));        // taille
    enveloppe.type_message = 0;
    static uint32_t compteur_sequence = 0;          // sequence
    enveloppe.num_sequence = htonl(compteur_sequence);
    compteur_sequence++;

    // Recuperation de la liste des destinateurs
    typedef struct list_players
    {
        uint32_t ip;        // l'address ip du joueur
        int fd;             // file descriptor du socket UDP
        struct list_players *next;     // le suivant
    } list_players;
    
    list_players *players = NULL;       // a recuperer a partir de chez oumar

    /* TRANSMISSION DU PAQUET  */

    // Le buffer
    int TAILLE_PAQUET = strlen(donnee_json) + sizeof(EnteteUDP); 
    char *Buffer = malloc(sizeof(TAILLE_PAQUET));
    if(Buffer == NULL){
        printf("erreur d'allocation du buffer");
        return -1;
    }

    // Remplissage du buffer
    char *tmp = memcpy(Buffer, &enveloppe, sizeof(EnteteUDP));
    char *tmp2 = memcpy(Buffer + sizeof(EnteteUDP), donnee_json, strlen(donnee_json));


    // Boucle principale (sur la liste chainee)
    list_players *tmp = players;
    while (tmp->next != NULL)
    {
        /* diffusion vers tous les players */

    }
    


    return 0;
}


int diffusion_message_sens2(){};