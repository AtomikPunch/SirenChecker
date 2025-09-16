import requests
import json
import time
from datetime import datetime, date

# Configuration
API_KEY = "932b9388-e2b4-4beb-ab93-88e2b41beb8d"
BASE_URL = "https://api.insee.fr/api-sirene/3.11/siret"
MAX_REQUESTS_PER_MINUTE = 30
MAX_ETABLISSEMENTS_PER_REQUEST = 1000
DELAY_BETWEEN_REQUESTS = 8  # 8 secondes entre chaque requête (temps moyen d'une requête)

def lire_sirens():
    """Lit les numéros SIREN depuis le fichier Siren.txt"""
    sirens = []
    with open("Siren.txt", "r") as fichier:
        for ligne in fichier:
            siren = ligne.strip()
            if siren:  # Ignore les lignes vides
                sirens.append(siren)
    return sirens

def filtrer_etablissements_recents(data):
    """Filtre les établissements créés entre le 1er décembre 2024 et aujourd'hui"""
    if not data or 'etablissements' not in data:
        return []
    
    etablissements_recents = []
    date_debut = date(2024, 12, 1)  # 1er décembre 2024
    aujourd_hui = date.today()  # Aujourd'hui
    
    for etablissement in data['etablissements']:
        date_creation = etablissement.get('dateCreationEtablissement')
        if date_creation:
            try:
                # Convertir la date de création (format YYYY-MM-DD)
                date_creation_obj = datetime.strptime(date_creation, '%Y-%m-%d').date()
                
                # Vérifier si l'établissement a été créé entre le 1er décembre 2024 et aujourd'hui
                if date_debut <= date_creation_obj <= aujourd_hui:
                    etablissements_recents.append(etablissement)
            except ValueError:
                # Ignorer les dates mal formatées
                continue
    
    return etablissements_recents

def appel_api_page(siren, debut=0, nombre=1000):
    """Fait un appel API pour une page spécifique d'établissements avec respect des limites"""
    url = f"{BASE_URL}?debut={debut}&nombre={nombre}&q=siren:{siren}"
    headers = {
        "X-INSEE-Api-Key-Integration": API_KEY
    }
    
    try:
        # Attendre avant chaque requête pour respecter la limite de 30/min
        time.sleep(DELAY_BETWEEN_REQUESTS)
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return None

def appel_api_siren_complet(siren):
    """Récupère TOUS les établissements d'un SIREN en respectant les limites API"""
    print(f"  📡 Premier appel pour SIREN {siren}...")
    
    # Premier appel pour connaître le total (1000 max par requête)
    data = appel_api_page(siren, debut=0, nombre=MAX_ETABLISSEMENTS_PER_REQUEST)
    if not data:
        return None
    
    total_etablissements = data.get('header', {}).get('total', 0)
    print(f"  📊 Total d'établissements trouvés: {total_etablissements}")
    
    if total_etablissements == 0:
        return {
            'siren': siren,
            'total_etablissements': 0,
            'etablissements_recents': [],
            'nombre_recents': 0
        }
    
    # Collecter tous les établissements
    tous_etablissements = data.get('etablissements', [])
    
    # Si il y a plus d'établissements, faire des appels supplémentaires par pages de 1000
    if total_etablissements > MAX_ETABLISSEMENTS_PER_REQUEST:
        debut = MAX_ETABLISSEMENTS_PER_REQUEST
        while debut < total_etablissements:
            print(f"  📡 Appel supplémentaire {debut+1}-{min(debut+MAX_ETABLISSEMENTS_PER_REQUEST, total_etablissements)}...")
            data_page = appel_api_page(siren, debut=debut, nombre=MAX_ETABLISSEMENTS_PER_REQUEST)
            if data_page:
                tous_etablissements.extend(data_page.get('etablissements', []))
            debut += MAX_ETABLISSEMENTS_PER_REQUEST
    
    print(f"  ✅ Récupéré {len(tous_etablissements)} établissements sur {total_etablissements}")
    
    # Filtrer les établissements récents
    etablissements_recents = filtrer_etablissements_recents({'etablissements': tous_etablissements})
    
    return {
        'siren': siren,
        'total_etablissements': len(tous_etablissements),
        'etablissements_recents': etablissements_recents,
        'nombre_recents': len(etablissements_recents)
    }

def main():
    print("Lecture des numéros SIREN...")
    sirens = lire_sirens()
    print(f"Trouvé {len(sirens)} numéros SIREN")
    
    print(f"\n⚠️  LIMITES API:")
    print(f"   - Maximum {MAX_REQUESTS_PER_MINUTE} requêtes par minute")
    print(f"   - Maximum {MAX_ETABLISSEMENTS_PER_REQUEST} établissements par requête")
    print(f"   - Délai de {DELAY_BETWEEN_REQUESTS}s entre chaque requête (temps moyen d'une requête)")
    print(f"   - Filtrage : établissements créés entre le 1er décembre 2024 et aujourd'hui")
    
    print("\nDébut des appels API...")
    tous_siret_recents = []
    
    for i, siren in enumerate(sirens, 1):
        print(f"\n[{i}/{len(sirens)}] Traitement SIREN: {siren}")
        
        resultat = appel_api_siren_complet(siren)
        if resultat:
            print(f"✓ Succès pour SIREN {siren} - {resultat['nombre_recents']} établissement(s) récent(s) sur {resultat['total_etablissements']} total")
            
            # Extraire seulement les SIRET des établissements récents
            siret_recents = [etab['siret'] for etab in resultat['etablissements_recents']]
            tous_siret_recents.extend(siret_recents)
            
        else:
            print(f"✗ Échec pour SIREN {siren}")
    
    # Sauvegarde de tous les SIRET récents dans un fichier texte
    if tous_siret_recents:
        with open("siret_recents_2024.txt", "w", encoding="utf-8") as f:
            for siret in tous_siret_recents:
                f.write(f"{siret}\n")
        
        print(f"\n🎉 Terminé ! {len(tous_siret_recents)} SIRET créé(s) entre le 1er décembre 2024 et aujourd'hui trouvé(s)")
        print("📁 Liste des SIRET sauvegardée dans 'siret_recents_2024.txt'")
    else:
        print("\n❌ Aucun établissement créé entre le 1er décembre 2024 et aujourd'hui trouvé")

if __name__ == "__main__":
    main()
