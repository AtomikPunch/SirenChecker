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
    """Filtre les établissements créés OU fermés entre le 1er décembre 2024 et aujourd'hui"""
    if not data or 'etablissements' not in data:
        return {'ouverts': [], 'fermes': []}
    
    etablissements_ouverts = []
    etablissements_fermes = []
    date_debut = date(2024, 12, 1)  # 1er décembre 2024
    aujourd_hui = date.today()  # Aujourd'hui
    
    for etablissement in data['etablissements']:
        est_ouvert_recent = False
        est_ferme_recent = False
        
        # 1. Vérifier la date de création (établissement ouvert récent)
        date_creation = etablissement.get('dateCreationEtablissement')
        if date_creation:
            try:
                date_creation_obj = datetime.strptime(date_creation, '%Y-%m-%d').date()
                if date_debut <= date_creation_obj <= aujourd_hui:
                    est_ouvert_recent = True
            except ValueError:
                pass
        
        # 2. Vérifier les périodes de fermeture (établissement fermé récent)
        periodes = etablissement.get('periodesEtablissement', [])
        for periode in periodes:
            if periode.get('etatAdministratifEtablissement') == 'F':
                date_fermeture = periode.get('dateDebut')
                if date_fermeture:
                    try:
                        date_fermeture_obj = datetime.strptime(date_fermeture, '%Y-%m-%d').date()
                        if date_debut <= date_fermeture_obj <= aujourd_hui:
                            est_ferme_recent = True
                            break
                    except ValueError:
                        continue
        
        # Ajouter à la liste appropriée
        if est_ouvert_recent:
            etablissements_ouverts.append(etablissement)
        if est_ferme_recent:
            etablissements_fermes.append(etablissement)
    
    return {
        'ouverts': etablissements_ouverts,
        'fermes': etablissements_fermes
    }

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
            'etablissements_recents': {'ouverts': [], 'fermes': []},
            'nombre_ouverts': 0,
            'nombre_fermes': 0
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
        'nombre_ouverts': len(etablissements_recents['ouverts']),
        'nombre_fermes': len(etablissements_recents['fermes'])
    }

def main():
    print("Lecture des numéros SIREN...")
    sirens = lire_sirens()
    print(f"Trouvé {len(sirens)} numéros SIREN")
    
    print(f"\n⚠️  LIMITES API:")
    print(f"   - Maximum {MAX_REQUESTS_PER_MINUTE} requêtes par minute")
    print(f"   - Maximum {MAX_ETABLISSEMENTS_PER_REQUEST} établissements par requête")
    print(f"   - Délai de {DELAY_BETWEEN_REQUESTS}s entre chaque requête (temps moyen d'une requête)")
    print(f"   - Filtrage : établissements créés OU fermés entre le 1er décembre 2024 et aujourd'hui")
    
    print("\nDébut des appels API...")
    tous_siret_ouverts = []
    tous_siret_fermes = []
    
    for i, siren in enumerate(sirens, 1):
        print(f"\n[{i}/{len(sirens)}] Traitement SIREN: {siren}")
        
        resultat = appel_api_siren_complet(siren)
        if resultat:
            print(f"✓ Succès pour SIREN {siren} - {resultat['nombre_ouverts']} ouvert(s) + {resultat['nombre_fermes']} fermé(s) sur {resultat['total_etablissements']} total")
            
            # Extraire les SIRET des établissements ouverts et fermés
            siret_ouverts = [etab['siret'] for etab in resultat['etablissements_recents']['ouverts']]
            siret_fermes = [etab['siret'] for etab in resultat['etablissements_recents']['fermes']]
            
            tous_siret_ouverts.extend(siret_ouverts)
            tous_siret_fermes.extend(siret_fermes)
            
        else:
            print(f"✗ Échec pour SIREN {siren}")
    
    # Sauvegarde dans un fichier CSV unique
    if tous_siret_ouverts or tous_siret_fermes:
        with open("siret_recents_2024.csv", "w", encoding="utf-8") as f:
            # En-tête CSV
            f.write("SIRET,STATUT\n")
            
            # SIRET ouverts avec statut A
            for siret in tous_siret_ouverts:
                f.write(f"{siret},A\n")
            
            # SIRET fermés avec statut F
            for siret in tous_siret_fermes:
                f.write(f"{siret},F\n")
        
        print(f"\n📁 {len(tous_siret_ouverts)} SIRET ouverts + {len(tous_siret_fermes)} SIRET fermés sauvegardés dans 'siret_recents_2024.csv'")
    
    total_recents = len(tous_siret_ouverts) + len(tous_siret_fermes)
    if total_recents > 0:
        print(f"\n🎉 Terminé ! {total_recents} SIRET récents trouvés ({len(tous_siret_ouverts)} ouverts + {len(tous_siret_fermes)} fermés)")
        print("📊 Format CSV : SIRET,STATUT (A=ouvert, F=fermé)")
    else:
        print("\n❌ Aucun établissement créé ou fermé entre le 1er décembre 2024 et aujourd'hui trouvé")

if __name__ == "__main__":
    main()
