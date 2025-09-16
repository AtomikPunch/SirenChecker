# Script API SIREN

Script Python simple pour faire des appels API avec les numéros SIREN.

## Installation

1. Installez les dépendances :
```bash
pip install -r requirements.txt
```

## Utilisation

1. Assurez-vous que le fichier `Siren.txt` est dans le même dossier
2. Lancez le script :
```bash
python api_siren.py
```

## Résultats

Le script va :
- Lire tous les numéros SIREN du fichier `Siren.txt`
- Faire un appel API pour chaque numéro
- Sauvegarder les résultats dans des fichiers JSON séparés (`resultat_siren_XXXXXX.json`)

## Configuration

- Clé API : Déjà configurée dans le script
- URL API : `https://api.insee.fr/api-sirene/3.11/siret`
- Paramètres : `debut=0&nombre=10&q=siren:#SIREN`
