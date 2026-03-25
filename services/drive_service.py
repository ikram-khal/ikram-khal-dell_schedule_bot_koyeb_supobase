"""
Google Drive service operations for the Combined Bot
"""
import os
import io
import json
import base64
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from config.settings import DRIVE_CREDENTIALS


def init_drive():
    """Initialize Google Drive service"""
    if not DRIVE_CREDENTIALS or DRIVE_CREDENTIALS == "ENTER_UR_TOKEN":
        return None, None

    try:
        creds_json = base64.b64decode(DRIVE_CREDENTIALS).decode('utf-8')
        creds_dict = json.loads(creds_json)
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
        )
        drive_service = build('drive', 'v3', credentials=credentials)
        return drive_service, credentials
    except Exception as e:
        print(f"Error initializing Google Drive: {e}")
        return None, None


def upload_to_drive(drive_service, file_path: str, folder_id: str):
    """Upload file to Google Drive"""
    if not drive_service:
        return None
    
    try:
        file_name = os.path.basename(file_path)
        file_metadata = {'name': file_name, 'parents': [folder_id]}
        media = MediaFileUpload(file_path)
        file = drive_service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id'
        ).execute()
        return file.get('id')
    except Exception as e:
        print(f"Error uploading to Google Drive: {e}")
        return None


def download_latest_from_drive(drive_service, folder_id: str, prefix: str):
    """Download latest file with given prefix from Google Drive"""
    if not drive_service:
        return None
    
    try:
        results = drive_service.files().list(
            q=f"'{folder_id}' in parents and name contains '{prefix}'",
            orderBy='createdTime desc',
            pageSize=1,
            fields="files(id, name)"
        ).execute()
        
        files = results.get('files', [])
        if not files:
            return None
        
        file_id, file_name = files[0]['id'], files[0]['name']
        file_path = os.path.join(os.path.dirname(__file__), '..', 'data', file_name)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        request = drive_service.files().get_media(fileId=file_id)
        with io.FileIO(file_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        
        return file_path
    except Exception as e:
        print(f"Error downloading from Google Drive: {e}")
        return None


def list_drive_files(drive_service, folder_id: str, prefix: str = None):
    """List files in Google Drive folder"""
    if not drive_service:
        return []
    
    try:
        query = f"'{folder_id}' in parents"
        if prefix:
            query += f" and name contains '{prefix}'"
        
        results = drive_service.files().list(
            q=query,
            fields="files(id, name, createdTime)",
            orderBy='createdTime desc'
        ).execute()
        
        return results.get('files', [])
    except Exception as e:
        print(f"Error listing Drive files: {e}")
        return []


def delete_drive_file(drive_service, file_id: str):
    """Delete file from Google Drive"""
    if not drive_service:
        return False
    
    try:
        drive_service.files().delete(fileId=file_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting Drive file: {e}")
        return False