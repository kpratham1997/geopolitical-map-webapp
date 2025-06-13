import os
import json
from flask import Flask, render_template, request, jsonify, url_for, session
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
from shapely.geometry import Point, MultiPolygon, Polygon
import shutil # For clearing static directory
import numpy as np # For numerical operations in coordinate conversion

app = Flask(__name__)
# Set a secret key for session management.
# IMPORTANT: In a real application, this should be a strong, random key
# and ideally loaded from an environment variable, not hardcoded.
app.secret_key = 'your_super_secret_and_complex_key_here_12345' 

# Define the path for static files (e.g., generated map image)
STATIC_FOLDER = os.path.join(os.path.dirname(__file__), 'static')
if not os.path.exists(STATIC_FOLDER):
    os.makedirs(STATIC_FOLDER)

# Define the path for templates
TEMPLATES_FOLDER = os.path.join(os.path.dirname(__file__), 'templates')
if not os.path.exists(TEMPLATES_FOLDER):
    os.makedirs(TEMPLATES_FOLDER)

app.template_folder = TEMPLATES_FOLDER

# Geopolitical data (kept the same as previous versions)
geopolitical_data = {
    # North America
    "USA": {"name": "United States", "allies": ["CAN", "GBR", "AUS", "JPN", "KOR", "DEU", "FRA", "MEX", "COL", "CHL"], "enemies": ["PRK", "IRN", "RUS", "CHN", "VEN", "CUB"]},
    "CAN": {"name": "Canada", "allies": ["USA", "GBR", "AUS", "JPN", "KOR", "DEU", "FRA"], "enemies": []},
    "MEX": {"name": "Mexico", "allies": ["USA", "CAN", "BRA", "COL"], "enemies": []},
    "CUB": {"name": "Cuba", "allies": ["RUS", "CHN", "VEN", "PRK"], "enemies": ["USA"]},
    # South America
    "BRA": {"name": "Brazil", "allies": ["ARG", "MEX", "ZAF", "IND", "CHN", "RUS"], "enemies": []}, # BRICS
    "ARG": {"name": "Argentina", "allies": ["BRA", "CHL", "USA"], "enemies": []},
    "COL": {"name": "Colombia", "allies": ["USA", "PAN", "CHL"], "enemies": ["VEN"]},
    "CHL": {"name": "Chile", "allies": ["USA", "ARG", "BRA"], "enemies": []},
    "VEN": {"name": "Venezuela", "allies": ["CUB", "RUS", "CHN", "IRN"], "enemies": ["USA", "COL"]},
    # Europe
    "GBR": {"name": "United Kingdom", "allies": ["USA", "CAN", "AUS", "DEU", "FRA", "ITA", "ESP"], "enemies": []},
    "DEU": {"name": "Germany", "allies": ["FRA", "USA", "GBR", "ITA", "ESP", "POL"], "enemies": ["RUS"]},
    "FRA": {"name": "France", "allies": ["DEU", "USA", "GBR", "ITA", "ESP", "IND"], "enemies": []},
    "ITA": {"name": "Italy", "allies": ["DEU", "FRA", "USA"], "enemies": []},
    "ESP": {"name": "Spain", "allies": ["FRA", "DEU", "USA"], "enemies": []},
    "POL": {"name": "Poland", "allies": ["USA", "DEU", "UKR"], "enemies": ["RUS", "BLR"]},
    "UKR": {"name": "Ukraine", "allies": ["USA", "GBR", "DEU", "FRA", "POL"], "enemies": ["RUS"]},
    "RUS": {"name": "Russian Federation", "allies": ["CHN", "BLR", "IRN", "PRK", "SYR"], "enemies": ["USA", "UKR", "DEU", "GBR", "FRA", "POL"]},
    "BLR": {"name": "Belarus", "allies": ["RUS"], "enemies": ["POL", "UKR"]},
    "GRC": {"name": "Greece", "allies": ["CYP", "USA", "FRA", "DEU"], "enemies": ["TUR"]},
    "CYP": {"name": "Cyprus", "allies": ["GRC", "FRA", "ISR", "EGY"], "enemies": ["TUR"]},
    "TUR": {"name": "Turkey", "allies": ["AZE", "QAT", "SOM", "UKR"], "enemies": ["GRC", "CYP", "ARM", "SYR", "SAU", "ARE"]}, # Added specific rivals
    "ARM": {"name": "Armenia", "allies": ["RUS", "FRA", "GRC"], "enemies": ["AZE", "TUR"]},
    "AZE": {"name": "Azerbaijan", "allies": ["TUR", "ISR", "PAK"], "enemies": ["ARM", "IRN"]},
    "SWE": {"name": "Sweden", "allies": ["FIN", "NOR", "DNK"], "enemies": []},
    "FIN": {"name": "Finland", "allies": ["SWE", "NOR", "DNK"], "enemies": ["RUS"]},
    "NOR": {"name": "Norway", "allies": ["SWE", "FIN", "DNK"], "enemies": []},
    "DNK": {"name": "Denmark", "allies": ["SWE", "FIN", "NOR"], "enemies": []},
    "CHE": {"name": "Switzerland", "allies": [], "enemies": []}, # Neutral
    "AUT": {"name": "Austria", "allies": [], "enemies": []}, # EU, but traditionally neutral
    "NLD": {"name": "Netherlands", "allies": ["DEU", "GBR", "USA"], "enemies": []},
    "BEL": {"name": "Belgium", "allies": ["DEU", "FRA", "NLD"], "enemies": []},
    "PRT": {"name": "Portugal", "allies": ["USA", "GBR"], "enemies": []},
    "IRL": {"name": "Ireland", "allies": ["GBR"], "enemies": []},
    "LUX": {"name": "Luxembourg", "allies": ["BEL", "FRA", "DEU"], "enemies": []},
    "MLT": {"name": "Malta", "allies": [], "enemies": []},
    "ISL": {"name": "Iceland", "allies": ["USA", "NOR"], "enemies": []},
    "GEO": {"name": "Georgia", "allies": ["USA", "UKR"], "enemies": ["RUS"]},
    "MDA": {"name": "Moldova", "allies": ["ROU", "UKR"], "enemies": ["RUS"]},
    "ROU": {"name": "Romania", "allies": ["USA", "DEU"], "enemies": []},
    "SVK": {"name": "Slovakia", "allies": ["CZE", "DEU"], "enemies": []},
    "CZE": {"name": "Czechia", "allies": ["SVK", "DEU"], "enemies": []},
    "HUN": {"name": "Hungary", "allies": [], "enemies": []},
    "BGR": {"name": "Bulgaria", "allies": [], "enemies": []},
    "HRV": {"name": "Croatia", "allies": [], "enemies": []},
    "SVN": {"name": "Slovenia", "allies": [], "enemies": []},
    "SRB": {"name": "Serbia", "allies": ["RUS", "CHN"], "enemies": ["KOS", "ALB"]},
    "KOS": {"name": "Kosovo", "allies": ["USA", "ALB", "DEU"], "enemies": ["SRB"]},
    "ALB": {"name": "Albania", "allies": ["USA", "KOS"], "enemies": ["SRB"]},
    "BIH": {"name": "Bosnia and Herzegovina", "allies": [], "enemies": ["SRB"]},
    "MNE": {"name": "Montenegro", "allies": [], "enemies": []},
    "MKD": {"name": "North Macedonia", "allies": [], "enemies": []},
    "EST": {"name": "Estonia", "allies": ["USA", "FIN", "LVA", "LTU"], "enemies": ["RUS"]},
    "LVA": {"name": "Latvia", "allies": ["USA", "EST", "LTU"], "enemies": ["RUS"]},
    "LTU": {"name": "Lithuania", "allies": ["USA", "EST", "LVA"], "enemies": ["RUS"]},
    # Middle East & North Africa
    "ISR": {"name": "Israel", "allies": ["USA", "IND", "ARE", "BHR", "MAR", "SDN"], "enemies": ["IRN", "LBN", "PSE", "SYR"]},
    "IRN": {"name": "Iran", "allies": ["RUS", "CHN", "SYR", "PRK"], "enemies": ["USA", "ISR", "SAU", "ARE", "AZE"]},
    "SAU": {"name": "Saudi Arabia", "allies": ["USA", "GBR", "ARE", "BHR", "EGY", "PAK", "QAT"], "enemies": ["IRN"]},
    "ARE": {"name": "United Arab Emirates", "allies": ["USA", "SAU", "ISR"], "enemies": ["IRN", "QAT"]},
    "QAT": {"name": "Qatar", "allies": ["USA", "TUR", "IRN"], "enemies": ["SAU", "ARE", "BHR", "EGY"]},
    "SYR": {"name": "Syria", "allies": ["RUS", "IRN"], "enemies": ["ISR", "TUR", "USA"]},
    "EGY": {"name": "Egypt", "allies": ["USA", "SAU", "ARE", "JOR", "ISR"], "enemies": []},
    "PAK": {"name": "Pakistan", "allies": ["CHN", "TUR", "SAU"], "enemies": ["IND", "AFG"]},
    "AFG": {"name": "Afghanistan", "allies": ["CHN", "PAK"], "enemies": ["PAK"]},
    "LBN": {"name": "Lebanon", "allies": ["FRA"], "enemies": ["ISR", "SYR"]},
    "JOR": {"name": "Jordan", "allies": ["USA", "GBR", "SAU", "EGY"], "enemies": []},
    "IRQ": {"name": "Iraq", "allies": ["USA", "IRN"], "enemies": ["ISIS", "TUR"]},
    "DZA": {"name": "Algeria", "allies": ["RUS", "CHN"], "enemies": ["MAR"]},
    "MAR": {"name": "Morocco", "allies": ["USA", "FRA", "ISR"], "enemies": ["DZA"]},
    "KWT": {"name": "Kuwait", "allies": ["USA", "SAU"], "enemies": ["IRN"]},
    "OMN": {"name": "Oman", "allies": ["GBR", "USA"], "enemies": []},
    "BHR": {"name": "Bahrain", "allies": ["USA", "SAU", "ARE", "ISR"], "enemies": ["IRN"]},
    "YEM": {"name": "Yemen", "allies": ["SAU"], "enemies": ["IRN"]},
    "SDN": {"name": "Sudan", "allies": ["EGY", "SAU", "ARE"], "enemies": []},
    "LBY": {"name": "Libya", "allies": ["TUR"], "enemies": ["EGY", "RUS"]},
    "TUN": {"name": "Tunisia", "allies": ["FRA"], "enemies": []},
    "MRT": {"name": "Mauritania", "allies": ["FRA"], "enemies": []},

    # Asia-Pacific
    "CHN": {"name": "China", "allies": ["RUS", "PRK", "PAK", "IRN", "LAO", "KHM"], "enemies": ["USA", "IND", "JPN", "KOR", "TWN", "AUS", "PHL", "VNM"]},
    "IND": {"name": "India", "allies": ["USA", "RUS", "FRA", "JPN", "AUS", "ISR"], "enemies": ["PAK", "CHN"]},
    "JPN": {"name": "Japan", "allies": ["USA", "AUS", "IND", "KOR"], "enemies": ["CHN", "PRK", "RUS"]},
    "KOR": {"name": "South Korea", "allies": ["USA", "JPN"], "enemies": ["PRK", "CHN"]},
    "PRK": {"name": "North Korea", "allies": ["CHN", "RUS", "IRN"], "enemies": ["USA", "KOR", "JPN"]},
    "AUS": {"name": "Australia", "allies": ["USA", "GBR", "JPN", "IND", "NZL"], "enemies": ["CHN"]},
    "NZL": {"name": "New Zealand", "allies": ["AUS", "USA", "GBR"], "enemies": []},
    "PHL": {"name": "Philippines", "allies": ["USA", "JPN", "AUS"], "enemies": ["CHN"]},
    "VNM": {"name": "Vietnam", "allies": ["USA", "RUS"], "enemies": ["CHN"]},
    "IDN": {"name": "Indonesia", "allies": ["AUS", "MYS", "SGP"], "enemies": []},
    "MYS": {"name": "Malaysia", "allies": ["IDN", "SGP", "GBR"], "enemies": []},
    "SGP": {"name": "Singapore", "allies": ["IDN", "MYS", "USA"], "enemies": []},
    "THA": {"name": "Thailand", "allies": ["USA", "JPN"], "enemies": []},
    "LAO": {"name": "Laos", "allies": ["CHN", "VNM"], "enemies": []},
    "KHM": {"name": "Cambodia", "allies": ["CHN", "VNM"], "enemies": []},
    "TWN": {"name": "Taiwan", "allies": ["USA", "JPN"], "enemies": ["CHN"]},
    "KAZ": {"name": "Kazakhstan", "allies": ["RUS", "CHN"], "enemies": []},
    "UZB": {"name": "Uzbekistan", "allies": ["RUS", "CHN"], "enemies": []},
    "TKM": {"name": "Turkmenistan", "allies": [], "enemies": []},
    "KGZ": {"name": "Kyrgyzstan", "allies": ["RUS", "CHN"], "enemies": []},
    "TJK": {"name": "Tajikistan", "allies": ["RUS", "CHN"], "enemies": []},
    "LKA": {"name": "Sri Lanka", "allies": ["IND", "CHN"], "enemies": []},
    "MDV": {"name": "Maldives", "allies": ["IND", "CHN"], "enemies": []},
    "BGD": {"name": "Bangladesh", "allies": ["IND", "CHN"], "enemies": []},
    "NPL": {"name": "Nepal", "allies": ["IND", "CHN"], "enemies": []},
    "BTN": {"name": "Bhutan", "allies": ["IND"], "enemies": []},
    "MMR": {"name": "Myanmar", "allies": ["CHN", "RUS"], "enemies": []},
    "PNG": {"name": "Papua New Guinea", "allies": ["AUS", "USA"], "enemies": []},
    "FJI": {"name": "Fiji", "allies": ["AUS", "NZL"], "enemies": []},
    "KIR": {"name": "Kiribati", "allies": ["AUS", "NZL"], "enemies": []},
    "SLB": {"name": "Solomon Islands", "allies": ["AUS", "CHN"], "enemies": ["CHN"]},
    "VUT": {"name": "Vanuatu", "allies": ["AUS", "NZL"], "enemies": []},
    "WSM": {"name": "Samoa", "allies": ["AUS", "NZL"], "enemies": []},
    "TUV": {"name": "Tuvalu", "allies": ["AUS", "NZL"], "enemies": []},
    "MHL": {"name": "Marshall Islands", "allies": ["USA"], "enemies": []},
    "FSM": {"name": "Micronesia (Federated States of)", "allies": ["USA"], "enemies": []},
    "PLW": {"name": "Palau", "allies": ["USA"], "enemies": []},

    # Africa
    "ZAF": {"name": "South Africa", "allies": ["BRA", "IND", "CHN", "RUS"], "enemies": []},
    "NGA": {"name": "Nigeria", "allies": ["USA", "GBR", "FRA"], "enemies": []},
    "ETH": {"name": "Ethiopia", "allies": ["CHN", "RUS"], "enemies": ["ERI", "SOM"]},
    "ERI": {"name": "Eritrea", "allies": [], "enemies": ["ETH"]},
    "KEN": {"name": "Kenya", "allies": ["USA", "GBR"], "enemies": ["SOM"]},
    "SOM": {"name": "Somalia", "allies": ["TUR", "QAT", "ETH"], "enemies": ["ETH", "KEN"]},
    "MLI": {"name": "Mali", "allies": ["RUS"], "enemies": ["FRA"]},
    "NER": {"name": "Niger", "allies": ["RUS"], "enemies": ["FRA"]},
    "BFA": {"name": "Burkina Faso", "allies": ["RUS"], "enemies": ["FRA"]},
    "CIV": {"name": "Cote d'Ivoire", "allies": ["FRA"], "enemies": []},
    "GHA": {"name": "Ghana", "allies": ["GBR", "USA"], "enemies": []},
    "CMR": {"name": "Cameroon", "allies": ["FRA"], "enemies": []},
    "GAB": {"name": "Gabon", "allies": ["FRA"], "enemies": []},
    "COD": {"name": "Dem. Rep. Congo", "allies": ["BEL", "USA"], "enemies": ["RWA"]},
    "RWA": {"name": "Rwanda", "allies": ["GBR", "USA"], "enemies": ["COD"]},
    "UGA": {"name": "Uganda", "allies": ["USA"], "enemies": []},
    "TZA": {"name": "Tanzania", "allies": ["CHN"], "enemies": []},
    "MOZ": {"name": "Mozambique", "allies": ["CHN"], "enemies": []},
    "MDG": {"name": "Madagascar", "allies": ["FRA"], "enemies": []},
    "COM": {"name": "Comoros", "allies": ["FRA"], "enemies": []},
    "SYC": {"name": "Seychelles", "allies": ["IND"], "enemies": []},
    "MUS": {"name": "Mauritius", "allies": ["IND"], "enemies": []},
    "NAM": {"name": "Namibia", "allies": ["CHN"], "enemies": []},
    "BWA": {"name": "Botswana", "allies": ["ZAF"], "enemies": []},
    "AGO": {"name": "Angola", "allies": ["CHN"], "enemies": []},
    "GMB": {"name": "Gambia", "allies": ["GBR"], "enemies": []},
    "SEN": {"name": "Senegal", "allies": ["FRA"], "enemies": []},
    "GNB": {"name": "Guinea-Bissau", "allies": ["PRT"], "enemies": []},
    "GIN": {"name": "Guinea", "allies": ["CHN"], "enemies": []},
    "SLE": {"name": "Sierra Leone", "allies": ["GBR"], "enemies": []},
    "LBR": {"name": "Liberia", "allies": ["USA"], "enemies": []},
    "COG": {"name": "Republic of the Congo", "allies": ["FRA"], "enemies": []},
    "CAF": {"name": "Central African Republic", "allies": ["RUS"], "enemies": ["FRA"]},
    "SSD": {"name": "South Sudan", "allies": ["USA"], "enemies": ["SDN"]},

    # Default fallback for countries not explicitly listed
    "DEFAULT": {"name": "Unknown Country", "allies": [], "enemies": []}
}

# Pre-load country geometries once on app startup to avoid reloading for every click
_country_geometries = {}
def load_country_geometries():
    """Loads country geometries from Natural Earth shapefile into memory."""
    global _country_geometries # Declare as global to modify the module-level variable
    try:
        shpfilename = shpreader.natural_earth(resolution='110m',
                                              category='cultural',
                                              name='admin_0_countries')
        reader = shpreader.Reader(shpfilename)
        for record in reader.records():
            _country_geometries[record.attributes['ISO_A3']] = {
                'name': record.attributes['NAME'],
                'geometry': record.geometry
            }
        print("Country geometries loaded successfully.")
    except Exception as e:
        print(f"Error loading country geometries: {e}")

# Call this function once when the app starts
load_country_geometries()

# Define the default map extent
DEFAULT_EXTENT = [-180, 180, -90, 90] # [lon_min, lon_max, lat_min, lat_max]
ZOOM_FACTOR = 0.7 # Factor to zoom in/out (e.g., 0.7 means 70% of current view)
MIN_ZOOM_WIDTH = 10 # Minimum longitude range for zoom in limit
MIN_ZOOM_HEIGHT = 10 # Minimum latitude range for zoom in limit

def generate_world_map_image(image_path="static/world_map.png", extent=DEFAULT_EXTENT, selected_iso=None, allies_iso_list=None, enemies_iso_list=None):
    """
    Generates a static world map image with optional coloring and specified extent,
    and saves it to the specified path.
    """
    if allies_iso_list is None:
        allies_iso_list = []
    if enemies_iso_list is None:
        enemies_iso_list = []

    try:
        fig = plt.Figure(figsize=(10, 7), dpi=100) # Keep original figure size and DPI
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

        # Set the extent for the current view
        ax.set_extent(extent, crs=ccrs.PlateCarree())

        ax.add_feature(cfeature.OCEAN, facecolor='#e0f2fe')
        ax.add_feature(cfeature.LAND, facecolor='#f8f8f8', edgecolor='white')

        for iso_a3, data in _country_geometries.items():
            geom = data['geometry']
            facecolor = '#cbd5e0' # Default grey

            if selected_iso and iso_a3 == selected_iso:
                facecolor = 'orange'
            elif iso_a3 in allies_iso_list:
                facecolor = 'green'
            elif iso_a3 in enemies_iso_list:
                facecolor = 'red'

            ax.add_geometries([geom], ccrs.PlateCarree(),
                                 facecolor=facecolor, edgecolor='white', linewidth=0.5, zorder=1)

        ax.add_feature(cfeature.BORDERS, linestyle=':', edgecolor='gray', zorder=2)
        ax.add_feature(cfeature.COASTLINE, linewidth=0.5, edgecolor='gray', zorder=2)

        fig.set_facecolor('#f3f4f6')
        ax.set_facecolor('white')

        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        fig.savefig(image_path, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        print(f"Generated map image at {image_path} with extent: {extent}")
    except Exception as e:
        print(f"Error generating map image: {e}")

@app.route('/')
def index():
    """
    Renders the main index.html page.
    Initializes the map extent in the session if not present.
    """
    if 'current_extent' not in session:
        session['current_extent'] = DEFAULT_EXTENT
        print(f"Initialized session extent to: {session['current_extent']}")
    
    # Generate the initial default map using the current session extent
    default_map_filename = 'world_map_default.png'
    default_map_path = os.path.join(STATIC_FOLDER, default_map_filename)
    
    # Always regenerate the default map with the current session extent for robustness
    generate_world_map_image(default_map_path, extent=session['current_extent'])
    print(f"Ensured default map exists at {default_map_path} for initial load.")

    return render_template('index.html', initial_map_url=url_for('static', filename=default_map_filename))

@app.route('/click_map', methods=['POST'])
def click_map():
    """
    API endpoint to handle map clicks, identify the country,
    and return updated geopolitical info and a colored map image URL.
    """
    data = request.json
    client_x = data.get('x')
    client_y = data.get('y')
    client_img_width = data.get('img_width')
    client_img_height = data.get('img_height')

    if None in [client_x, client_y, client_img_width, client_img_height]:
        return jsonify({"error": "Missing click coordinates or image dimensions"}), 400

    # Retrieve current extent from session to ensure click coordinates are relative to current view
    current_extent = session.get('current_extent', DEFAULT_EXTENT)
    lon_min, lon_max, lat_min, lat_max = current_extent

    # Define the original map dimensions from matplotlib fig.figsize and dpi
    original_map_width_px = 10 * 100 # figsize width * dpi
    original_map_height_px = 7 * 100 # figsize height * dpi

    # Scale the click coordinates from the client image dimensions to the original map dimensions
    scaled_x = (client_x / client_img_width) * original_map_width_px
    scaled_y = (client_y / client_img_height) * original_map_height_px

    # Convert pixel coordinates to longitude and latitude within the current extent
    # Calculate the current geographic width and height of the displayed map
    current_lon_range = lon_max - lon_min
    current_lat_range = lat_max - lat_min

    clicked_lon = lon_min + (scaled_x / original_map_width_px) * current_lon_range
    clicked_lat = lat_max - (scaled_y / original_map_height_px) * current_lat_range # Y-axis inverted for lat

    print(f"Clicked pixel: ({client_x}, {client_y}) on displayed image ({client_img_width}x{client_img_height})")
    print(f"Scaled pixel: ({scaled_x}, {scaled_y}) on original map ({original_map_width_px}x{original_map_height_px})")
    print(f"Converted Lat/Lon: ({clicked_lat}, {clicked_lon}) within extent {current_extent}")

    clicked_point = Point(clicked_lon, clicked_lat)

    selected_country_iso = None
    selected_country_name = "None"
    allies_names = []
    enemies_names = []

    # Iterate through pre-loaded country geometries to find which one contains the clicked point
    for iso, country_data in _country_geometries.items():
        geom = country_data['geometry']
        if geom.contains(clicked_point):
            selected_country_iso = iso
            selected_country_name = country_data['name'] # Use name from geometry data
            break

    if selected_country_iso:
        country_info = geopolitical_data.get(selected_country_iso, geopolitical_data["DEFAULT"])
        allies_iso = country_info.get('allies', [])
        enemies_iso = country_info.get('enemies', [])
        
        # Convert ISO codes of allies/enemies to their full names for display
        allies_names = [geopolitical_data.get(iso, {}).get('name', iso) for iso in allies_iso]
        enemies_names = [geopolitical_data.get(iso, {}).get('name', iso) for iso in enemies_iso]
        
        # Generate a new map image with the selected country and its relations colored
        colored_map_filename = f"world_map_{selected_country_iso}_{os.urandom(4).hex()}.png"
        colored_map_path = os.path.join(STATIC_FOLDER, colored_map_filename)
        
        generate_world_map_image(
            image_path=colored_map_path,
            extent=current_extent, # Use the current zoom extent for the new map
            selected_iso=selected_country_iso,
            allies_iso_list=allies_iso,
            enemies_iso_list=enemies_iso
        )
        map_url = url_for('static', filename=colored_map_filename)
        print(f"Map updated for {selected_country_name}, URL: {map_url}")

    else:
        # If no country was clicked (e.g., clicked on ocean), reset info and provide a fresh map (default colors)
        temp_map_filename = f"world_map_default_current_zoom_{os.urandom(4).hex()}.png" # Unique filename for a fresh map
        temp_map_path = os.path.join(STATIC_FOLDER, temp_map_filename) # Full path to save the image
        generate_world_map_image(temp_map_path, extent=current_extent) # Regenerate default colors with current zoom
        map_url = url_for('static', filename=temp_map_filename) # Generate URL for the frontend
        selected_country_name = "None"
        allies_names = ["None listed"]
        enemies_names = ["None listed"]
        print("No country clicked. Reverting to default map colors at current zoom.")

    response_data = {
        "name": selected_country_name,
        "allies": allies_names,
        "enemies": enemies_names,
        "map_url": map_url
    }
    return jsonify(response_data)

@app.route('/zoom_to_rect', methods=['POST'])
def zoom_to_rect():
    """
    API endpoint to handle rectangle zoom, calculate new extent,
    and return a new map image URL.
    """
    data = request.json
    x1, y1 = data.get('x1'), data.get('y1')
    x2, y2 = data.get('x2'), data.get('y2')
    img_width = data.get('img_width')
    img_height = data.get('img_height')

    if None in [x1, y1, x2, y2, img_width, img_height]:
        return jsonify({"error": "Missing rectangle coordinates or image dimensions"}), 400

    current_extent = session.get('current_extent', DEFAULT_EXTENT)
    lon_min_curr, lon_max_curr, lat_min_curr, lat_max_curr = current_extent

    # Original map dimensions used for generation
    original_map_width_px = 10 * 100
    original_map_height_px = 7 * 100

    # Scale client rectangle coordinates to original map dimensions
    scaled_x1 = (x1 / img_width) * original_map_width_px
    scaled_y1 = (y1 / img_height) * original_map_height_px
    scaled_x2 = (x2 / img_width) * original_map_width_px
    scaled_y2 = (y2 / img_height) * original_map_height_px

    # Convert scaled pixel coordinates to new geographic extent
    # Lon range maps to X axis, Lat range maps to Y axis (inverted)
    current_lon_range = lon_max_curr - lon_min_curr
    current_lat_range = lat_max_curr - lat_min_curr

    # Calculate new min/max longitudes and latitudes based on the selected rectangle
    # The new longitude is scaled from the current longitude range
    new_lon_min = lon_min_curr + (scaled_x1 / original_map_width_px) * current_lon_range
    new_lon_max = lon_min_curr + (scaled_x2 / original_map_width_px) * current_lon_range

    # The new latitude is scaled from the current latitude range, remembering Y is inverted
    new_lat_max = lat_max_curr - (scaled_y1 / original_map_height_px) * current_lat_range
    new_lat_min = lat_max_curr - (scaled_y2 / original_map_height_px) * current_lat_range

    new_extent = [new_lon_min, new_lon_max, new_lat_min, new_lat_max]

    # Ensure extent is within valid global bounds and sensible (min size for zoom)
    new_extent[0] = max(new_extent[0], -180)
    new_extent[1] = min(new_extent[1], 180)
    new_extent[2] = max(new_extent[2], -90)
    new_extent[3] = min(new_extent[3], 90)

    # Prevent extremely small zooms that might cause rendering issues or bad UX
    if (new_extent[1] - new_extent[0] < MIN_ZOOM_WIDTH) or \
       (new_extent[3] - new_extent[2] < MIN_ZOOM_HEIGHT):
        print("Zoom rectangle too small. Adjusting to minimum zoom width/height.")
        # Re-center the new extent to ensure it's not off-screen if user dragged too small
        center_lon = (new_extent[0] + new_extent[1]) / 2
        center_lat = (new_extent[2] + new_extent[3]) / 2
        new_extent = [
            center_lon - (MIN_ZOOM_WIDTH / 2),
            center_lon + (MIN_ZOOM_WIDTH / 2),
            center_lat - (MIN_ZOOM_HEIGHT / 2),
            center_lat + (MIN_ZOOM_HEIGHT / 2)
        ]
        # And re-clamp to global bounds
        new_extent[0] = max(new_extent[0], -180)
        new_extent[1] = min(new_extent[1], 180)
        new_extent[2] = max(new_extent[2], -90)
        new_extent[3] = min(new_extent[3], 90)


    session['current_extent'] = new_extent
    print(f"Zoomed to rectangle. New extent: {new_extent}")

    # Generate a new map image with the updated extent
    zoomed_map_filename = f"world_map_zoomed_{os.urandom(4).hex()}.png"
    zoomed_map_path = os.path.join(STATIC_FOLDER, zoomed_map_filename)
    generate_world_map_image(zoomed_map_path, extent=new_extent)

    # When zooming, reset country info as no specific country was clicked yet in new view
    return jsonify({
        "map_url": url_for('static', filename=zoomed_map_filename),
        "name": "None",
        "allies": [],
        "enemies": []
    })

@app.route('/reset_view', methods=['POST'])
def reset_view():
    """
    API endpoint to reset the map view to the default global extent.
    """
    session['current_extent'] = DEFAULT_EXTENT
    print("Resetting view to default global extent.")

    # Generate a new default map image
    reset_map_filename = f"world_map_reset_{os.urandom(4).hex()}.png"
    reset_map_path = os.path.join(STATIC_FOLDER, reset_map_filename)
    generate_world_map_image(reset_map_path, extent=DEFAULT_EXTENT)

    return jsonify({
        "map_url": url_for('static', filename=reset_map_filename),
        "name": "None",
        "allies": [],
        "enemies": []
    })


if __name__ == '__main__':
    # Initial cleanup of the static folder once at app startup
    print(f"Clearing contents of {STATIC_FOLDER} on app startup...")
    for filename in os.listdir(STATIC_FOLDER):
        file_path = os.path.join(STATIC_FOLDER, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path} during startup cleanup. Reason: {e}')
    print("Static folder cleanup complete.")

    # Generate the initial default map right after cleanup
    default_map_filename = 'world_map_default.png'
    default_map_path = os.path.join(STATIC_FOLDER, default_map_filename)
    generate_world_map_image(default_map_path, extent=DEFAULT_EXTENT)
    print(f"Generated initial default map at {default_map_path}")

    app.run(debug=True, port=5000)
