/**
 * @file connexion_multi.h
 * @brief Définitions des structures et prototypes pour la gestion des pairs.
 * @author Équipe Reseau
 */

#ifndef CONNEXION_MULTI_H
#define CONNEXION_MULTI_H

#include <netinet/in.h>
#include <time.h> 
#include <stdint.h>  
#include <stdio.h>
#include <string.h>
#include <ifaddrs.h>
#include <arpa/inet.h>
#include <unistd.h>
#include "diffusion.h"

/**
 * @struct paire
 * @brief Structure représentant un joueur distant (un pair).
 */
struct paire {
    struct sockaddr_in addr;    /**< Adresse IP et port du pair. */
    uint32_t id;                /**< Timestamp du dernier message reçu (pour le heartbeat). */
    time_t dernier_vu;          /**< Identifiant unique du joueur distant. */
};



// =========================
// PROTOTYPES DES FONCTIONS 
// =========================

/* * Ajoute une nouvelle adresse au carnet si elle n'y est pas déjà.
 * Pour le P2P : appelé à chaque fois qu'on reçoit un paquet inconnu.
 */
void add_peer_if_new(struct sockaddr_in new_peer_addr);


/* * Récupère le carnet d'adresses complet.
 * Le paramètre 'count' est modifié pour contenir le nombre de joueurs actuels.
 * Retourne un pointeur vers le début du tableau de joueurs.
 */
struct paire* get_connected_peers(int *count);


/* * Affiche toutes les adresses IP publiques de la machine dans le terminal.
 * Utiliser au lancement du jeu pour que le joueur puisse donner son IP à ses amis qui souhaitent rejoindre la partie.
 */
void afficher_mes_ips();


//fonction pour fermer la connexion 
int close_socket(int sockfd);

// Suppression d'un participant de la liste des pairs actifs
int remove_peer(int index);


//qelqu'un qui se deconecte via @ip et port
void disconnect_paire_by_addr(struct sockaddr_in addr);

//verification des @ inactives
int check_and_get_inactive_paire(int timeout_sec, struct sockaddr_in *addr_out);

// Met à jour le timestamp d'activité d'un joueur et vérifie son identité.
void actualiser_activite(struct sockaddr_in addr, uint32_t id_joueur);


/* * Affiche la liste détaillée de tous les joueurs actuellement connectés dans le terminal. */
void afficher_liste_joueurs();

#endif // CONNEXION_MULTI_H