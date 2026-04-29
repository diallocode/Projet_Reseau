#include "socket_compat.h"   // de l'entete socket_compat pour la compatibilité entre Windows et Debian
#include "connexion_multi.h"
#include <stdio.h>
#include <string.h>
#include <time.h> 
#ifndef _WIN32
#include <ifaddrs.h> // Uniquement pour Linux
#endif
#define NB_JOUEUR_MAX 5

struct paire paire_connected[NB_JOUEUR_MAX];
int nb_joueur_connecte = 0;

//  La fonction pour ajouter un contact
void add_peer_if_new(struct sockaddr_in new_peer_addr) {
    printf("[DEBUG] Tentative ajout pair : %s:%d\n",
    inet_ntoa(new_peer_addr.sin_addr),
    ntohs(new_peer_addr.sin_port));  // ← ce port est-il bien 5002 ?


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

// La fonction pour lire le carnet
struct paire* get_connected_peers(int *count) {
   *count = nb_joueur_connecte;
   return paire_connected;
}

// La fonction pour afficher les IP (extraite de son main)

//on la protege selon qu'il soit compilé sur Windows ou Linux pour eviter les erreurs de compilation sur Windows
void afficher_mes_ips() {
    printf("--- MES ADRESSES IP POUR JOUER ---\n");

#ifndef _WIN32
    // --- Code pour Linux (Debian) ---
    struct ifaddrs *ifaddrp, *ifad;
    char *addr;
    if (getifaddrs(&ifaddrp) == -1) return;

    for(ifad = ifaddrp; ifad != NULL; ifad = ifad->ifa_next){
        if(ifad->ifa_addr && ifad->ifa_addr->sa_family == AF_INET){
            addr = inet_ntoa(((struct sockaddr_in *)ifad->ifa_addr)->sin_addr);
            if(strcmp(addr,"127.0.0.1") != 0){      
                printf("-> %s\n", addr);
            }
        }
    }
    freeifaddrs(ifaddrp);
#else
    // --- Code pour Windows (Ton HP) ---
    char szHostName[255];
    // On récupère le nom de la machine
    if (gethostname(szHostName, 255) == 0) {
        struct hostent *host_entry;
        // On cherche les adresses liées à ce nom
        host_entry = gethostbyname(szHostName);
        if (host_entry != NULL) {
            int i = 0;
            // On parcourt la liste des adresses trouvées
            while (host_entry->h_addr_list[i] != NULL) {
                struct in_addr addr;
                memcpy(&addr, host_entry->h_addr_list[i], sizeof(struct in_addr));
                char *ip = inet_ntoa(addr);
                // On n'affiche pas l'adresse de boucle locale
                if (strcmp(ip, "127.0.0.1") != 0) {
                    printf("-> %s (Windows)\n", ip);
                }
                i++;
            }
        }
    }
#endif

    printf("----------------------------------\n");
}

int close_socket(SOCKET_T sockfd) { // on Change int par SOCKET_T pour gerer les tailles de socket sur les deux OS
     CLOSE_SOCKET(sockfd); // Utilise la macro pour garantir la compatibilité
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
    printf("[CARNET] Le joueur ID %d a ete supprime de la liste de diffusion.\n", id_supprime);

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


void actualiser_activite(struct sockaddr_in addr, uint32_t vrai_id_joueur) {
    printf("[DEBUG] actualiser_activite cherche %s:%d\n",
    inet_ntoa(addr.sin_addr), ntohs(addr.sin_port));
   for (int i = 0; i < nb_joueur_connecte; i++) {
       if (paire_connected[i].addr.sin_addr.s_addr == addr.sin_addr.s_addr &&
           paire_connected[i].addr.sin_port == addr.sin_port) {
          
           paire_connected[i].dernier_vu = time(NULL);
           // On met à jour le carnet avec le vrai ID de l'adversaire !
           paire_connected[i].id = vrai_id_joueur;
          
           return;
       }
   }
}



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
            // Conversion de l'IP binaire en chaîne de caractères classique (ex: "192.168.1.10")
            char *ip = inet_ntoa(joueurs[i].addr.sin_addr);
            // Conversion du port binaire en entier classique
            int port = ntohs(joueurs[i].addr.sin_port);
            // Calcul du temps écoulé depuis le dernier message reçu
            int inactif_depuis = temps_actuel - joueurs[i].dernier_vu;

            printf(" [%d] Joueur ID : %u | IP : %s | Port : %d | Inactif depuis : %ds\n", 
                   i, joueurs[i].id, ip, port, inactif_depuis);
        }
    }
    printf("==========================================\n\n");
}

// Ajoute cette fonction dans connexion_multi.c
SOCKET_T initialiser_ma_connexion() {
    SOCKET_T sock;
    struct sockaddr_in mon_addr;

    // 1. Création du socket UDP
    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == INVALID_SOCKET) {
        perror("Erreur création socket");
        return INVALID_SOCKET;
    }

    // 2. Préparation de l'adresse (Port 0 = Dynamique)
    memset(&mon_addr, 0, sizeof(mon_addr));
    mon_addr.sin_family = AF_INET;
    mon_addr.sin_addr.s_addr = INADDR_ANY; 
    mon_addr.sin_port = htons(0); // <--- LE SECRET EST ICI

    // 3. Liaison (Bind)
    if (bind(sock, (struct sockaddr *)&mon_addr, sizeof(mon_addr)) < 0) {
        perror("Erreur bind");
        CLOSE_SOCKET(sock);
        return INVALID_SOCKET;
    }

    // 4. Récupération du port attribué pour l'afficher
    struct sockaddr_in adr_reelle;
    socklen_t len = sizeof(adr_reelle);
    getsockname(sock, (struct sockaddr *)&adr_reelle, &len);

    printf("\n[SUCCÈS] Connexion prête !");
    printf("\n[INFO] Ton port de jeu actuel est : %d", ntohs(adr_reelle.sin_port));
    printf("\n[INFO] Donne ce numéro à ton ami pour qu'il puisse te rejoindre.\n\n");

    return sock;
}