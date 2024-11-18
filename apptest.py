from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

GRAPHOPPER_API_KEY = '1395718d-379c-452b-b1c7-538e1a5a7a68'
GRAPHOPPER_URL = "https://graphhopper.com/api/1/route"
CHARGETRIP_CLIENT_KEY = '6710ba84021ae871189270f5'
CHARGETRIP_APP_KEY = '6710ba84021ae871189270f7'
CHARGETRIP_URL = 'https://api.chargetrip.io/graphql'

# Variable globale pour stocker les données des véhicules
vehicles_data = []

graphql_query_vehicles = """
query vehicleListAll {
  vehicleList {
    id
    naming {
      make
      model
    }
    range {
      chargetrip_range {
        best
        worst
      }
    }
    battery {
      usable_kwh
      full_kwh
    }
  }
}
"""

def fetch_vehicles_data():
    global vehicles_data
    headers = {
        'x-client-id': CHARGETRIP_CLIENT_KEY,
        'x-app-id': CHARGETRIP_APP_KEY,
        'Authorization': f'Bearer {CHARGETRIP_CLIENT_KEY}',
        'Content-Type': 'application/json'
    }
    response = requests.post(CHARGETRIP_URL, json={'query': graphql_query_vehicles}, headers=headers)
    if response.status_code == 200:
        vehicles_data = response.json()['data']['vehicleList']
    else:
        vehicles_data = []

@app.route('/')
def index():
    try:
        fetch_vehicles_data()  # Récupérer les données des véhicules à chaque fois que l'on accède à l'index
        return render_template('index.html', vehicles=vehicles_data)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/route_data', methods=['POST'])
def route_data():
    ville_depart = request.form['start_city']
    ville_arrivee = request.form['end_city']
    vehicule_id = request.form['vehicle_id']

    try:
        # Récupérer l'autonomie de la voiture sélectionnée
        vehicle_autonomy = None
        for vehicle in vehicles_data:  # Utiliser les données globales
            if vehicle['id'] == vehicule_id:
                # Vérifiez si l'attribut 'battery' existe
                if 'range' in vehicle and 'chargetrip_range' in vehicle['range']:
                    vehicle_autonomy = vehicle['range']['chargetrip_range']['best']  # Utiliser la meilleure autonomie
                break

        if vehicle_autonomy is None:
            return jsonify({'error': 'Vehicle not found or battery data unavailable'}), 404

        # Requête pour obtenir les coordonnées du point de départ
        response = requests.get(f"https://graphhopper.com/api/1/geocode?q={ville_depart}&key={GRAPHOPPER_API_KEY}")
        start_data = response.json()
        coords_depart = start_data['hits'][0]['point']

        # Requête pour obtenir les coordonnées du point d'arrivée
        response = requests.get(f"https://graphhopper.com/api/1/geocode?q={ville_arrivee}&key={GRAPHOPPER_API_KEY}")
        end_data = response.json()
        coords_arrivee = end_data['hits'][0]['point']

        # Interroger GraphHopper pour l'itinéraire
        params = {
            'point': [f"{coords_depart['lat']},{coords_depart['lng']}", f"{coords_arrivee['lat']},{coords_arrivee['lng']}"],
            'vehicle': 'car',
            'key': GRAPHOPPER_API_KEY,
            'instructions': 'false',
            'points_encoded': 'false'
        }

        response = requests.get(GRAPHOPPER_URL, params=params)
        route_data = response.json()

        geometrie_itineraire = route_data['paths'][0]['points']['coordinates']
        distance_totale = route_data['paths'][0]['distance'] / 1000  # en km
        duree_minutes = route_data['paths'][0]['time'] / 60000  # en minutes

        # Conversion en heures et minutes
        heures = int(duree_minutes // 60)  # Nombre d'heures
        minutes = int(duree_minutes % 60)   # Nombre de minutes

        # Convertir les points en lat-lng pour Leaflet
        coords_itineraire = [[coord[1], coord[0]] for coord in geometrie_itineraire]

        return jsonify({
            'distance': f"{distance_totale:.2f} km",
            'duration': f"{heures} heures {minutes} minutes",  # Afficher la durée en heures et minutes
            'route': coords_itineraire
        })

    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
