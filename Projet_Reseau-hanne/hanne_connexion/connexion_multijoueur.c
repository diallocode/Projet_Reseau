#include <stdio.h>
#include <syscall.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <ifaddrs.h>
#include <netinet/in.h>
#include <fcntl.h>
#define NB_JOUEUR_MAX 5
int portno=1024;
int sockfd;
   struct paire{
       struct sockaddr_in addr;
       int id ;
   };
   struct paire paire_connected[NB_JOUEUR_MAX];
   int nb_joueur_connecte=0;
   void add_peer_if_new(struct sockaddr_in new_peer_addr) {
   for (int i = 0; i < nb_joueur_connecte; i++) {
       if (paire_connected[i].addr.sin_addr.s_addr == new_peer_addr.sin_addr.s_addr &&
           paire_connected[i].addr.sin_port == new_peer_addr.sin_port) {
           return;
       }
   }
   if (nb_joueur_connecte< NB_JOUEUR_MAX) {
       paire_connected[nb_joueur_connecte].addr = new_peer_addr;//on ajoute le nouvel joueur
       paire_connected[nb_joueur_connecte].id = nb_joueur_connecte ; //on lui attribue un id unique
       nb_joueur_connecte++;
       printf("Nouveau pair ajouté ! Total : %d\n", nb_joueur_connecte);
   }
}




struct paire* get_connected_peers(int *count) {
   *count = nb_joueur_connecte;
   return paire_connected;
}








int main(){
   //creation de la socket
    struct sockaddr_in my_addr;
   socklen_t addr_len=sizeof(my_addr);
   sockfd=socket(AF_INET,SOCK_DGRAM,0);
   if(sockfd==-1){
       perror("connexion echouée");
       exit(EXIT_FAILURE);
   }
   //on met la structure d'addresse à zero et on écoute sur tous les ports
   memset(&my_addr,0,sizeof(my_addr));
   my_addr.sin_addr.s_addr=INADDR_ANY;
   my_addr.sin_family=AF_INET;
   my_addr.sin_port=htons(portno);
 
   //on peut binder le sockeet
   if (bind(sockfd,(struct sockaddr *)&my_addr,sizeof(my_addr))<0){
       perror("bind echoué");
       exit(EXIT_FAILURE);
   }
   //rcvfrom est par defaut bloquant , si y'a pas de connexion il fait rien ; on va corriger avec fcntl pour le rendre non bloquant
    int flags = fcntl(sockfd, F_GETFL, 0);
    fcntl(sockfd, F_SETFL, flags | O_NONBLOCK);
   printf("socket ouvert sur le port %d\n",portno);
   //on récupere et affiche les addresses ip publiques pour qu'elles soient visibles aux autres potents joueurs
   struct ifaddrs *ifaddrp,*ifad;
   struct sockaddr_in *sa;
   char *addr;
   //on liste les interfacesqui sont dispo dans les differentees cartes réseaux
   getifaddrs(&ifaddrp);
   for(ifad = ifaddrp; ifad != NULL; ifad = ifad->ifa_next){
       //on recup que les ip de type AF_INET
       if(ifad->ifa_addr && ifad->ifa_addr->sa_family == AF_INET){
           sa=(struct sockaddr_in *)ifad->ifa_addr;
           addr=inet_ntoa(sa->sin_addr); //on convertiti en format ip
           printf("Adresse IP publique: %s\n",addr);
           //on s'assure que l'adresse ip n'est pas celle de loopback pour ne pas afficher une adresse ip locale
           if(strcmp(addr,"127.0.0.1")!=0){      
               printf("Adresse IP publique: %s\n",addr);
           }
       }
   }
   freeifaddrs(ifaddrp); //libération de la mémoire allouée pour les interfaces réseau
   //la partie concernant les joueurs qui vont se connecctés








 
//affichage des infos recus
   char rep[1024];
   struct sockaddr_in addr_srv;
   socklen_t sender_len=sizeof(addr_srv);
   //on peut recevoir les mess
   while(1){
       int  n=recvfrom(sockfd,rep,1024,0, (struct sockaddr *)&addr_srv,&sender_len);
       if(n>0){
           rep[n]='\0';
           printf("Message reçu de %s:%d - %s\n",inet_ntoa(addr_srv.sin_addr),ntohs(addr_srv.sin_port),rep);
           add_peer_if_new(addr_srv); //on ajoute le joueur si il n'est pas déjà dans la liste
       }
     
   }
   //fermeture de la connexion udp
    close(sockfd);
    return 0;




}


