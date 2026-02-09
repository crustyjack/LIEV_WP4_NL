# Written by: Michael Jenks
# Last update: 24/11/2025

import gspread
#import requests
#import folium

import streamlit as st
import pandas as pd
#import numpy as np
#import matplotlib.pyplot as plt
#import altair as alt

from google.oauth2.service_account import Credentials
#from datetime import timedelta
#from PIL import Image
#from io import BytesIO

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


if __name__ == "__main__":
    loaded = load_Gsheets()