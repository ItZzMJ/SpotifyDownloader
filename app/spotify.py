import json
import os
import traceback
from json import JSONDecodeError
from os.path import isfile
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
import PySimpleGUI as sg
import requests


class SpotifyDownloader:
    def __init__(self):
        settings = self.load_settings()
        self.result_dir = settings['result_dir']
        self.url = settings['url']

        self.debug = []

        load_dotenv(".env")
        self.dl_path = ""

        self.auth = SpotifyClientCredentials(client_id=os.getenv("SP_CLIENT_ID"), client_secret=os.getenv("SP_SECRET"))

        self.sp = spotipy.Spotify(auth_manager=self.auth)
        self.website = "https://myfreemp3music.com/"

    def get_songs(self, url):
        valid_item = validate_spotify_url(url)

        item_type, item_id = spotify.parse_spotify_url(url)
        directory_name = spotify.get_item_name(self.sp, item_type, item_id).replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
        save_path = Path(PurePath.joinpath(Path(self.result_dir), Path(directory_name)))
        save_path.mkdir(parents=True, exist_ok=True)
        self.dl_path = str(save_path)
        print("[LOG] Saving Songs to " + self.dl_path)
        self.debug.append("[LOG] Saving Songs to " + self.dl_path)

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
                print("[ERR] MP3 Corrupted!")
                self.debug.append("[ERR] MP3 Corrupted!")
            except NotImplementedError as e:
                print("[ERR] Not Impltemented Error for: ")
                self.debug.append("[ERR] Not Impltemented Error for: ")
                print(file_path)
                self.debug.append(file_path)
                self.debug.append("[ERR] Error: {0}".format(e))

            downloaded_tracks.append(artist + " - " + song)

        return downloaded_tracks

    def get_homepage(self):
        try:
            self.driver.get(self.website)
        except WebDriverException:
            print("[ERR] No Website!! Exiting..")
            self.debug.append("[ERR] No Website!! Exiting..")
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
                print("[LOG] No Song found!! " + q)
                self.debug.append("[LOG] No Song found!! " + q)
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
                except StaleElementReferenceException as e:
                    print("[ERR] Element is not Attached to the side!")
                    self.debug.append("[ERR] Element is not Attached to the side!")
                    print(entry.tag_name)
                    self.debug.append(entry.tag_name)
                    print(entry.text)
                    self.debug.append(entry.text)
                    self.debug.append("[ERR] Error: {0}".format(e))
                    exit(-5)

                except IndexError as e:
                    print("[ERR] Index Error while getting size_elem!")
                    self.debug.append("[ERR] Index Error while getting size_elem!")
                    self.debug.append("[ERR] Error: {0}".format(e))

                i += 1

                try:
                    if "NaN kB" in size_elem.text:
                        size_button.click()
                        continue
                    else:
                        dbutton = driver.find_elements_by_partial_link_text("Download")[i]
                        break
                except Exception as e:
                    print("[ERR] No attribute text")
                    self.debug.append("[ERR] No attribute text")
                    self.debug.append("[ERR] Error: {0}".format(e))

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
                print("[LOG] " + q + " is already downloaded!")
                self.debug.append("[LOG] " + q + " is already downloaded!")
                continue
            else:
                print("[LOG] Getting " + q)
                self.debug.append("[LOG] Getting " + q)

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
                print("[LOG] No Download link found for " + q)
                self.debug.append("[LOG] No Download link found for " + q)
                print("[ERR] Error: {0}".format(e))
                self.debug.append("[ERR] Error: {0}".format(e))
                continue

            try:
                driver.get(link)
                dbutton2 = WebDriverWait(driver, 6).until(
                    lambda driver: driver.find_element_by_xpath(download_button2))
            except TimeoutException as e:
                print("[ERR] No Download Button! for " + q)
                self.debug.append("[ERR] No Download Button! for " + q)

                self.debug.append("[ERR] Error: {0}".format(e))

            else:
                download_link = dbutton2.get_attribute("onclick").replace("window.open(\'", "") \
                    .replace("\',\'_blank\');", "")

                song_array[id] = {'dlink': download_link, 'song': song}
                id += 1
                self.update_progress_bar(False)

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

            print("[LOG] Downloading: " + song_path)
            self.debug.append("[LOG] Downloading: " + song_path)

            urllib.request.urlretrieve(url, song_path)

            print("[LOG] Download finished! Setting metadata..")
            self.debug.append("[LOG] Download finished! Setting metadata..")
            self.update_progress_bar(False)

            self.set_metadata(song_path, song)
            sleep(1)
        print("<-------------- Download completed! Fasching Mafensen -------------->")
        self.debug.append("<-------------- Download completed! Fasching Mafensen -------------->")
        self.update_progress_bar(True)

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
            print("[ERR] Corrupted MP3!! deleting...:" + song['artist'] + " - " + song['name'])
            self.debug.append("[ERR] Corrupted MP3!! deleting...:" + song['artist'] + " - " + song['name'])
            self.debug.append("[ERR] Error: {0}".format(err))

            os.remove(song_path)

    def create_browser(self, show_chrome=False):
        ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36"

        options = webdriver.ChromeOptions()
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument("--incognito")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument("--disable-notifications")
        options.add_argument('--disable-dev-shm-usage')

        if not show_chrome:
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")

        # options.add_argument('--allow-insecure-localhost')

        options.add_experimental_option("prefs", {
            "download.default_directory": self.dl_path,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing_for_trusted_sources_enabled": False,
            "safebrowsing.enabled": False
        })

        self.driver = webdriver.Chrome("/usr/bin/chromedriver",
                                       options=options)

        self.driver.set_window_position(3000, 0)
        self.driver.maximize_window()

    def update_progress_bar(self, complete):
        if complete:
            max = self.progress_bar.TKProgressBar.Max
            self.progress_bar.update_bar(max)
        else:
            count = self.progress_bar.TKProgressBar.TKProgressBarForReal['value']
            self.progress_bar.update_bar(count + 1)
        self.window.refresh()

    def load_settings(self):
        file = "settings.json"
        if not os.path.isfile(file):
            return {'result_dir': '', 'url': ''}

        f = open(file, "r+")
        try:
            settings = json.load(f)
        except JSONDecodeError as e:
            print("[ERR] Error while reading settings! Check file!")
            self.debug.append("[ERR] Error while reading settings! Check file!")
            self.debug.append("[ERR] Error: {0}".format(e))

            settings = {'result_dir': '', 'url': ''}
        finally:
            f.close()

        return settings

    def save_settings(self, result_dir, url):
        file = "settings.json"

        if isfile(file):
            os.remove(file)

        settings = {'result_dir': result_dir, 'url': url}

        try:
            f = open(file, "w+")
            json.dump(settings, f)
        finally:
            f.close()

    def run(self):
        self.window = self.make_window('dark grey 9')
        try:

            while True:
                event, values = self.window.read()

                if event == sg.WINDOW_CLOSED or event == 'Exit':
                    break

                elif event == 'Download':
                    self.window['-OUTPUT-'].Update('')
                    if not values['-FOLDER-']:
                        print("[ERR] Keinen Zielordner angegeben!")
                        self.debug.append("[ERR] Keinen Zielordner angegeben!")

                    elif not values['-LINK-']:
                        self.debug.append("[ERR] Keinen Playlistlink angegeben!")

                    else:
                        show_chrome = values['-SHOWCHROME-']
                        self.result_dir = values['-FOLDER-']
                        self.url = values['-LINK-']

                        self.save_settings(self.result_dir, self.url)

                        self.progress_bar = self.window['-PROGRESS BAR-']

                        songs = self.get_songs(self.url)

                        downloaded_tracks = self.check_dir(self.dl_path)

                        song_count = len(songs) - len(downloaded_tracks)

                        self.progress_bar.update_bar(1, song_count*2)


                        try:
                            self.create_browser(show_chrome)

                            song_array = self.get_dl_links(songs, downloaded_tracks)

                            self.download_from_links(song_array)
                        finally:
                            self.tear_down()
        except Exception as e:
            tb = traceback.format_exc()
            self.debug.append(tb)

        finally:
            print("[LOG] Exiting..")
            self.debug.append("[LOG] Exiting..")
            self.window['-OUTPUT-'].__del__()
            self.window.close()

    def tear_down(self):
        self.driver.quit()

    def print_debug(self):
        os.remove("debug.txt")
        i = 0
        f = open("debug.txt", "a+")
        for message in self.debug:
            print("[" + str(i) + "] " + message)
            f.write("[" + str(i) + "] " + message + "\n")
            i += 1
        f.close()

    def make_window(self, theme):
        sg.theme(theme)

        dir_input = [
            sg.Text("Zielordner auswählen"),
            sg.In(size=(90, 10), enable_events=True, key="-FOLDER-", default_text=self.result_dir),
            sg.FolderBrowse()
        ]

        link_input = [
            sg.Text("Playlistlink eingeben"),
            sg.In(size=(90, 10), enable_events=True, key="-LINK-", default_text=self.url),
        ]

        output = [
            sg.Output(size=(110, 30), background_color='white', text_color='black', key='-OUTPUT-')
        ]

        sg.SetOptions(progress_meter_color=('green', 'white'))
        progress_bar = [
            sg.ProgressBar(1000, orientation='h', size=(72, 20), key='-PROGRESS BAR-')
        ]

        buttons = [
            sg.Button('Exit'),
            sg.Checkbox('show Chrome', pad=((550, 0), 0), default=False, key='-SHOWCHROME-'),
            sg.Button('Download', pad=((50, 0), 0)),
        ]

        layout = [
            [dir_input],
            [link_input],
            [output],
            [progress_bar],
            [buttons]
        ]

        return sg.Window("Spotify Downloader", layout)


if __name__ == '__main__':
    sd = SpotifyDownloader()
    try:
        sd.run()
    except Exception as err:
        tb = traceback.format_exc()
        print(err)
        print(tb)
        sd.tear_down()
    finally:
        sd.tear_down()
        sd.print_debug()
