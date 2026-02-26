import folium
import background_code
import streamlit as st
import pandas as pd
#import geopandas as gpd

#from shapely import wkt
from datetime import timedelta, datetime
from streamlit_folium import st_folium


st.set_page_config(layout="wide")

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
    st.session_state.MSRs = bg.get_sheet_dataframe("MSRs short", workbook)

if "vbo_objects" not in st.session_state:
    st.session_state.vbo_objects = bg.get_sheet_dataframe("Objects", workbook)

if "profielen" not in st.session_state:
    st.session_state.profielen = bg.get_sheet_dataframe("Profielen", workbook)

msr_gdf = bg.build_msr_gdf(st.session_state.MSRs)
houses_gdf = bg.build_vbo_gdf(st.session_state.vbo_objects, "vbo_points1")
profielen_df = st.session_state.profielen
gebruik_df = bg.build_gebruik_df(st.session_state.vbo_objects)

# --- Session state ---
if "selected_id" not in st.session_state:
    st.session_state.selected_id = None

m = bg.build_base_map(msr_gdf)

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
                zoom_start=17
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

            st.subheader(f"Buildings connected to MSR: {st.session_state.selected_id}")
            st_folium(house_map, width="100%", height=400, key="house_map")
        else:
            st.warning("No houses found for this MSR.")

    #HvA_logo_url = "https://lectorenplatformleve.nl/wp-content/uploads/2021/11/HvA.jpg"
    HvA_logo_url = "https://amsterdamgreencampus.nl/wp-content/uploads/2016/01/AmsUniOfAppSci.png"
    st.image(bg.image_converter(HvA_logo_url, 255, 255, 255, 255, 200))

with right_col:
    if st.session_state.selected_id:
        st.subheader(f"MSR: {st.session_state.selected_id}")

        st.write("Current selected_id:", st.session_state.selected_id)

        # Input box
        #new_id = st.text_input("Override selected_id")

        # Button
        #if st.button("Override"):
        #    st.session_state.selected_id = new_id
        #    st.success("selected_id updated!")

        #st.write("Updated selected_id:", st.session_state.selected_id)

        # Filter MSR row
        msr_row = gebruik_df[gebruik_df["owner_msr"].astype(str) == str(st.session_state.selected_id)]
        #st.dataframe(msr_row)

        if len(msr_row) > 0:
            # Display all columns as a simple table
            charge_strat = st.selectbox(
                "Which charging strategy would you like to apply?",
                ("Regular on-demand charging", "Grid-aware smart charging", "Capacity pooling", "V2G"))

            #Accom_elect_perc = st.slider("What percentage of accomodation is fully electric?", 0, 100, 25)

            #year = st.slider("What year would you like to model? - For now only impacts EV adoption", 2025, 2050, 2025)
            EV_adoption_perc = st.slider("What percentage of EV adoption would you like to model?", int(msr_row["percentage_evs_msr"].iloc[0]), 100, int(msr_row["percentage_evs_msr"].iloc[0]))
            #WP_adoption_perc = st.slider("What percentage of electrical heat pump adoption would you like to model?", 10, 100, 10)

            df_output = bg.profile_creator(profielen_df, msr_row, EV_adoption_perc)
            #st.dataframe(df_output)
            #df_output = bg.update_charge_strat(df_output, charge_strat, profielen_df, gebruik_df, st.session_state.selected_id)
            #df_output = bg.adjust_EV_profile(df_output, EV_adoption_perc, EV_factor=5)

            #df_output = bg._map_2024_to_year(df_output, year)

            if "min_max" not in st.session_state:
                st.session_state.min_max = "-"

            if st.button("Change date to day with highest peak load"):
                date_max_power = df_output.loc[df_output["MSR totaal [kW]"].idxmax(), ("DATUM_TIJDSTIP_2024")]
                st.session_state.date_max_power = date_max_power
                st.session_state.min_max = "max"

            if st.button("Change date to day with least (or most negative) peak load"):
                date_min_power = df_output.loc[df_output["MSR totaal [kW]"].idxmin(), ("DATUM_TIJDSTIP_2024")]
                st.session_state.date_min_power = date_min_power
                st.session_state.min_max = "min"
            #st.write("You are modelling ", MSR_name, " MSR", "with an fully electric home adoption rate of ", Accom_elect_perc, "%, in the year ", year, ".")

            min_date = df_output["DATUM_TIJDSTIP_2024"].min().date()
            max_date = df_output["DATUM_TIJDSTIP_2024"].max().date()

            default_start = min_date

            if "min_max" in st.session_state:
                if st.session_state.min_max == "max" and "date_max_power" in st.session_state:
                    default_start = st.session_state.date_max_power
                elif st.session_state.min_max == "min" and "date_min_power" in st.session_state:
                    default_start = st.session_state.date_min_power

            if isinstance(default_start, pd.Timestamp):
                default_start = default_start.date()

            default_start = min(max(default_start, min_date), max_date)

            start_date = st.date_input("Start date", default_start, min_value=min_date, max_value=max_date)
            end_date = st.date_input("End date", start_date + timedelta(days=1), min_value=start_date + timedelta(days=1), max_value=max_date)

            date_range = (end_date - start_date).days

            # Initialize session_state flags
            if "awaiting_confirmation" not in st.session_state:
                st.session_state.awaiting_confirmation = False

            # ---- MAIN LOGIC ----
            if date_range <= 10:
                # short range → run immediately
                bg.prepare_plot_df(start_date, end_date, df_output)

            else:
                # long range → require confirmation
                if not st.session_state.awaiting_confirmation:
                    st.warning(f"You selected a long date range: {date_range} days.")
                    st.info("This may be slow. Do you want to continue?")
                    if st.button("Yes, continue"):
                        st.session_state.awaiting_confirmation = True
                    else:
                        st.stop()  # Avoid running anything else
                if st.session_state.awaiting_confirmation:
                    bg.prepare_plot_df(start_date, end_date, df_output)
                    st.session_state.awaiting_confirmation = False

            plot_placeholder = st.empty()   # chart will appear BELOW this

            # ---- INIT SESSION STATE ----
            if "df_plot_data" not in st.session_state:
                st.session_state["df_plot_data"] = None

            # ---- BUTTON (always above the plot) ----
            #if st.button("Update plot"):
                #bg.prepare_plot_df(start_date, end_date, df_output, MSR_name, df_MSRs_measured) # not sure what this does

            bg.prepare_plot_df(start_date, end_date, df_output) # not sure what this does

            # ---- SHOW PLOT (if exists) ----
            plot_placeholder = st.empty()   # <--- optional: ensure placeholder exists early

            if st.session_state["df_plot_data"] is not None:
                #plot_placeholder.line_chart(st.session_state["df_plot_data"])
                bg.plot_df_with_dashed_lines(st.session_state["df_plot_data"], plot_placeholder)
            else:
                st.write("No plot generated yet.")

            

    else:
        st.info("👈 Click an MSR point on the map to see details here.")
