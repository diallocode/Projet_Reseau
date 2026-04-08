#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <sys/time.h>
#include <netinet/in.h>
#include <arpa/inet.h>


// Cette directive magique empêche le compilateur C de rajouter des octets 
// vides (padding) au milieu de ta structure. C'est vital pour le réseau !
#pragma pack(push, 1)



// Structure qui va envelopper le paquet a envoyer
typedef struct
{
    uint8_t type_message;     // Le type du message (sur 1 octet) 
    uint32_t num_sequence;    // Le numero de suivie ( 4 octets)
    uint16_t taille_payload;  // La taille des donnees JSON, pour lire le json (2 octets)
} EnteteUDP;


#pragma pack(pop)



// Structure pour ta "Salle des Machines" (Ne part pas sur le réseau)
typedef struct NoeudAttente {
    EnteteUDP entete;               // La copie de l'en-tête envoyé
    char payload[2048];             // La copie de ton JSON 
    long temps_envoi;               // Le chronomètre (pour savoir quand renvoyer)
    struct NoeudAttente *suivant;   // Le pointeur vers le colis suivant dans la liste !
} NoeudAttente;

