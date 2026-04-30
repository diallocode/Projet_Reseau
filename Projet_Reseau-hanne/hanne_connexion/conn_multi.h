#ifndef OUMAR_H
#define OUMAR_H

#include <netinet/in.h> // Requis pour la structure sockaddr_in
#include <time.h> // Requis pour gérer les timestamps et les timeouts²
// Structure représentant un joueur dans le carnet d'adresses
struct paire {
    struct sockaddr_in addr;
    int id;
    time_t dernier_vu; // Timestamp pour gérer les timeouts
};

// ==========================================
// PROTOTYPES DES FONCTIONS DU MODULE OUMAR
// ==========================================

/* * Ajoute une nouvelle adresse au carnet si elle n'y est pas déjà.
 * Idéal pour le P2P : appelé à chaque fois qu'on reçoit un paquet inconnu.
 */
void add_peer_if_new(struct sockaddr_in new_peer_addr);

/* * Récupère le carnet d'adresses complet.
 * Le paramètre 'count' sera modifié pour contenir le nombre de joueurs actuels.
 * Retourne un pointeur vers le début du tableau de joueurs.
 */
struct paire* get_connected_peers(int *count);

/* * Affiche toutes les adresses IP publiques de la machine dans le terminal.
 * Utile au lancement du jeu pour que le joueur puisse donner son IP à ses amis.
 */
void afficher_mes_ips();

//fonction pour fermer la connexion 
int close_socket(int sockfd);

int remove_peer(int index);
//qelqu'un qui se deconecte via @ip et port
void disconnect_paire_by_addr(struct sockaddr_in addr);
//verification des @ inactives
int check_and_get_inactive_paire(int timeout_sec);

#endif // OUMAR_H