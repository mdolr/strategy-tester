import os
import typing
import dotenv

from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

dotenv.load_dotenv()

# Load credentials from the JSON file
CREDENTIALS_FILE = os.environ.get('GOOGLE_CREDENTIALS_PATH')
SPREADSHEET_ID = os.environ.get('GOOGLE_SHEET_ID')

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']  # Scopes for Google Sheets API

# Set up the Google Sheets API client
credentials = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
service = build('sheets', 'v4', credentials=credentials)

# Get the Spreadsheet ID from the environment variable
if not SPREADSHEET_ID:
    raise EnvironmentError("GOOGLE_SHEET_ID environment variable is not set")

def update_sheet(data: typing.List[typing.Dict]):
    """
    Function that takes a list of dictionaries formatted with multiple keys and values.

    Writes the keys of the object in column A, then for every item writes the values in columns B to ...

    Parameters:
    - data (list): The list of dictionaries to write to the Google Sheet.

    Returns:
    - None
    """
    if not data:
        raise ValueError("The data list is empty.")

    # Get the keys of the first dictionary
    keys = list(data[0].keys())

    # Prepare data to write in row-major order
    sheet_data = []
    for key in keys:
        # Create a row: first column is the key, followed by the values for each dictionary
        if "returns" in key:
            row = [key] + [round(item[key], 3) if isinstance(item[key], (int, float)) else item[key] for item in data]
        else:
            row = [key] + [item[key] for item in data]
        sheet_data.append(row)

    # Write the prepared data to the sheet
    range_ = 'A1'
    request_body = {
        'range': range_,
        'values': sheet_data
    }

    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=range_,
        valueInputOption='RAW',
        body=request_body
    ).execute()

    return None

def clear_sheet():
    """
    Function that clears the contents of the Google Sheet.

    Returns:
    - None
    """
    service.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID,
        range='A1:Z100'
    ).execute()

    return None