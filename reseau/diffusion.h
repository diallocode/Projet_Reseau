#ifndef DIFFUSION_H
#define DIFFUSION_H

#include "socket_compat.h" // On utilise notre traducteur universel
#include <stdint.h>

// Structure de l'entête UDP (Format fixe pour tous les OS)
#pragma pack(push, 1)
typedef struct {
    uint16_t taille_payload;
    uint8_t  type_message;
    uint32_t id_expediteur;
    uint32_t num_sequence;
} EnteteUDP;
#pragma pack(pop)

// Structure pour la file d'attente des ACKs
typedef struct NoeudAttente {
    EnteteUDP entete;
    char payload[12288];
    long temps_envoi;
    struct sockaddr_in dest;
    struct NoeudAttente *suivant;
} NoeudAttente;

// Prototypes portables (utilisent SOCKET_T)
int diffusion_message_sens1(const char *donnee_json, SOCKET_T mon_socket_udp, uint8_t type_msg);
char* diffusion_message_sens2(SOCKET_T reseau_fd);
void verifier_retransmissions(SOCKET_T mon_socket_udp);
void message_systeme(SOCKET_T mon_socket_udp, uint8_t type_msg, uint32_t num_seq, struct sockaddr_in dest);
void supprimer_de_la_file(uint32_t seq, struct sockaddr_in expediteur);
void nettoyer_file_joueur_parti(struct sockaddr_in joueur_parti);
long get_time();
void set_mon_id(uint32_t id);

#endif