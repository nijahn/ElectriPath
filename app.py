from flask import Flask, render_template, request, jsonify
import requests
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__)

API_KEY_ROUTE = '715a3b7b-0aa4-4829-9429-6ba3038dd58f'
ROUTING_SERVICE_URL = "https://graphhopper.com/api/1/route"
EV_CHARGING_CLIENT_ID = '673d0ac8bd45c1778cd88d28'
EV_CHARGING_APP_ID = '673d0ac8bd45c1778cd88d2a'
EV_CHARGING_ENDPOINT = 'https://api.chargetrip.io/graphql'

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
    global vehicles_info
    headers = {
        'x-client-id': EV_CHARGING_CLIENT_ID,
        'x-app-id': EV_CHARGING_APP_ID,
        'Authorization': f'Bearer {EV_CHARGING_CLIENT_ID}',
        'Content-Type': 'application/json'
    }
    response = requests.post(EV_CHARGING_ENDPOINT, json={'query': graphql_query_cars}, headers=headers)
    response.raise_for_status()
    vehicles_info = response.json().get('data', {}).get('vehicleList', [])

@app.route('/')
def home():
    retrieve_vehicle_data()
    return render_template('home.html', vehicles=vehicles_info)

@app.route('/calculate_route', methods=['POST'])
def calculate_route():
    origin_city = request.form['origin_city']
    destination_city = request.form['destination_city']
    car_id = request.form['car_id']

    selected_vehicle = next((car for car in vehicles_info if car['id'] == car_id), None)
    if not selected_vehicle:
        return jsonify({'error': 'Vehicle not found'}), 404

    car_specs = {
        'battery_capacity': selected_vehicle['battery']['usable_kwh'],
        'optimal_range': selected_vehicle['range']['chargetrip_range']['best'],
        'efficiency': selected_vehicle['battery']['usable_kwh'] / selected_vehicle['range']['chargetrip_range']['best']
    }

    start_coords = get_location_coordinates(origin_city)
    end_coords = get_location_coordinates(destination_city)
    if not start_coords or not end_coords:
        return jsonify({'error': 'Invalid coordinates'}), 400

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
    route_path = extract_route_coordinates(route_details)

    # Localiser les bornes de recharge
    charging_stations = locate_stations(route_path, 200, car_specs['efficiency'], selected_vehicle)

    # Ajouter les bornes dans l'itinéraire
    via_points = [f"{station['location']['coordinates'][1]},{station['location']['coordinates'][0]}" for station in charging_stations]
    if via_points:
        params['point'] = [f"{start_coords['lat']},{start_coords['lng']}"] + via_points + [f"{end_coords['lat']},{end_coords['lng']}"]

        # Recalculer l'itinéraire avec les points intermédiaires
        final_route_response = requests.get(ROUTING_SERVICE_URL, params=params)
        final_route_response.raise_for_status()
        route_details = final_route_response.json()
        route_path = extract_route_coordinates(route_details)

    duration_ms = route_details['paths'][0]['time']
    hours = duration_ms // 3600000
    minutes = (duration_ms % 3600000) // 60000

    return jsonify({
        'total_distance': f"{route_details['paths'][0]['distance'] / 1000:.2f} km",
        'travel_time': f"{hours}h {minutes}m",
        'route_path': route_path,
        'charging_stations': charging_stations,
        'car_specs': car_specs
    })

def get_location_coordinates(city_name):
    response = requests.get(f"https://graphhopper.com/api/1/geocode?q={city_name}&key={API_KEY_ROUTE}")
    response.raise_for_status()
    data = response.json()
    if data['hits']:
        return data['hits'][0]['point']
    return None

def extract_route_coordinates(route_response):
    if 'paths' not in route_response or not route_response['paths']:
        raise ValueError("No paths found in the route response")
    coordinates = route_response['paths'][0]['points']['coordinates']
    if not coordinates:
        raise ValueError("No coordinates found in the path")
    return [[point[1], point[0]] for point in coordinates]

def locate_stations(route_path, max_distance, efficiency, car_info):
    headers = {
        'x-client-id': EV_CHARGING_CLIENT_ID,
        'x-app-id': EV_CHARGING_APP_ID,
        'Authorization': f'Bearer {EV_CHARGING_CLIENT_ID}',
        'Content-Type': 'application/json'
    }
    stations = []
    current_distance = 0
    max_range = car_info['range']['chargetrip_range']['worst']

    for i in range(len(route_path) - 1):
        segment_distance = haversine_distance(route_path[i], route_path[i + 1])
        current_distance += segment_distance

        if current_distance >= max_range:
            station_location = route_path[i]
            query = f"""
            query {{
                stationAround(
                    filter: {{
                        location: {{ type: Point, coordinates: [{station_location[1]}, {station_location[0]}] }},
                        distance: 5000
                    }},
                    size: 1
                ) {{
                    id
                    name
                    location {{
                        coordinates
                    }}
                    power
                }}
            }}
            """
            response = requests.post(EV_CHARGING_ENDPOINT, json={'query': query}, headers=headers)
            if response.status_code == 200:
                station_data = response.json().get('data', {}).get('stationAround', [])
                if station_data:
                    stations.append(station_data[0])
                    current_distance = 0

    return stations

def haversine_distance(coord1, coord2):
    if not coord1 or not coord2 or len(coord1) != 2 or len(coord2) != 2:
        raise ValueError("Invalid coordinates provided for haversine calculation")

    R = 6371
    dlat = radians(coord2[0] - coord1[0])
    dlon = radians(coord2[1] - coord1[1])
    a = sin(dlat / 2)**2 + cos(radians(coord1[0])) * cos(radians(coord2[0])) * sin(dlon / 2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

if __name__ == '__main__':
    app.run(debug=True)
