#!/bin/env python3
#
# This script downloads and manages Hubitat configuration backups.
# In order to use it, you must enable backups first under
#    https://<hubitat.ip.address>/hub/backup
# The tool is meant to run as cron job.
#
# Example usage:
#    hubitat-backup.py 192.168.1.100 34:e1:d1:00:11:22 ~/Downloads -a 7
import argparse
from datetime import datetime
import io
import os
import requests
from typing import Any, List


def throw(message: str):
    """Throw a simple Exception with supplied message."""
    raise (Exception(message))


def get_date(partial: str) -> datetime:
    """Convert partial date/time string (mm/dd HH:MM) to a full datetime object."""
    now = datetime.now()
    date1 = datetime.strptime(f"{now.year} {partial}", "%Y %m/%d %H:%M")
    date2 = datetime.strptime(f"{now.year - 1} {partial}", "%Y %m/%d %H:%M")
    return date1 if date1 < now else date2


class Hub:
    session: requests.Session
    ip_addr: str
    mac_address: str

    def __init__(self, ip_addr: str, mac_address: str):
        self.session = requests.Session()
        self.ip_addr = ip_addr
        self.mac_address = mac_address

    def login(self):
        """Sign in to Hubitat Maintenance site."""
        print(f"Signing in")
        self.post(f"/newLogin", "".join(self.mac_address.split(":")).upper())

    def _url(self, request_path: str) -> str:
        """Generate Hubitat Maintenance URL."""
        return f"http://{self.ip_addr}:8081{request_path}"

    def _verify_response(
        self,
        request_type: str,
        request_path: str,
        is_json: bool,
        response: requests.Response,
    ) -> Any:
        if response.status_code != 200:
            throw(f"{request_type} request to {request_path} failed: {response.reason}")

        if not is_json:
            return response.content

        json_response = response.json()
        if not json_response["success"]:
            throw(
                f"{request_type} request to {request_path} not successful: {response.content.decode()}"
            )

        return json_response

    def post(self, request_path: str, data: str) -> Any:
        result = self.session.post(self._url(request_path), data)
        return self._verify_response("POST", request_path, True, result)

    def get(self, request_path: str) -> Any:
        result = self.session.get(self._url(request_path))
        return self._verify_response("GET", request_path, True, result)

    def download(self, request_path: str) -> bytes:
        result = self.session.get(self._url(request_path))
        return self._verify_response("DOWNLOAD", request_path, False, result)


def download_available_backups(backup_path: str, hub: Hub):
    # Create destination directory if one doesn't exist already.
    os.makedirs(backup_path, exist_ok=True)

    backups = hub.get("/api/backups")["backups"]
    if not backups:
        throw(
            f"No backups found. Make sure backups are enabled on http://{hub.ip_addr}/hub/backup"
        )

    for backup in backups:
        backup_name: str = backup["name"]
        backup_date: str = backup["createTime"]

        if not backup_name.endswith(".lzf"):
            print(f"Skipping {backup_name}: unrecognized suffix")
            continue

        target = os.path.join(backup_path, backup_name)
        if os.path.exists(target):
            print(f"Skipping already downloaded backup file: {backup_name}")
            continue

        content = hub.download(f"/api/downloadBackup/{backup_name}")

        with io.open(target, "wb") as file:
            print(f"Downloading backup file: {backup_name}")
            file.write(content)
            date = get_date(backup_date).timestamp()
            os.utime(file.name, (date, date))


def clean_old_backups(backup_path, max_age_days: int):
    now = datetime.now()

    for item in os.scandir(backup_path):
        if not item.is_file(follow_symlinks=False):
            # Not a file. Ignore.
            continue

        if not item.name.endswith(".lzf"):
            # Not a backup file. Ignore.
            continue

        stat = os.stat(os.path.join(backup_path, item.name))
        file_stamp = datetime.fromtimestamp(stat.st_mtime)
        file_age_days = (now - file_stamp).days

        if file_age_days < max_age_days:
            continue

        print(f"Removing old backup file: {item.name} - {file_age_days} days old")
        os.unlink(os.path.join(backup_path, item.name))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download Hubitat backups to specified location."
    )
    parser.add_argument("-a", "--max-age-days", type=int, default="90")
    parser.add_argument("ip_address")
    parser.add_argument("mac_address")
    parser.add_argument("destination")

    args = parser.parse_args()

    DESTINATION = args.destination
    MAX_AGE_DAYS = args.max_age_days

    print(
        f"Downloading backup files to {DESTINATION}, removing files older than {MAX_AGE_DAYS} days"
    )

    try:
        hub = Hub(args.ip_address, args.mac_address)
        hub.login()
        download_available_backups(DESTINATION, hub)
    except Exception as e:
        print(e)

    clean_old_backups(DESTINATION, MAX_AGE_DAYS)
