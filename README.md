AI Battle Simulator (Distributed Architecture)

This project is a distributed RTS battle simulator where the network logic (written in C) and the game engine/AI (written in Python) operate as separate processes.
🚀 How to Run

To start the simulation, you must launch both the network process and the game client.


1. Launch the Network Coordinator (C)

This process manages network communication with other players and also with the internal Python process.
cd reseau
make
./IPC
What to expect:

   . The program will display your local IP addresses to help other player to join you.

   .It will ask you: Voulez-vous rejoindre une partie existante ? (o/n). Follow the prompt to either join a session or start a new one.


   
2. Launch the AI Game Client (Python)

In a new terminal, launch the Python client to start the game.

# Ensure you are in the src directory
python3 Main.py run <AI_Name>

What to expect:

  .Once you get an ID , you will be prompted to choose a scenario (default) or in src/Constant.py to start the battle.

  .The simulation will then begin with the chosen AI strategy.
