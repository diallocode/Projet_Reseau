#ifndef DIFFUSION__h
#define DIFFUSION__h

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
    uint32_t id_expediteur;     // L'identifiant du joueur
    uint8_t type_message;      // Le type du message 
    uint32_t num_sequence;     // Le numero de suivie 
    uint16_t taille_payload;   // La taille des donnees JSON, pour lire le json (2 octets)
} EnteteUDP;


#pragma pack(pop)



// Structure pour ta "Salle des Machines" (Ne part pas sur le réseau)
typedef struct NoeudAttente {
    EnteteUDP entete;               // La copie de l'en-tête envoyé
    struct sockaddr_in dest;        // Destination du paquet
    char payload[10049];             // La copie de ton JSON 
    long temps_envoi;               // Le chronomètre (pour savoir quand renvoyer)
    struct NoeudAttente *suivant;   // Le pointeur vers le colis suivant dans la liste !
} NoeudAttente;


/*------------------------FONCTIONS--------------------------------- */
extern int diffusion_message_sens1(const char *donnee_json, int mon_socket_udp, uint8_t type_msg);
extern char *diffusion_message_sens2(int reseau_fd);
extern void verifier_retransmissions(int mon_socket_udp);
extern long get_time();
extern void supprimer_de_la_file(uint32_t seq_a_supprimer, struct sockaddr_in expediteur);
extern void message_systeme(int mon_socket_udp, uint8_t type_msg, uint32_t num_seq, struct sockaddr_in dest);
extern void nettoyer_file_joueur_parti(struct sockaddr_in joueur_parti);

extern void set_mon_id(uint8_t id);





#endif