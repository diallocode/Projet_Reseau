/**
 * @file connexion_multi.c
 * @brief Implémentation de la gestion des pairs et du suivi d'activité.
 */

#include "connexion_multi.h"


#define NB_JOUEUR_MAX 5

struct paire paire_connected[NB_JOUEUR_MAX];
int nb_joueur_connecte = 0;



/**
 * @brief Ajoute un nouveau pair à la liste s'il n'existe pas déjà.
 * @param addr L'adresse réseau du pair à ajouter.
 */
void add_peer_if_new(struct sockaddr_in new_peer_addr) {
    printf("[DEBUG] Tentative ajout pair : %s:%d\n",
    inet_ntoa(new_peer_addr.sin_addr),
    ntohs(new_peer_addr.sin_port)); 


   for (int i = 0; i < nb_joueur_connecte; i++) {
       if (paire_connected[i].addr.sin_addr.s_addr == new_peer_addr.sin_addr.s_addr &&
           paire_connected[i].addr.sin_port == new_peer_addr.sin_port) {
           return; // Déjà connu !
       }
   }
   if (nb_joueur_connecte < NB_JOUEUR_MAX) {
       paire_connected[nb_joueur_connecte].addr = new_peer_addr;
       paire_connected[nb_joueur_connecte].dernier_vu = time(NULL);
       paire_connected[nb_joueur_connecte].id = 0;
       nb_joueur_connecte++;
       printf("[CARNET] Nouveau pair ajouté ! Total : %d\n", nb_joueur_connecte);
   }
}


/**
 * @brief Récupère la liste des pairs actuellement connectés.
 * @param count Pointeur vers un entier qui recevra le nombre de pairs.
 * @return Un pointeur vers le tableau de structures paire.
 */
struct paire* get_connected_peers(int *count) {
   *count = nb_joueur_connecte;
   return paire_connected;
}

/**
 * @brief Affiche l'IP du joueur actuel
 */
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

/**
 * @brief Fermet un socket
 */
int close_socket(int sockfd) {
     close(sockfd);
     return 0;
}

/**
 * @brief Supprime les joueurs n'ayant pas envoyé de signal depuis plus de 10 secondes.
 */
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
    return -1; 
}


/**
 * @brief Deconnexion dans le cas ou l'utilisateur appui sur quitter (on peut identifier l'utilisateur à trvaers son ip et port)
 */
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


/**
 * @brief Supprimer un joueur du carnet d'adresse
 * @param index La position du joueur dans la liste (le carnet)
 */
int remove_peer(int index) {
    if (index < 0 || index >= nb_joueur_connecte) return -1;
   
    int id_supprime = paire_connected[index].id;
    printf("[CARNET] Le joueur ID %d a ete supprime de la liste de diffusion.\n", id_supprime);

    for (int i = index; i < nb_joueur_connecte - 1; i++) {
        paire_connected[i] = paire_connected[i + 1];
    }
    
    nb_joueur_connecte--;
    
    printf("[CARNET] Joueurs restants : %d\n", nb_joueur_connecte);
    return id_supprime; // On retourne l'ID du joueur supprimé pour que tanou puisse faire son broadcast
}


/**
 * @brief Met à jour le timestamp d'activité d'un joueur et vérifie son identité.
 * @details Si l'ID est déjà utilisé par une autre adresse, le message est ignoré (protection contre l'usurpation).
 * @param addr Adresse de l'expéditeur.
 * @param vrai_id_joueur ID déclaré dans le paquet UDP.
 */
void actualiser_activite(struct sockaddr_in addr, uint32_t vrai_id_joueur) {
    printf("[DEBUG] actualiser_activite cherche %s:%d\n",
    inet_ntoa(addr.sin_addr), ntohs(addr.sin_port));
   for (int i = 0; i < nb_joueur_connecte; i++) {
        if (paire_connected[i].id == vrai_id_joueur) {
            
            // On verifie que m ce n'est PAS la même adresse IP ou le même Port qu'un autre joueur !
            if (paire_connected[i].addr.sin_addr.s_addr != addr.sin_addr.s_addr || 
                paire_connected[i].addr.sin_port != addr.sin_port) {
                
                printf("[ALERTE] USURPATION D'IDENTITÉ ! L'ID %d est déjà utilisé par un autre joueur.\n", vrai_id_joueur);
                return; // On rejette ce paquet, on ne met pas à jour l'activité !
            }
        }

       if (paire_connected[i].addr.sin_addr.s_addr == addr.sin_addr.s_addr &&
           paire_connected[i].addr.sin_port == addr.sin_port) {
          
           paire_connected[i].dernier_vu = get_time();
           paire_connected[i].id = vrai_id_joueur; // On met à jour le carnet avec le vrai ID de l'adversaire !
          
           return;
       }
   }
}


/**
 * @brief Affiche les Joueur participants (IPs/PORTs/IDs)
 */
void afficher_liste_joueurs() {
    int nb_joueurs = 0;
    
    // On récupère le tableau et le nombre exact de joueurs
    struct paire *joueurs = get_connected_peers(&nb_joueurs);

    printf("\n=== LISTE DES JOUEURS CONNECTÉS (%d) ===\n", nb_joueurs);
    
    if (nb_joueurs == 0) {
        printf(" -> Aucun joueur distant dans le carnet.\n");
    } else {
        long temps_actuel = time(NULL);
        
        for (int i = 0; i < nb_joueurs; i++) {
            char *ip = inet_ntoa(joueurs[i].addr.sin_addr);
            int port = ntohs(joueurs[i].addr.sin_port);
            int inactif_depuis = temps_actuel - joueurs[i].dernier_vu;

            printf(" [%d] Joueur ID : %u | IP : %s | Port : %d | Inactif depuis : %ds\n", 
                   i, joueurs[i].id, ip, port, inactif_depuis);
        }
    }
    printf("==========================================\n\n");
}