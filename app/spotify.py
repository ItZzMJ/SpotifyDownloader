import os
from pprint import pprint
from time import sleep
from mutagen.mp3 import HeaderNotFoundError
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import WebDriverException, TimeoutException, ElementClickInterceptedException, \
    NoSuchFrameException, StaleElementReferenceException, NoSuchElementException
from spotify_dl import spotify
import spotipy
from spotify_dl.spotify import validate_spotify_url
from spotipy.oauth2 import SpotifyClientCredentials
from pathlib import Path, PurePath
from dotenv import load_dotenv
import music_tag
from mutagen.mp3 import MP3
import urllib.request


class SpotifyDownloader:
    def __init__(self):
        ########### Ziel Ordner ###############
        self.result_dir = "C:/Users/Jannik/Desktop/musicTest"
        #######################################

        ########### Playlist URL ##############
        self.url = "https://open.spotify.com/playlist/6zK6D0YigFUc0ClcBEUAy0?si=01983811d566458e"
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
        song = ""
        artist = ""

        for file_name in items:
            file_path = os.path.join(path, file_name)

            try:
                mp3 = music_tag.load_file(file_path)
                song = mp3['title'].value
                artist = mp3['artist'].value

            except HeaderNotFoundError:
                print("MP3 Corrupted!")
            except NotImplementedError:
                print("Not Impltemented Error for: ")
                print(file_path)

            downloaded_tracks.append(artist + " - " + song)

        return downloaded_tracks

    # def rename_files(self, path, songs):
    #     items = os.listdir(path)
    #
    #     for file in items:
    #         if " myfreemp3.vip " in file:
    #             splitted = file.split(" - ")
    #             new_file = ""
    #
    #             for song in songs:
    #                 if song['name'] in splitted[1] and song['artist'] in splitted[0]:
    #                     new_file = path + "/" + song['artist'] + " - " + song['name']
    #                     os.rename(path + "/" + file, new_file)
    #
    #             if new_file == "":
    #                 print(file + " was not found in songs")

                # if " myfreemp3.vip " in file:
                #     file = file.strip()
                #     new_file = path + "/" + file.replace(" myfreemp3.vip ", "")
                #     if not os.path.isfile(new_file):
                #         os.rename(path + "/" + file, new_file)
                #     else:
                #         os.remove(path + "/" + file)

    def get_homepage(self):
        try:
            self.driver.get(self.website)
        except WebDriverException:
            print("No Website!! Exiting..")
            exit(-1)

    def get_dl_button(self, q):
        driver = self.driver
        request_not_found = "/html/body/div[2]/div[2]/div[2]/li"
        dbutton = ""

        try:
            input_elem = WebDriverWait(driver, 2).until(
                lambda driver: driver.find_element_by_id("query"))

            input_elem.send_keys(q)
            input_elem.send_keys(Keys.RETURN)
            # dbutton = WebDriverWait(driver, 3).until(
            #     lambda driver: driver.find_element_by_xpath(download_button1))

            list_entries = WebDriverWait(driver, 3).until(
                lambda driver: driver.find_elements_by_css_selector("#result > div.list-group > li"))

        except TimeoutException:
            try:
                error_elem = WebDriverWait(driver, 3).until(
                    lambda driver: driver.find_element_by_xpath(request_not_found))
            except TimeoutException:
                driver.refresh()
                sleep(1)
                return dbutton
            else:
                print("No Song found!! " + q)
                return "skip"
        else:

            i = 0
            for entry in list_entries:
                try:
                    size_button = entry.find_element_by_class_name("dropdown-toggle")
                    size_button.click()
                    sleep(2)
                except NoSuchElementException:
                    continue

                try:
                    size_elem = driver.find_elements_by_class_name("info-link")[i]
                except StaleElementReferenceException:
                    print("Element is not Attached to the side!")
                    print(entry.tag_name)
                    print(entry.text)
                    exit(-5)
                i += 1

                if "NaN kB" in size_elem.text:
                    size_button.click()
                    continue
                else:
                    dbutton = driver.find_elements_by_partial_link_text("Download")[i]
                    break

        return dbutton

    def get_dl_links(self, songs, downloaded_tracks):
        driver = self.driver
        dl_links = []
        dbutton = ""
        success = False
        download_button1 = "/html/body/div[2]/div[2]/div[2]/li/div/a[3]"
        download_button2 = "/html/body/div[2]/div/div[1]/button"
        song_array = {}
        id = 0

        for song in songs:
            q = song['artist'] + " - " + song['name']
            if q in downloaded_tracks:
                print(q + " is already downloaded!")
                continue
            else:
                print("getting " + q)

            self.get_homepage()

            count = 0

            while True:
                if count >= 5:
                    break
                else:
                    dbutton = self.get_dl_button(q)
                    if dbutton != "":
                        break
                    else:
                        count += 1

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

                song_array[id] = {'dlink': download_link, 'song': song}
                id += 1
        return song_array

    def replace_chars(self, string, chars):
        for char in chars:
            string = string.replace(char, "")
        return string

    def download_from_links(self, song_array):
        driver = self.driver
        for key in song_array:
            item = song_array[key]

            url = item['dlink']
            song = item['song']
            file_name = self.replace_chars(song['artist'] + " - " + song['name'] + ".mp3", "<>:\"/\\|?*")

            song_path = os.path.join(self.dl_path, file_name)

            print("downloading: " + song_path)

            urllib.request.urlretrieve(url, song_path)

            print("download finished! Setting metadata..")

            self.set_metadata(song_path, song)
            sleep(1)

    def set_metadata(self, song_path, song):
        try:
            mp3 = music_tag.load_file(song_path)
            mp3['title'] = song['name']
            mp3['artist'] = song['artist']
            mp3['genre'] = song['genre']
            mp3['year'] = song['year']
            mp3['album'] = song['album']
            del mp3['tracknumber']
            mp3.save()

        except HeaderNotFoundError as err:
            print(err)
            print("Corrupted MP3!! deleting...:")
            print(song_path)
            os.remove(song_path)

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

        self.driver = webdriver.Chrome("C:/Users/Jannik/AppData/Local/Programs/Python/Python39/chromedriver.exe", options=options)

        self.driver.set_window_position(3000, 0)
        self.driver.maximize_window()

    def run(self):
        url = self.url
        songs = self.get_songs(url)

        downloaded_tracks = self.check_dir(self.dl_path)

        self.create_browser()

        song_array = self.get_dl_links(songs, downloaded_tracks)

        self.download_from_links(song_array)
        sleep(15)

    def tear_down(self):
        self.driver.quit()


if __name__ == '__main__':
    sd = SpotifyDownloader()
    try:
        sd.run()
    finally:
        sd.tear_down()
