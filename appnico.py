from flask import Flask, render_template, request, jsonify
import requests

application = Flask(__name__)

API_KEY_ROUTE = '715a3b7b-0aa4-4829-9429-6ba3038dd58f'
ROUTING_SERVICE_URL = "https://graphhopper.com/api/1/route"
EV_CHARGING_CLIENT_ID = '673a3742aad68b4b27a41e79'
EV_CHARGING_APP_ID = '673a3742aad68b4b27a41e7b'
EV_CHARGING_ENDPOINT = 'https://api.chargetrip.io/graphql'

# Liste pour stocker les informations sur les véhicules
vehicles_info = []

graphql_query_cars = """
query fetchAllVehicles {
  vehicleList {
    id
    naming {
      make
      model
      version
      edition
      chargetrip_version
    }
    drivetrain {
      type
    }
    connectors {
      standard
      power
      max_electric_power
      time
      speed
    }
    battery {
      usable_kwh
      full_kwh
    }
    range {
      chargetrip_range {
        best
        worst
      }
    }
  }
}
"""

def retrieve_vehicle_data():
    global vehicles_info, EV_CHARGING_CLIENT_ID, EV_CHARGING_APP_ID
    headers = {
        'x-client-id': EV_CHARGING_CLIENT_ID,
        'x-app-id': EV_CHARGING_APP_ID,
        'Authorization': f'Bearer {EV_CHARGING_CLIENT_ID}',
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(EV_CHARGING_ENDPOINT, json={'query': graphql_query_cars}, headers=headers)
        response.raise_for_status()
        vehicles_info = response.json().get('data', {}).get('vehicleList', [])
    except requests.RequestException as error:
        print(f"Erreur lors de la récupération des données des véhicules : {error}")
        vehicles_info = []

@application.route('/')
def home():
    try:
        retrieve_vehicle_data()
        return render_template('home.html', vehicles=vehicles_info)
    except Exception as error:
        return jsonify({'error': str(error)})

@application.route('/calculate_route', methods=['POST'])
def calculate_route():
    origin_city = request.form['origin_city']
    destination_city = request.form['destination_city']
    car_id = request.form['car_id']

    try:
        # Obtenir les informations du véhicule sélectionné
        selected_vehicle = next((car for car in vehicles_info if car['id'] == car_id), None)
        if not selected_vehicle:
            return jsonify({'error': 'Selected vehicle not found'}), 404

        # Extraire les spécifications du véhicule
        car_specs = {
            'battery_capacity': selected_vehicle['battery']['usable_kwh'],
            'optimal_range': selected_vehicle['range']['chargetrip_range']['best'],
            'efficiency': selected_vehicle['battery']['usable_kwh'] / selected_vehicle['range']['chargetrip_range']['best']
        }

        # Obtenir les coordonnées des villes d'origine et de destination
        start_coords = get_location_coordinates(origin_city)
        end_coords = get_location_coordinates(destination_city)

        if not start_coords or not end_coords:
            return jsonify({'error': 'Unable to fetch coordinates'}), 400

        # Planifier l'itinéraire
        params = {
            'point': [f"{start_coords['lat']},{start_coords['lng']}", f"{end_coords['lat']},{end_coords['lng']}"],
            'vehicle': 'car',
            'key': API_KEY_ROUTE,
            'instructions': 'false',
            'points_encoded': 'false'
        }
        initial_route_response = requests.get(ROUTING_SERVICE_URL, params=params)
        initial_route_response.raise_for_status()

        route_details = initial_route_response.json()
        route_coords = extract_route_coordinates(route_details)

        # Identifier les stations de recharge
        charging_stations = locate_stations(route_coords, 200, car_specs['efficiency'], selected_vehicle)

        print(f"DEBUG: Stations de recharge trouvées : {charging_stations}")

        # Calculer la durée du trajet
        total_duration_ms = route_details['paths'][0]['time']
        duration_hours = total_duration_ms // 3600000
        duration_minutes = (total_duration_ms % 3600000) // 60000

        return jsonify({
            'total_distance': f"{route_details['paths'][0]['distance'] / 1000:.2f} km",
            'travel_time': f"{duration_hours}h {duration_minutes}m",
            'route_path': route_coords,
            'charging_stations': charging_stations,
            'car_specs': car_specs
        })
    except Exception as error:
        print(f"Erreur lors du calcul de l'itinéraire : {error}")
        return jsonify({'error': str(error)})

def get_location_coordinates(city_name):
    try:
        response = requests.get(f"https://graphhopper.com/api/1/geocode?q={city_name}&key={API_KEY_ROUTE}")
        response.raise_for_status()
        data = response.json()
        if data['hits']:
            return data['hits'][0]['point']
        return None
    except requests.RequestException:
        return None

def extract_route_coordinates(route_response):
    return [[point[1], point[0]] for point in route_response['paths'][0]['points']['coordinates']]

def locate_stations(route_path, max_distance, efficiency, car_info):
    global EV_CHARGING_CLIENT_ID, EV_CHARGING_APP_ID
    try:
        print(f"DEBUG: Début de la recherche de stations.")
        stations = []  # Simulation ou logique réelle pour récupérer les stations
        print(f"DEBUG: Stations trouvées : {stations}")
        return stations
    except Exception as error:
        print(f"Erreur lors de la recherche des stations : {error}")
        return []

if __name__ == '__main__':
    application.run(debug=True)
