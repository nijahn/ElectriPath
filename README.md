# ElectriPath

ElectriPath est une application web qui aide les utilisateurs de véhicules électriques à planifier leurs trajets en tenant compte des bornes de recharge disponibles. L'application calcule un itinéraire optimisé en fonction des véhicules et affiche une carte interactive avec les points de recharge.

## Fonctionnalités

- Planification d'un itinéraire entre deux villes.
- Prise en compte de l'autonomie du véhicule électrique pour localiser les bornes de recharge nécessaires.
- Affichage dynamique de l'itinéraire, des bornes de recharge et des informations (distance, durée).
- Récupération des données via des API REST et GraphQL :
  - **GraphHopper** : Calcul des itinéraires et géocodage des villes.
  - **Chargetrip** : Données des véhicules électriques et des stations de recharge.

## Architecture

- **Backend** : Flask
  - Gestion des routes et appels aux API REST/GraphQL.
  - Manipulation des données JSON pour le frontend.
- **Frontend** : HTML, JavaScript, CSS
  - Interface utilisateur interactive.
  - Intégration avec Leaflet pour la carte.


## Prérequis

- **Python 3.9+**
- **pip** : Gestionnaire de packages Python
- **Clés API** :
  - Une clé API GraphHopper pour le calcul d'itinéraires.
  - Identifiants API Chargetrip pour les données des véhicules et des bornes.

## Installation

1. Clonez le dépôt :
   ```bash
   git clone https://github.com/votre-repo/electripath.git
   cd electripath
