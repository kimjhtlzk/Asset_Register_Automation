# pip3 install google-api-python-client google-auth-httplib2 google-auth-oauthlib gspread gspread-dataframe pandas
import gspread
import datetime
import os
import logging
import shutil
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import gspread_dataframe as gd

RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
ORANGE = "\033[38;5;214m"
UNDERLINE = "\033[4m"


class CustomFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        return datetime.datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = CustomFormatter(f'{BLUE}%(asctime)s{RESET} - {YELLOW}%(levelname)s{RESET} - {ORANGE}%(message)s{RESET}')
handler.setFormatter(formatter)
logger.handlers = [handler]

CSV_DIR = './temp_csv'
PARENT_FOLDER_ID = '1RvZ*/*******************'

def authenticate_google_services(key_file_path):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(key_file_path, scopes=scopes)
    return gspread.authorize(creds), build('drive', 'v3', credentials=creds)

def fetch_sheet_data(sheet_id, sheet_names, gc):
    dataframes = {}
    spreadsheet = gc.open_by_key(sheet_id)

    for sheet_name in sheet_names:
        worksheet = spreadsheet.worksheet(sheet_name)
        df = gd.get_as_dataframe(worksheet, evaluate_formulas=True)
        dataframes[sheet_name] = df.dropna(how='all')
        logger.info(f"{GREEN}{sheet_name} 시트 데이터 추출 완료{RESET}")
    return dataframes

def save_to_csv(dataframes):
    os.makedirs(CSV_DIR, exist_ok=True)
    for sheet_name, df in dataframes.items():
        df.to_csv(f"{CSV_DIR}/{sheet_name}.csv", index=False)
        logger.info(f"{GREEN}{sheet_name}.csv 파일 저장 완료{RESET}")

def get_folder_name(folder_id, drive_service):
    try:
        folder = drive_service.files().get(fileId=folder_id, fields="name", supportsAllDrives=True).execute()
        return folder.get("name")
    except HttpError as error:
        logger.error(f"{RED}폴더 이름 가져오기 오류: {error}{RESET}")
        return None

def get_or_create_year_folder(parent_id, year, drive_service):
    query = f"name = '{year}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder'"
    results = drive_service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)",
        includeItemsFromAllDrives=True,
        supportsAllDrives=True
    ).execute()
    folders = results.get("files", [])

    if folders:
        logger.info(f"{RED}{year} 연도 폴더가 이미 존재합니다.{RESET}")
        return folders[0]['id']
    else:
        folder_metadata = {
            'name': str(year),
            'mimeType': "application/vnd.google-apps.folder",
            'parents': [parent_id]
        }
        folder = drive_service.files().create(
            body=folder_metadata,
            fields='id',
            supportsAllDrives=True
        ).execute()
        logger.info(f"{GREEN}{year} 연도 폴더를 생성했습니다.{RESET}")
        return folder.get('id')

def create_month_folder(parent_id, month, drive_service):
    folder_metadata = {
        'name': str(month),
        'mimeType': "application/vnd.google-apps.folder",
        'parents': [parent_id]
    }
    folder = drive_service.files().create(
        body=folder_metadata,
        fields='id',
        supportsAllDrives=True
    ).execute()
    logger.info(f"{GREEN}{month} 월 폴더를 새로 생성했습니다.{RESET}")
    return folder.get('id')

def upload_file_to_drive(file_name, folder_id, drive_service):
    try:
        file_metadata = {'name': file_name, 'parents': [folder_id]}
        media = MediaFileUpload(f"{CSV_DIR}/{file_name}", mimetype='text/csv')
        drive_service.files().create(body=file_metadata, media_body=media, fields='id',
                                     supportsAllDrives=True).execute()
        logger.info(f"{GREEN}{file_name} 파일 Google Drive 업로드 완료{RESET}")
    except HttpError as error:
        logger.error(f"{RED}Google API 오류 발생: {error}{RESET}")

def cleanup():
    if os.path.exists(CSV_DIR):
        shutil.rmtree(CSV_DIR)
        logger.info(f"{GREEN}임시 CSV 파일 정리 완료{RESET}")


def main():
    key_file_path = '../auth/gcp-ie3-grafana-d0e7985d808a.json'
    sheet_id = "1rQ3rQ********************"
    sheet_names = [
        'LOGS_FIREWALL',
        'LOGS_ACCOUNT',
        'LOGS_KEY',
        'LOGS_INSTANCE'
    ]

    gc, drive_service = authenticate_google_services(key_file_path)

    # 부모 폴더 이름 출력
    parent_folder_name = get_folder_name(PARENT_FOLDER_ID, drive_service)
    if parent_folder_name:
        logger.info(f"{GREEN}작업 대상 부모 폴더: {parent_folder_name} ({PARENT_FOLDER_ID}){RESET}")
    else:
        logger.warning(f"{RED}부모 폴더 이름을 가져올 수 없습니다. ID: {PARENT_FOLDER_ID}{RESET}")

    dataframes = fetch_sheet_data(sheet_id, sheet_names, gc)
    save_to_csv(dataframes)

    now = datetime.datetime.now()
    year = now.year
    month = now.month
    if month == 1:
        year -= 1
        month = 12
    else:
        month -= 1

    # 연도 폴더 확인 및 생성
    year_folder_id = get_or_create_year_folder(PARENT_FOLDER_ID, year, drive_service)

    # 월 폴더 항상 새로 생성
    month_folder_id = create_month_folder(year_folder_id, month, drive_service)

    # 파일 업로드
    for sheet_name in sheet_names:
        file_name = f"{sheet_name}.csv"
        upload_file_to_drive(file_name, month_folder_id, drive_service)

    cleanup()


if __name__ == '__main__':
    main()
