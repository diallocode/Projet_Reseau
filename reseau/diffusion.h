/**
 * @file diffusion.h
 * @brief Structures du protocole UDP et gestion de la fiabilité.
 */


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
// vides (padding) au milieu de la structure. 
#pragma pack(push, 1)



/**
 * @struct EnteteUDP
 * @brief En-tête personnalisé pour les paquets réseau du jeu.
 */
typedef struct
{
    uint32_t id_expediteur;     /**< ID du joueur émetteur. */
    uint8_t type_message;       /**< Type : 0:Jeu, 1:ACK, 2:Ping, etc.. */
    uint32_t num_sequence;      /**< ID du paquet pour acquittement (htonl). */
    uint16_t taille_payload;    /**< Taille du JSON (htons). */
} EnteteUDP;


#pragma pack(pop)



/**
 * @struct NoeudAttente
 * @brief Élément d'une liste chaînée pour la retransmission des messages.
 */
typedef struct NoeudAttente {
    EnteteUDP entete;                /**< Copie de l'en-tête envoyé. */
    struct sockaddr_in dest;         /**< Destination du message. */
    char payload[10049];             /**< Copie du contenu JSON. */
    long temps_envoi;                /**< Heure du dernier envoi (ms). */
    struct NoeudAttente *suivant;    /**< Pointeur vers le message suivant. */
} NoeudAttente;


// Prototypes
extern int diffusion_message_sens1(const char *donnee_json, int mon_socket_udp, uint8_t type_msg);
extern char *diffusion_message_sens2(int reseau_fd);
extern void verifier_retransmissions(int mon_socket_udp);
extern long get_time();
extern void supprimer_de_la_file(uint32_t seq_a_supprimer, struct sockaddr_in expediteur);
extern void message_systeme(int mon_socket_udp, uint8_t type_msg, uint32_t num_seq, struct sockaddr_in dest);
extern void nettoyer_file_joueur_parti(struct sockaddr_in joueur_parti);
extern void set_mon_id(uint32_t id);


#endif