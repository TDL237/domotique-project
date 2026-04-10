# Domotique Project

## Description

Plateforme domotique composée de plusieurs micro-services permettant de piloter des objets connectés simulés (lampe, prise, thermostat) via une API REST. L'interface accepte des commandes en langage naturel.

## Architecture

| Service | Port | Rôle |
|---------|------|------|
| Redis | 6379 | Bus de messages |
| lamp-agent | 8001 | Gestion de la lampe |
| prise-agent | 8002 | Gestion de la prise |
| thermostat-agent | 8003 | Gestion du thermostat |
| coordinateur | - | Orchestration des commandes |
| interface-agent | 8005 | API utilisateur |

## Installation et démarrage

### Prérequis

- Docker Desktop installé

### Lancer la plateforme


docker compose up --build


Vérifier que tout fonctionne

docker ps

Vous devez voir 6 conteneurs en cours d'exécution..

Tester l'API

Via Swagger

Ouvrez votre navigateur : http://localhost:8005/docs

Via la ligne de commande

# Allumer la lampe

curl -X POST http://localhost:8005/command_ia -H "Content-Type: application/json" -d '{"texte":"allume la lampe"}'

# Éteindre la prise

curl -X POST http://localhost:8005/command_ia -H "Content-Type: application/json" -d '{"texte":"éteins la prise"}'

# Consulter le thermostat

curl -X POST http://localhost:8005/command_ia -H "Content-Type: application/json" -d '{"texte":"donne moi l état du thermostat"}'

# Changer la température

curl -X POST http://localhost:8005/command_ia -H "Content-Type: application/json" -d '{"texte":"mets le thermostat à 22 degrés"}'

Vérifier les états

curl http://localhost:8001/state
curl http://localhost:8002/state
curl http://localhost:8003/state
Structure du projet
text
domotique-project/
├── lamp-agent/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── prise-agent/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── thermostat-agent/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── coordinateur/
│   ├── coordinateur.py
│   ├── Dockerfile
│   └── requirements.txt
├── interface-agent/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
└── README.md

Technologies utilisées

Docker / Docker Compose

FastAPI

Redis Streams

Uvicorn

Python 3.11

Auteur : DARRYL LINUS / Pseudo GitHub (TDL237)

Projet réalisé dans le cadre d'un brief sur l'architecture micro-services et la domotique.

Date
Avril 2026
