import gspread
import folium
import background_code

import streamlit as st
import geopandas as gpd

#from google.oauth2.service_account import Credentials
from shapely import wkt
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, FastMarkerCluster

st.title("Modelling system for all medium voltage stations in NL")
st.write(
    "Please select the MSR you would like to analyse."
)
st.write(
    "For any comments please reach out to m.j.f.jenks@hva.nl"
)



bg = background_code.BackgroundCode()

# Load sheet only if not already in session_state
if "workbook" not in st.session_state:
    st.session_state.workbook = bg.load_Gsheets()

workbook = st.session_state.workbook

# Load profiles dataframe only if not already in session_state
if "MSR_locations" not in st.session_state:
    st.session_state.MSRs = bg.get_sheet_dataframe("MSRs", workbook)

MSR_locations = st.session_state.MSRs

# Load profiles dataframe only if not already in session_state
if "vbo_points" not in st.session_state:
    st.session_state.vbo_objects = bg.get_sheet_dataframe("Objects", workbook)

vbo_points = st.session_state.vbo_objects

##################
# test code
##################
MSR_locations["geometry"] = MSR_locations["geometry"].apply(wkt.loads)

msr_gdf = gpd.GeoDataFrame(
    MSR_locations, 
    geometry=MSR_locations["geometry"],
    crs="EPSG:28992"
)

# working version
"""
test_msrs = msr_gdf.copy()

# Convert to WGS84
gdf_wgs = test_msrs.to_crs(epsg=4326)

# Extract coordinates
coords = list(zip(gdf_wgs.geometry.y, gdf_wgs.geometry.x, gdf_wgs["ID"]))  # lat, lon

# Create map
mean_lat = gdf_wgs.geometry.y.mean()
mean_lon = gdf_wgs.geometry.x.mean()
m = folium.Map(location=[mean_lat, mean_lon], zoom_start=7)

# Add all points at once
FastMarkerCluster(coords).add_to(m)

# Render in Streamlit
st_folium(m, width=700, height=500)

"""

from folium.plugins import FastMarkerCluster
import folium
from streamlit_folium import st_folium

test_msrs = msr_gdf.copy()

# Initialize session state
if "selected_id" not in st.session_state:
    st.session_state.selected_id = None

gdf_wgs = test_msrs.to_crs(epsg=4326)

m = folium.Map(location=[gdf_wgs.geometry.y.mean(), gdf_wgs.geometry.x.mean()], zoom_start=7)

callback = """
function (row) {
    var marker = L.marker(new L.LatLng(row[0], row[1]));
    marker.bindPopup(String(row[2]));
    marker.bindTooltip(String(row[2]));
    return marker;
}
"""


coords = list(zip(gdf_wgs.geometry.y, gdf_wgs.geometry.x, gdf_wgs["ID"]))
FastMarkerCluster(coords, callback=callback).add_to(m)

map_data = st_folium(m, width=700, height=500)

# Update session state when a marker is clicked
if map_data.get("last_object_clicked_tooltip"):
    st.session_state.selected_id = map_data["last_object_clicked_tooltip"]

# This now persists across reruns
if st.session_state.selected_id:
    st.success(f"Selected ID: **{st.session_state.selected_id}**")
    st.write("Proceeding with ID:", st.session_state.selected_id)
    # your next step code here...

