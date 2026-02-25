# Written by: Michael Jenks
# Last update: 24/11/2025

import gspread
import requests
#import folium

import altair as alt
import streamlit as st
import pandas as pd
import geopandas as gpd
#import numpy as np
#import matplotlib.pyplot as plt


from google.oauth2.service_account import Credentials
from shapely import wkt
#from datetime import timedelta
from PIL import Image
from io import BytesIO

class BackgroundCode:

    def __init__(self):
        self.locations = {
            "Sporenburg": (52.373815, 4.945598),
            "Roelantstraat": (52.376836, 4.856632),
            "Vincent van Goghstraat": (52.349022, 4.888944),
        }
    
    def load_Gsheets(
            self, 
            Gsheet_ID="1p2HqiGGOKvuZfjxSTOIi_NBotnnCxq0_0UG8hZhbM0g"
            ):
        # Load service account info securely from Streamlit secrets
        
        SCOPES = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=SCOPES)
        gc = gspread.authorize(creds)

        spreadsheet = gc.open_by_key(Gsheet_ID)

        return spreadsheet

    def get_sheet_dataframe(self, sheet_name, sheet):
        """Read a worksheet into a DataFrame."""
        try:
            worksheet = sheet.worksheet(sheet_name)
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except gspread.WorksheetNotFound:
            st.warning(f"Worksheet '{sheet_name}' not found.")
            return pd.DataFrame()
        
    def get_sheet_dataframe(self, sheet_name, sheet):
        """Read a worksheet into a DataFrame."""
        try:
            worksheet = sheet.worksheet(sheet_name)
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except gspread.WorksheetNotFound:
            st.warning(f"Worksheet '{sheet_name}' not found.")
            return pd.DataFrame()
        
    # --- Build GeoDataFrames ---
    @staticmethod
    @st.cache_resource
    def build_msr_gdf(_df):
        if _df["geometry"].dtype == object and isinstance(_df["geometry"].iloc[0], str):
            _df["geometry"] = _df["geometry"].apply(wkt.loads)
        return gpd.GeoDataFrame(_df, geometry="geometry", crs="EPSG:28992")

    @staticmethod
    @st.cache_resource
    def build_vbo_gdf(_df, col_name):
        if _df[col_name].dtype == object and isinstance(_df[col_name].iloc[0], str):
            _df = _df[_df[col_name].notna()]
            _df = _df[_df[col_name].str.strip() != ""]
            _df[col_name] = _df[col_name].apply(wkt.loads)
        return gpd.GeoDataFrame(_df, geometry=col_name, crs="EPSG:28992")
    
    def profile_creator(self, df_profiles, msr_row):
        #import inspect
        #st.write("Function called from:")
        #st.write(inspect.stack()[1])

        df_MSR_profile = pd.DataFrame()
        #msr_row = df_MSRs[df_MSRs['owner_msr'] == MSR_ID]
        if len(msr_row.index) is not 1:
            st.write("Error in MSR matches")

        df_MSR_profile["DATUM_TIJDSTIP_2024"] = df_profiles["DATUM_TIJDSTIP_2024"].copy()

        df_MSR_profile["Woningen totaal [kW]"] = df_profiles["jvb_woon"].copy()*msr_row["jvb_woon"].iloc[0]*4
        df_MSR_profile["Winkel [kW]"] = df_profiles["jvb_winkel"].copy()*msr_row["jvb_winkel"].iloc[0]*4
        


        #df_MSR_profile["Woningen totaal [kW]"] = df_MSR_profile["Woning [kW]"] + df_MSR_profile["Appartement [kW]"]
        df_MSR_profile["Utiliteit totaal [kW]"] = df_MSR_profile["Winkel [kW]"] #+ df_MSR_profile["Onderwijs [kW]"] + df_MSR_profile["Kantoor [kW]"] + df_MSR_profile["Gezondsheid [kW]"] + df_MSR_profile["Industrie [kW]"] + df_MSR_profile["Overig [kW]"] + df_MSR_profile["Logies [kW]"] + df_MSR_profile["Bijenkomst [kW]"] + df_MSR_profile["Sport [kW]"]
        
        
        df_MSR_profile["MSR totaal [kW]"] = df_MSR_profile["Woningen totaal [kW]"] + df_MSR_profile["Utiliteit totaal [kW]"] # + df_MSR_profile["Zonnepanelen [kW]"] + df_MSR_profile["Oplaad punten [kW]"]

        df_MSR_profile["DATUM_TIJDSTIP_2024"] = pd.to_datetime(df_MSR_profile["DATUM_TIJDSTIP_2024"], dayfirst=True)

        return df_MSR_profile
    
    def update_charge_strat(self, df, charge_strat, df_profiles, df_MSRs, MSR_ID):
        charge_profile_name = self.charge_profile_lookup(charge_strat)
        msr_row = df_MSRs[df_MSRs['owner_msr'] == MSR_ID]

        # this data still to be added to gsheets
        #df["Oplaad punten [kW]"] = df_profiles[charge_profile_name].copy()*msr_row["jvb_EV"]*4
        df["MSR totaal [kW]"] = df["Zonnepanelen [kW]"] + df["Oplaad punten [kW]"] + df["Woningen totaal [kW]"] + df["Utiliteit totaal [kW]"]

        return df

    def charge_profile_lookup(self, charge_strat):
        
        if charge_strat == "Regular on-demand charging":
            prof_name = "Charge point energy_normalised [kWh/kWh]"
        
        if charge_strat == "Grid-aware smart charging":
            prof_name = "Elaad_net_bewust_norm. [kWh/kWh]"

        if charge_strat == "Capacity pooling":
            prof_name = "Elaad_cap_pooling_norm. [kWh/kWh]"

        if charge_strat == "V2G":
            prof_name = "Elaad_V2G_norm. [kWh/kWh]"

        return prof_name
    
    def prepare_plot_df(self, start_date, end_date, df):
        mask = (df["DATUM_TIJDSTIP_2024"] >= pd.to_datetime(start_date)) & (df["DATUM_TIJDSTIP_2024"] <= pd.to_datetime(end_date))
        
        df_slice = df.loc[mask]

        # --- add to cols to plot ---
        cols_to_plot = [
            "Woningen totaal [kW]",
            "Utiliteit totaal [kW]",
            #"Zonnepanelen [kW]",
            #"Oplaad punten [kW]",
            "MSR totaal [kW]"
        ]
        
        # --- store into session_state
        st.session_state["df_plot_data"] = df_slice.set_index("DATUM_TIJDSTIP_2024")[cols_to_plot]

    def plot_df_with_dashed_lines(
            self, 
            df,
            placeholder,
            dashed_series = [
                #"Oplaad punten [kW]",
                "Utiliteit totaal [kW]",
                "Woningen totaal [kW]",
                #"Zonnepanelen [kW]"
            ]
        ):
        if df is None or df.empty:
            placeholder.write("No data to plot.")
            return
        
        label_map = {
            "Oplaad punten [kW]" : "Public charging points",
            "Utiliteit totaal [kW]": "Utility buildings",
            "Woningen totaal [kW]": "Accomodation buildings",
            "Zonnepanelen [kW]": "Solar panels"
        }

        dashed_series = [
            #"Public charging points",
            "Utility buildings",
            "Accomodation buildings",
            #"Solar panels"
        ]

        # Reset index safely
        df_reset = df.reset_index()

        # Identify the index column (the column added by reset_index)
        index_col = df_reset.columns[0]

        # Ensure datetime index is treated correctly
        df_reset[index_col] = pd.to_datetime(df_reset[index_col])

        # Convert to long format
        df_long = df_reset.melt(
            id_vars=index_col,
            var_name="series",
            value_name="value"
        )

        df_long["series"] = df_long["series"].replace(label_map)

        # Build chart
        chart = (
            alt.Chart(df_long)
            .mark_line()
            .encode(
                x=alt.X(index_col + ":T", title="Date"),   # Temporal axis (date/time)
                y=alt.Y("value:Q", title="Power [kW]"),
                color=alt.Color("series:N", title=""),
                strokeDash=alt.condition(
                    alt.FieldOneOfPredicate(field="series", oneOf=dashed_series),
                    alt.value([4, 4]),       # dashed style
                    alt.value([1, 0])        # solid style
                ),
                strokeWidth=alt.condition(
                    alt.FieldOneOfPredicate(field="series", oneOf=dashed_series),
                    alt.value(1),            # thinner dashed lines
                    alt.value(2.5)           # thicker solid lines
                )
            )
            .properties(
                padding={"bottom": 40}         # add 40px bottom margin
            )
        )

        # Render chart
        placeholder.altair_chart(chart, width='stretch')

    def image_converter(self, URL, R, G, B, A, width=None):
        response = requests.get(URL)
        image = Image.open(BytesIO(response.content)).convert("RGBA")
        background = Image.new("RGBA", image.size, (R, G, B, A))
        background.paste(image, (0,0), image)
        final_image = background.convert("RGB")

        if width:
            w, h = final_image.size
            ratio = width / w
            new_height = int(h * ratio)
            final_image = final_image.resize((width, new_height), Image.LANCZOS)

        return final_image

if __name__ == "__main__":
    loaded = load_Gsheets()