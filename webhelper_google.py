import gspread
import json
from oauth2client.client import SignedJwtAssertionCredentials
import time
import os

GOOGLE_SHEETS_API_KEY_FILE = os.path.dirname(os.path.realpath(__file__)) + os.sep + 'google_api_key.json'
    

class GoogleSpreadsheet:
    def __repr__(self):
        return "Google spreadsheet %s" % (self.name,)

    def __init__(self, name):
        self.name = name
        json_key = json.load(open(GOOGLE_SHEETS_API_KEY_FILE))
        scope = ['https://spreadsheets.google.com/feeds']

        credentials = SignedJwtAssertionCredentials(json_key['client_email'], json_key['private_key'], scope)
        gc = gspread.authorize(credentials)

        self.ss = gc.open(name)

    def export_data(self, rows, sheet_name):
        worksheet = None
        cols = 1
        for row in rows:
            if cols < len(row):
                cols = len(row)
        cols = max(cols, 2)

        sheets = self.ss.worksheets()
        if not sheet_name in [sheet.title for sheet in sheets]:
            worksheet = self.ss.add_worksheet(title = sheet_name, rows = str(len(rows) + 1), cols = str(cols))
        else:
            worksheet = self.ss.worksheet(sheet_name)
            worksheet.resize(rows = str(len(rows) + 1), cols = str(cols))

        curdate = time.localtime()
            
        if len(rows) > 0:
            # Get cell objects from google
            cell_list = worksheet.range('A2:%s' % (worksheet.get_addr_int(len(rows)+1, cols)))
            assert len(cell_list) == cols * (len(rows))

            # Update cell objects with data
            for y, r in enumerate(rows):
                for x in range(cols):
                    if x < len(r):
                        cell_list[y*cols + x].value = r[x]
                    else:
                        cell_list[y*cols + x].value = ""

            # Send batch of updates to server
            worksheet.update_cells(cell_list)

        worksheet.update_cell(1, 1, 'Updated %0.2d/%0.2d/%d at %0.2d:%0.2d' % (curdate.tm_mon, curdate.tm_mday, curdate.tm_year, curdate.tm_hour, curdate.tm_min))

    def import_data(self, sheet_name):
        sheets = self.ss.worksheets()
        if not sheet_name in [sheet.title for sheet in sheets]:
            return []
        worksheet = self.ss.worksheet(sheet_name)
        return worksheet.get_all_values()[1:]
