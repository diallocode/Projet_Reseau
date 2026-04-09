#ifndef OUMAR_H
#define OUMAR_H

#include <netinet/in.h> // Requis pour la structure sockaddr_in

// Structure représentant un joueur dans le carnet d'adresses
struct paire {
    struct sockaddr_in addr;
    int id;
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

#endif // OUMAR_H