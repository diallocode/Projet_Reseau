#include "connexion_multi.h"
#include <stdio.h>
#include <string.h>
#include <ifaddrs.h>
#include <arpa/inet.h>

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
       // Note : L'ID géré ici par Oumar sautera demain quand tu feras ton système P2P
       paire_connected[nb_joueur_connecte].id = nb_joueur_connecte; 
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