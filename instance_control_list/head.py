import string
import gspread
import time
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from gcp_instance_control_list import main  as get_data_GCP
from tencent_instance_control_list import main  as get_data_TENCENT
from aws_instance_control_list import main  as get_data_AWS


RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
ORANGE = "\033[38;5;214m"
UNDERLINE = "\033[4m"


def upload_gsheet(worksheet_name, sheet_id, datas):
    # ------------------------------- Basic sheet info -------------------------------
    key_file_path = '../auth/gcp.json'

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file"
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        key_file_path,
        scopes=scope
    )

    client = gspread.authorize(credentials)
    service = build('sheets', 'v4', credentials=credentials)

    spreadsheet = client.open_by_key(sheet_id)
    worksheet = spreadsheet.worksheet(worksheet_name)
    num_items = len(datas)
    end_column = string.ascii_uppercase[len(vars(datas[0])) - 1]
    existing_rows = worksheet.row_count

    # ------------------------------- Clear the entire sheet first -------------------------------
    range_to_clear = f"A2:{end_column}{existing_rows}"
    worksheet.batch_clear([range_to_clear])

    # ------------------------------- Delete rows -------------------------------
    delete_rows_requests = [{
        "deleteDimension": {
            "range": {
                "sheetId": worksheet.id,
                "dimension": "ROWS",
                "startIndex": 0,
                "endIndex": existing_rows-1
            }
        }
    }]

    delete_rows_body = {
        'requests': delete_rows_requests
    }
    service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=delete_rows_body).execute()

    # ------------------------------- Prepare data to upload -------------------------------
    data_to_upload = []
    header = [attr for attr in vars(datas[0])]

    # Add header to data_to_upload
    data_to_upload.append(header)

    for data in datas:
        row = [getattr(data, attr) for attr in header]
        row = [', '.join(item) if isinstance(item, list) else item for item in row]
        data_to_upload.append(row)

    worksheet.insert_rows(data_to_upload, 1)  # Insert at row 1 to include header

    # ------------------------------- Set header style -------------------------------
    header_format = {
        "repeatCell": {
            "range": {
                "sheetId": worksheet.id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 0,
                "endColumnIndex": len(header)
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {
                        "red": 0.643,
                        "green": 0.761,
                        "blue": 0.957
                    },
                    "textFormat": {
                        "foregroundColor": {
                            "red": 1,
                            "green": 1,
                            "blue": 1
                        },
                        "fontSize": 11,
                        "bold": True
                    }
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat)"
        }
    }
    service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={'requests': [header_format]}).execute()

    # ------------------------------- Apply filter to the entire data range -------------------------------
    sheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheets = sheet_metadata.get('sheets', [])
    row_count = 1000
    for sheet in sheets:
        if sheet['properties']['title'] == worksheet_name:
            row_count = (sheet['properties']['gridProperties']['rowCount'])-1
            # print(row_count)
            break

    filter_request = {
        "setBasicFilter": {
            "filter": {
                "range": {
                    "sheetId": worksheet.id,
                    "startRowIndex": 0,
                    "endRowIndex": row_count,
                    "startColumnIndex": 0,
                    "endColumnIndex": len(header)
                }
            }
        }
    }
    service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={'requests': [filter_request]}).execute()

    # ------------------------------- Set sheet style -------------------------------
    cell_style_requests = []
    # Set vertical alignment to middle and horizontal alignment to left for data rows only
    for i in range(2, num_items + 2):
        cell_style_requests.append({
            "updateCells": {
                "rows": {
                    "values": [{
                        "userEnteredFormat": {
                            "verticalAlignment": "MIDDLE",
                            "horizontalAlignment": "LEFT"
                        }
                    }] * len(header)
                },
                "fields": "userEnteredFormat.verticalAlignment,userEnteredFormat.horizontalAlignment",  # 필드에 가로 맞춤 추가
                "range": {
                    "sheetId": worksheet.id,
                    "startRowIndex": i - 1,
                    "endRowIndex": i,
                    "startColumnIndex": 0,
                    "endColumnIndex": len(header)
                }
            }
        })

    # Add requests to auto resize columns
    for col_index in range(len(header)):
        cell_style_requests.append(
            {
                "autoResizeDimensions": {
                    "dimensions": {
                        "sheetId": worksheet.id,
                        "dimension": "COLUMNS",
                        "startIndex": col_index,
                        "endIndex": col_index + 1
                    },
                },
            },
        )

    # Add request to set the new width (current width + 10 pixels)
    for col_index in range(len(header)):
        column_metadata = service.spreadsheets().get(spreadsheetId=sheet_id, ranges=worksheet.title,fields='sheets.data.columnMetadata').execute()
        current_width = column_metadata['sheets'][0]['data'][0]['columnMetadata'][col_index]['pixelSize']

        new_width = current_width + 10
        cell_style_requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": worksheet.id,
                        "dimension": "COLUMNS",
                        "startIndex": col_index,
                        "endIndex": col_index + 1
                    },
                    "properties": {
                        "pixelSize": new_width
                    },
                    "fields": "pixelSize"
                }
            }
        )

    # Add requests to auto resize rows
    for row_index in range(2, num_items + 2):
        cell_style_requests.append(
            {
                "autoResizeDimensions": {
                    "dimensions": {
                        "sheetId": worksheet.id,
                        "dimension": "ROWS",
                        "startIndex": row_index - 1,
                        "endIndex": row_index
                    },
                },
            },
        )

    cell_style_body = {
        'requests': cell_style_requests
    }
    service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=cell_style_body).execute()

    # ------------------------------- Freeze to header rows -------------------------------
    freeze_request = {
        "updateSheetProperties": {
            "properties": {
                "sheetId": worksheet.id,
                "gridProperties": {
                    "frozenRowCount": 1
                }
            },
            "fields": "gridProperties.frozenRowCount"
        }
    }
    service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={'requests': [freeze_request]}).execute()


    print(f"{GREEN}Data uploaded to Google Sheets successfully!{RESET}")


def main():
    start_time = time.time()

    GCP = get_data_GCP()
    TENCENT = get_data_TENCENT()
    AWS = get_data_AWS()

    combined_datas = GCP + TENCENT + AWS
    # print("Combined Datas:", combined_datas)

    # sheet info
    sheet_id = "1rQ3rQ********************"
    worksheet_name = "INSTANCE"

    # upload data to gsheet
    upload_gsheet(
        worksheet_name=worksheet_name,
        sheet_id=sheet_id,
        datas=combined_datas
    )

    elapsed_time = time.time() - start_time
    hours, remainder = divmod(int(elapsed_time), 3600)
    minutes, seconds = divmod(remainder, 60)

    print(f"\n{worksheet_name} {BLUE}logic running: {hours}h : {minutes}m : {seconds}s{RESET}\n")


if __name__ == "__main__":
    main()
