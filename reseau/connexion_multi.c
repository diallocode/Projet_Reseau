#include "connexion_multi.h"
#include <stdio.h>
#include <string.h>
#include <ifaddrs.h>
#include <arpa/inet.h>
#include <unistd.h>

#define NB_JOUEUR_MAX 5

struct paire paire_connected[NB_JOUEUR_MAX];
int nb_joueur_connecte = 0;

//  La fonction pour ajouter un contact
void add_peer_if_new(struct sockaddr_in new_peer_addr) {
   for (int i = 0; i < nb_joueur_connecte; i++) {
       if (paire_connected[i].addr.sin_addr.s_addr == new_peer_addr.sin_addr.s_addr &&
           paire_connected[i].addr.sin_port == new_peer_addr.sin_port) {
           return; // Déjà connu !
       }
   }
   if (nb_joueur_connecte < NB_JOUEUR_MAX) {
       paire_connected[nb_joueur_connecte].addr = new_peer_addr;
       paire_connected[nb_joueur_connecte].dernier_vu = time(NULL);
       nb_joueur_connecte++;
       printf("[CARNET] Nouveau pair ajouté ! Total : %d\n", nb_joueur_connecte);
   }
}

// La fonction pour lire le carnet
struct paire* get_connected_peers(int *count) {
   *count = nb_joueur_connecte;
   return paire_connected;
}

// La fonction pour afficher les IP (extraite de son main)
void afficher_mes_ips() {
   struct ifaddrs *ifaddrp, *ifad;
   char *addr;
   getifaddrs(&ifaddrp);
   printf("--- MES ADRESSES IP POUR JOUER ---\n");
   for(ifad = ifaddrp; ifad != NULL; ifad = ifad->ifa_next){
       if(ifad->ifa_addr && ifad->ifa_addr->sa_family == AF_INET){
           addr = inet_ntoa(((struct sockaddr_in *)ifad->ifa_addr)->sin_addr);
           if(strcmp(addr,"127.0.0.1") != 0){      
               printf("-> %s\n", addr);
           }
       }
   }
   printf("----------------------------------\n");
   freeifaddrs(ifaddrp);
}


int close_socket(int sockfd) {
     close(sockfd);
     return 0;
}


int check_and_get_inactive_paire(int timeout_sec, struct sockaddr_in *addr_out) {
    time_t now = time(NULL);
    for (int i = 0; i < nb_joueur_connecte; i++) {
        if (difftime(now, paire_connected[i].dernier_vu) > timeout_sec) {
            if (addr_out != NULL) {
                *addr_out = paire_connected[i].addr;
            }
            return paire_connected[i].id;
        }
    }
    return -1; // Personne n'est inactif
}


//deconnexion dans le cas ou l'utilisateur appui sur quitter (on peut identifier l'utilisateur à trvaers son ip et port)
void disconnect_paire_by_addr(struct sockaddr_in addr) {
    for (int i = 0; i < nb_joueur_connecte; i++) {
        if (paire_connected[i].addr.sin_addr.s_addr == addr.sin_addr.s_addr &&
            paire_connected[i].addr.sin_port == addr.sin_port) {
            remove_peer(i);
            printf("[INFO] Déconnexion volontaire réussie.\n");
            return;
        }
    }
}

//supprimer un joueuer du carnet d'adresse
int remove_peer(int index) {
    if (index < 0 || index >= nb_joueur_connecte) return -1;
    // 1. On sauvegarde l'ID avant qu'il ne disparaisse
    int id_supprime = paire_connected[index].id;
    printf("[CARNET] Le joueur ID %d nous a quittés.\n", id_supprime);

    // Décalage pour supprimer l'élément du tableau
    for (int i = index; i < nb_joueur_connecte - 1; i++) {
        paire_connected[i] = paire_connected[i + 1];
    }
    
    // On met à jour le nombre total de joueurs connectés
    nb_joueur_connecte--;
    
    // NOTE : On ne touche pas aux .id des autres, ils restent intacts !
    printf("[CARNET] Joueurs restants : %d\n", nb_joueur_connecte);
    return id_supprime; // On retourne l'ID du joueur supprimé pour que tanou puisse faire son broadcast
}


// AJOUTE CETTE FONCTION : Pour dire Il est vivant !
void actualiser_activite(struct sockaddr_in addr, uint32_t vrai_id_joueur) {
    for (int i = 0; i < nb_joueur_connecte; i++) {
        if (paire_connected[i].addr.sin_addr.s_addr == addr.sin_addr.s_addr &&
            paire_connected[i].addr.sin_port == addr.sin_port) {
            
            paire_connected[i].dernier_vu = time(NULL); 
            // NOUVEAU : On met à jour le carnet avec le vrai ID de l'adversaire !
            paire_connected[i].id = vrai_id_joueur; 
            
            return;
        }
    }
}