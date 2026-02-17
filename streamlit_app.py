import folium
import background_code
import streamlit as st
import geopandas as gpd

from shapely import wkt
from streamlit_folium import st_folium
from folium.plugins import FastMarkerCluster

st.title("Modelling system for all medium voltage stations in NL")
st.write("Please select the MSR you would like to analyse.")
st.write("For any comments please reach out to m.j.f.jenks@hva.nl")

if st.button("🔄 Refresh Data"):
    st.cache_resource.clear()
    st.session_state.clear()
    st.rerun()

bg = background_code.BackgroundCode()

# --- Load data into session state ---
if "workbook" not in st.session_state:
    st.session_state.workbook = bg.load_Gsheets()

workbook = st.session_state.workbook

if "MSRs" not in st.session_state:
    st.session_state.MSRs = bg.get_sheet_dataframe("MSRs", workbook)

if "vbo_objects" not in st.session_state:
    st.session_state.vbo_objects = bg.get_sheet_dataframe("Objects", workbook)

st.write("\n--- DEBUG GEOMETRIES ---")

for i, g in enumerate(st.session_state.vbo_objects["vbo_points1"]):
    try:
        wkt.loads(g)
    except Exception as e:
        st.write("BROKEN ROW:", i)
        st.write("VALUE:", repr(g))
        st.write("ERROR:", e)
        break

# --- Build GeoDataFrames ---
@st.cache_resource
def build_msr_gdf(_df):
    if _df["geometry"].dtype == object and isinstance(_df["geometry"].iloc[0], str):
        _df["geometry"] = _df["geometry"].apply(wkt.loads)
    return gpd.GeoDataFrame(_df, geometry="geometry", crs="EPSG:28992")

# @st.cache_resource
def build_vbo_gdf(_df, col_name):

    print("\n--- DEBUG GEOMETRIES ---")

    for i, g in enumerate(_df[col_name]):
        try:
            wkt.loads(g)
        except Exception as e:
            print("BROKEN ROW:", i)
            print("VALUE:", repr(g))
            print("ERROR:", e)
            break
    if _df[col_name].dtype == object and isinstance(_df[col_name].iloc[0], str):
        _df = _df[_df[col_name].notna()]
        _df = _df[_df[col_name].str.strip() != ""]
        _df[col_name] = _df[col_name].apply(wkt.loads)
    return gpd.GeoDataFrame(_df, geometry=col_name, crs="EPSG:28992")

msr_gdf = build_msr_gdf(st.session_state.MSRs)
houses_gdf = build_vbo_gdf(st.session_state.vbo_objects, "vbo_points1")

# --- Session state ---
if "selected_id" not in st.session_state:
    st.session_state.selected_id = None

# --- Build map fresh each run (not cached) ---
def build_base_map(_gdf):
    gdf_wgs = _gdf.to_crs(epsg=4326)
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
    return m

m = build_base_map(msr_gdf)

# --- Create grid layout ---
left_col, right_col = st.columns([1, 1])  # map takes 2/3, data takes 1/3

with left_col:
    # --- Main MSR map ---
    map_data = st_folium(
        m,
        width="100%",
        height=400,
        key="main_map",
    )

    # --- Capture click ---
    if map_data.get("last_object_clicked_tooltip"):
        st.session_state.selected_id = map_data["last_object_clicked_tooltip"]

    # --- House map ---
    if st.session_state.selected_id:
        selected_houses = houses_gdf[
            houses_gdf["owner_msr"].astype(str) == str(st.session_state.selected_id)
        ].to_crs(epsg=4326)

        if len(selected_houses) > 0:
            house_map = folium.Map(
                location=[
                    selected_houses.geometry.centroid.y.mean(),
                    selected_houses.geometry.centroid.x.mean()
                ],
                zoom_start=14
            )
            for geom in selected_houses.geometry:
                for point in geom.geoms:
                    folium.CircleMarker(
                        location=[point.y, point.x],
                        radius=5,
                        color="red",
                        fill=True,
                        fill_opacity=0.8,
                    ).add_to(house_map)

            st.subheader(f"Houses — MSR {st.session_state.selected_id}")
            st_folium(house_map, width="100%", height=400, key="house_map")
        else:
            st.warning("No houses found for this MSR.")

with right_col:
    if st.session_state.selected_id:
        st.subheader(f"MSR {st.session_state.selected_id}")

        # Filter MSR row
        msr_row = msr_gdf[msr_gdf["ID"].astype(str) == str(st.session_state.selected_id)]

        if len(msr_row) > 0:
            # Display all columns as a simple table
            # Drop geometry column since it's not human readable
            display_data = msr_row.drop(columns="geometry").T
            display_data.columns = ["Value"]
            st.dataframe(display_data, use_container_width=True)
    else:
        st.info("👈 Click an MSR point on the map to see details here.")