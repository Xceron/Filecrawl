#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import os
import getpass
import keyring
import requests
from bs4 import BeautifulSoup
import sys
from typing import Union

from aran.setup_logger import logger


def save_credentials(username: str, password: str) -> None:
    """
    :param username: username used for Studip
    :param password: password used for Studip
    :return: sets username and password in local keyring
    """
    keyring.set_password("StudipCrawl", username, password)
    logger.debug(f"saved credentials {username} with {password}")


def get_credentials(username: str) -> str:
    """
    :param username: username used for Studip
    :return: password
    """
    logger.debug(f"getting credentials for {username}")
    return keyring.get_password("StudipCrawl", username)


def validate_password(username: str, password: str) -> bool:
    """
    :param username: username used for Studip
    :param password: password used for Studip
    :return: boolean if combination is right
    """
    with requests.Session() as r:
        homepage = r.get("https://studip.uni-trier.de/index.php?again=yes")
        soup = BeautifulSoup(homepage.text, "html.parser")
        security_token = soup.find("input", {"name": "security_token"})["value"]
        login_ticket = soup.find("input", {"name": "login_ticket"})["value"]
        try:
            if not homepage.ok:
                logger.error("Studip or user is offline")
                input("Press any key to exit")
                sys.exit(1)
            else:
                payload = {"security_ticket": security_token,
                           "login_ticket": login_ticket,
                           "loginname": username,
                           "password": password}
                login_start = r.post("https://studip.uni-trier.de/index.php?again=yes", data=payload)
                if "angemeldet" in login_start.text:
                    logger.debug(f"Password is valid")
                    return True
                else:
                    logger.error(f"Wrong username and/or password")
                    return False
        except AttributeError:
            logger.debug("AttributeError, retrying login")
            # weird cases where AttributeError gets thrown
            validate_password(username, password)


def create_json_config() -> None:
    """
    :return: saves into the json file
    """
    positive_answers = ["yes", "y", "ye", "ja", "+", "1"]
    negative_answers = ["no", "n", "nein", "-", "0"]
    data = {
        "username": "NAME",
        "path": "",
        "moodle": "x",
        "download_videos": "x"
    }

    # username and password

    def check_credentials():
        logger.info("Enter your Studip username:")
        username = input()
        logger.info("Enter your Studip password: ")
        password = getpass.getpass()
        data["username"] = username
        save_credentials(username, password)

    check_credentials()
    while not validate_password(data["username"], get_credentials(data["username"])):
        check_credentials()
    # path
    while not (os.path.exists(data["path"])):
        logger.info("Enter the path where the files should be downloaded. If you need help, type \"help\".")
        path = input()
        if path == "help":
            logger.debug("Entered \"help\" as path, opening GUI")
            try:
                import tkinter
                from tkinter import filedialog
                logger.debug("Opening Tkinter filedialog")
                tkinter.Tk().withdraw()
                path = filedialog.askdirectory()
            except ImportError:
                logger.error("Your Python version is missing Tkinter, it is not possible to open the GUI. Type "
                             "the path manually")
        logger.debug(f"Entered {path} as path to save files to")
        data["path"] = path
    while not (type(data["moodle"]) == bool):
        logger.info("Do you want to download files from moodle? [y/n]")
        moodle_input = input()
        if moodle_input in positive_answers:
            data["moodle"] = True
            while not (type(data["download_videos"]) == bool):
                logger.info("Do you want to download videos? [y/n]")
                video_input = input()
                if video_input in positive_answers:
                    data["download_videos"] = True
                elif video_input in negative_answers:
                    data["download_videos"] = False
        elif moodle_input in negative_answers:
            data["moodle"] = False
            data["download_videos"] = False
        logger.debug(f"Moodle is set to {moodle_input}")
        logger.debug(f"Download Videos is set to {video_input}")
    # convert into json data and save it
    data_json = json.dumps(data, indent=4)
    json_path = os.path.join(os.getcwd(), "aran_config.json")
    with open(json_path, "w") as file:
        logger.debug("Successfully opened the config file")
        file.write(data_json)


def get_value(key: str) -> Union[bool, str]:
    """
    :param key: key of json file
    :return: value of key
    """
    json_path = os.path.join(os.getcwd(), "aran_config.json")
    if not os.path.exists(json_path):
        logger.error("No config found")
        logger.info("Setup begins")
        create_json_config()
        if os.path.exists(json_path):
            logger.info(f"Successfully created config in {os.getcwd()}.")
            logger.info("Starting the download")
    else:
        with open(json_path, "r") as file:
            logger.debug("Succesfully opened the config file")
            data = json.load(file)
            return data[key]
