import os
from pprint import pprint
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import WebDriverException, TimeoutException, ElementClickInterceptedException, \
    NoSuchFrameException
from spotify_dl import spotify
import spotipy
from spotify_dl.spotify import validate_spotify_url
from spotipy.oauth2 import SpotifyClientCredentials
from pathlib import Path, PurePath
from dotenv import load_dotenv


class SpotifyDownloader:
    def __init__(self):
        ########### Ziel Ordner ###############
        self.result_dir = "/home/jannik/Musik/Test"
        #######################################

        ########### Playlist URL ##############
        self.url = "https://open.spotify.com/playlist/372BtTHHZohugO714p8mzK?si=cd675169d7724f95"
        #######################################

        load_dotenv(".env")
        self.dl_path = ""

        self.auth = SpotifyClientCredentials(client_id=os.getenv("SP_CLIENT_ID"), client_secret=os.getenv("SP_SECRET"))

        self.sp = spotipy.Spotify(auth_manager=self.auth)
        self.website = "https://myfreemp3music.com/"

    def get_songs(self, url):
        valid_item = validate_spotify_url(url)

        item_type, item_id = spotify.parse_spotify_url(url)
        directory_name = spotify.get_item_name(self.sp, item_type, item_id)
        save_path = Path(PurePath.joinpath(Path(self.result_dir), Path(directory_name)))
        save_path.mkdir(parents=True, exist_ok=True)
        self.dl_path = str(save_path)
        print("Saving Songs to " + self.dl_path)

        songs = spotify.fetch_tracks(self.sp, item_type, url)

        return songs

    def check_dir(self, path):
        items = os.listdir(path)
        downloaded_tracks = []

        for file_name in items:
            song = file_name.replace(" myfreemp3.vip ", "").replace(".mp3", "")
            downloaded_tracks.append(song)

        return downloaded_tracks

    def rename_files(self, path):
        items = os.listdir(path)

        for file in items:
            if " myfreemp3.vip " in file:
                os.rename(path + "/" + file, path + "/" + file.replace(" myfreemp3.vip ", ""))

    def get_homepage(self):
        try:
            self.driver.get(self.website)
        except WebDriverException:
            print("No Website!! Exiting..")
            exit(-1)

    def get_dl_links(self, songs, downloaded_tracks):
        driver = self.driver
        dl_links = []
        dbutton = ""
        success = False
        download_button1 = "/html/body/div[2]/div[2]/div[2]/li/div/a[3]"
        download_button2 = "/html/body/div[2]/div/div[1]/button"

        for song in songs:
            q = song['artist'] + " - " + song['name']
            if q in downloaded_tracks:
                print(q + " is already downloaded!")
                continue

            self.get_homepage()

            count = 0

            while True:
                if count >= 3:
                    break
                else:
                    try:
                        input_elem = WebDriverWait(driver, 3).until(
                            lambda driver: driver.find_element_by_id("query"))

                        input_elem.send_keys(q)
                        input_elem.send_keys(Keys.RETURN)
                        dbutton = WebDriverWait(driver, 6).until(
                            lambda driver: driver.find_element_by_xpath(download_button1))
                    except TimeoutException:
                        driver.refresh()
                        count += 1
                        sleep(1)
                    else:
                        break

            try:
                link = dbutton.get_attribute("onclick").replace("window.open(\'", "").replace("\',\'_blank\');", "")
            except Exception as e:
                print("No Download link found for " + q)
                print("Error: {0}".format(e))
                continue

            try:
                driver.get(link)
                dbutton2 = WebDriverWait(driver, 6).until(
                    lambda driver: driver.find_element_by_xpath(download_button2))
            except TimeoutException:
                print("No Download Button! for " + q)
            else:
                download_link = dbutton2.get_attribute("onclick").replace("window.open(\'", "")\
                    .replace("\',\'_blank\');", "")
                dl_links.append(download_link)
        return dl_links

    def download_from_links(self, links):
        driver = self.driver
        for link in links:
            try:
                sleep(1)
                driver.get(link)
            except WebDriverException:
                print("WebDriverException!!")

    def create_browser(self):
        ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36"

        options = webdriver.ChromeOptions()
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument("--incognito")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument("--disable-notifications")
        options.add_argument('--disable-dev-shm-usage')
        # options.add_argument("--headless")
        # options.add_argument("--disable-gpu")
        # options.add_argument('--allow-insecure-localhost')

        options.add_experimental_option("prefs", {
            "download.default_directory": self.dl_path,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing_for_trusted_sources_enabled": False,
            "safebrowsing.enabled": False
        })
        # options.add_experimental_option('prefs', prefs)

        self.driver = webdriver.Chrome("/usr/bin/chromedriver", options=options)

        self.driver.set_window_position(3000, 0)
        self.driver.maximize_window()

    def run(self):
        url = self.url
        songs = self.get_songs(url)

        downloaded_tracks = self.check_dir(self.dl_path)

        self.create_browser()

        dl_links = self.get_dl_links(songs, downloaded_tracks)

        self.download_from_links(dl_links)

        self.rename_files(self.dl_path)

    def tear_down(self):
        self.driver.quit()


if __name__ == '__main__':
    sd = SpotifyDownloader()
    try:
        sd.run()
    finally:
        sd.tear_down()