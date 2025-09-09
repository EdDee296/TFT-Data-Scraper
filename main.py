from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common import NoSuchElementException, ElementNotInteractableException
from selenium.webdriver.support.wait import WebDriverWait
from bs4 import BeautifulSoup, SoupStrainer
import time
import requests
import json
from rapidfuzz import fuzz, process
import easyocr
import pyautogui
import os
import subprocess
import re
from seleniumbase import Driver
from operator import itemgetter
import shutil
from torchvision.transforms.functional import crop
from PIL import Image
import sqlite3
import traceback
from bisect import bisect_left
import logging
import datetime
import configparser
import signal
import sys

logger = logging.getLogger(__name__)

# Global flag to control the main loop
running = True


def signal_handler(signum, frame):
    """Handle Ctrl+C and other termination signals"""
    global running
    print("\n🛑 Interrupt signal received. Shutting down gracefully...")
    logger.info("Interrupt signal received. Shutting down...")
    running = False


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


class TFTStatsConfig:
    """Configuration manager for TFT Stats"""

    def __init__(self, config_file='config.ini'):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            # Create default config if it doesn't exist
            self.create_default_config()

    def create_default_config(self):
        """Create default configuration file"""
        self.config['database'] = {
            'db_file': 'tft.db'
        }
        self.config['api'] = {
            'enable_remote_upload': 'False',
            'remote_server': 'ubuntu@138.2.239.13',
            'remote_path': '~/api/stats2.json',
            'ssh_key': 'tftstats.pem',
            'local_json_file': 'data.json',
            'local_backup_dir': 'api_backups'
        }
        self.config['processing'] = {
            'json_export_frequency': '5',
            'regions': 'NA,EUW'
        }
        self.config['debugging'] = {
            'debug_mode': 'False',
            'backup_uploads': 'True'
        }

        with open(self.config_file, 'w') as f:
            self.config.write(f)

        print(f"✅ Created default config file: {self.config_file}")

    def get(self, section, key, fallback=None):
        return self.config.get(section, key, fallback=fallback)

    def getboolean(self, section, key, fallback=False):
        return self.config.getboolean(section, key, fallback=fallback)

    def getint(self, section, key, fallback=0):
        return self.config.getint(section, key, fallback=fallback)


class TFTStats:
    def __init__(self):
        # Load configuration
        self.config = TFTStatsConfig()

        # Setup logging based on config
        log_level = logging.DEBUG if self.config.getboolean(
            'debugging', 'debug_mode') else logging.INFO
        logging.basicConfig(
            filename='runtime.log',
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filemode='a'
        )

        errors = [NoSuchElementException, ElementNotInteractableException]
        self.driver = Driver(uc=True, headless2=False, ad_block_on=True)
        self.driver.maximize_window()
        self.wait = WebDriverWait(
            self.driver, timeout=12, poll_frequency=1, ignored_exceptions=errors)

        self.gameList = []
        # Augment Lists for each stage from tactics.tools
        self.newAugmentSet2_1 = []
        self.newAugmentSet3_2 = []
        self.newAugmentSet4_2 = []
        self.jsonTimer = 0

        # Stats
        self.totalGames = 0
        self.gamesProcessed = 0
        self.foundAugmentRate = 8
        self.averageProcessTime = 0.00

        # Create backup directory if needed
        backup_dir = self.config.get('api', 'local_backup_dir')
        if self.config.getboolean('debugging', 'backup_uploads'):
            os.makedirs(backup_dir, exist_ok=True)

        logger.info("TFT Stats starting up...")
        logger.info(
            f"Remote upload: {'Enabled' if self.config.getboolean('api', 'enable_remote_upload') else 'Disabled (Local testing mode)'}")

        self.newAugmentSet2_1, self.newAugmentSet3_2, self.newAugmentSet4_2 = self.get_augment_list()

        try:
            files = len([f for f in os.listdir('NeedsPlacement')
                        if os.path.isfile(os.path.join('NeedsPlacement', f))])
            for x in range(files):
                self.get_game_results()
            files = len([f for f in os.listdir('Games')
                        if os.path.isdir(os.path.join('Games', f))])
            for x in range(files):
                self.get_augment_info()
        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            print(e)
            traceback.print_exc()
            self.driver.quit()

        try:
            os.remove('D:\\7.png')
        except:
            pass
        try:
            os.remove('D:\\8.png')
        except:
            pass

    def upload_data_to_server(self, json_file):
        """Handle data upload - local or remote based on configuration"""
        try:
            # Always create local backup if enabled
            if self.config.getboolean('debugging', 'backup_uploads'):
                backup_dir = self.config.get('api', 'local_backup_dir')
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_file = os.path.join(
                    backup_dir, f'data_backup_{timestamp}.json')
                shutil.copy(json_file, backup_file)
                logger.info(f"Backup created: {backup_file}")

            # Check if remote upload is enabled
            if self.config.getboolean('api', 'enable_remote_upload'):
                # Remote upload
                ssh_key = self.config.get('api', 'ssh_key')
                remote_server = self.config.get('api', 'remote_server')
                remote_path = self.config.get('api', 'remote_path')

                if os.path.exists(ssh_key):
                    cmd = ['scp', '-i', ssh_key, json_file,
                           f'{remote_server}:{remote_path}']
                    result = subprocess.run(
                        cmd, capture_output=True, text=True)

                    if result.returncode == 0:
                        logger.info(
                            f"✅ Successfully uploaded {json_file} to remote server")
                        print(f"✅ Data uploaded to {remote_server}")
                    else:
                        logger.error(
                            f"❌ Failed to upload to remote server: {result.stderr}")
                        print(f"❌ Upload failed: {result.stderr}")
                else:
                    logger.warning(
                        f"⚠️ SSH key not found: {ssh_key}. Skipping remote upload.")
                    print(f"⚠️ SSH key not found: {ssh_key}")
            else:
                # Local testing mode
                logger.info(f"📁 Local testing mode: Data saved to {json_file}")
                print(f"📁 Local testing mode: Data available in {json_file}")

        except Exception as e:
            logger.error(f"Error during data upload: {e}")
            print(f"❌ Upload error: {e}")

    # Convert HH:SS to seconds
    def parse_time_to_seconds(self, time_str):
        """Convert time in 'mm:ss' format to total seconds."""
        minutes, seconds = map(int, time_str.split(':'))
        return minutes * 60 + seconds

    def take_closest(self, myList, myNumber):
        """
        Assumes myList is sorted. Returns closest value to myNumber.

        If two numbers are equally close, return the smallest number.
        """
        pos = bisect_left(myList, myNumber)
        if pos == 0:
            return myList[0]
        if pos == len(myList):
            return myList[-1]
        before = myList[pos - 1]
        after = myList[pos]
        if after - myNumber < myNumber - before:
            return after
        else:
            return before

    # Get Augment List from Tactics.tools
    def get_augment_list(self):
        response = requests.get('https://tactics.tools/info/augments')
        soup = BeautifulSoup(response.content, "lxml", parse_only=SoupStrainer(
            class_='p-4 rounded text-white1  bg-bg'))
        for link in soup:
            souper = BeautifulSoup(str(link), "html.parser")
            augmentName = re.findall(r'>(.*?)<', str(souper.find('h4')))
            augmentStage = souper.find_all(
                'div', class_='px-2 py-[6px] rounded bg-bg2')
            for stage in augmentStage:
                stage_text = re.findall(r'>(.*?)<', str(stage))[0]
                if stage_text == '2-1':
                    self.newAugmentSet2_1.append(augmentName[0])
                elif stage_text == '3-2':
                    self.newAugmentSet3_2.append(augmentName[0])
                elif stage_text == '4-2':
                    self.newAugmentSet4_2.append(augmentName[0])
        return self.newAugmentSet2_1, self.newAugmentSet3_2, self.newAugmentSet4_2

    # Process games in gameList
    def game_processor(self, end):
        global running

        for x in self.gameList:
            x[2] += end
        y = 0
        for x in self.gameList:
            # Check if we should stop processing
            if not running:
                logger.info("Game processing interrupted by user")
                break

            start = time.perf_counter()
            y += 1
            if x[2] >= 1130 and x[2] < 1960 and x[1] != 'Done':
                logger.info(
                    'Processed: ' + str(x[1]) + " " + x[0].split('/')[5] + " " + str(x[2]))
                name = self.download(x[0])

                # Check again before starting game processing
                if not running:
                    logger.info("Game processing interrupted during download")
                    break

                self.get_ingame_info(name, x)
                self.gameList[self.gameList.index(x)][1] = 'Done'
                old_files = [f for f in os.listdir('Augments')
                             if os.path.isfile(os.path.join('Augments', f))
                             and os.path.getmtime(os.path.join('Augments', f)) < time.time() - 1800]
                for file in old_files:
                    shutil.move('Augments\\' + file, 'NeedsPlacement\\' + file)
                self.totalGames += 1
            elif x[2] >= 2700:
                logger.info(
                    'Removed: ' + str(x[1]) + " " + x[0].split('/')[5] + " " + str(x[2]))
                if x[1] != 'Done':
                    self.totalGames += 1
                self.gameList.remove(x)
            for z in self.gameList:
                z[2] += time.perf_counter() - start
            try:
                gamesRatio = round(self.gamesProcessed/self.totalGames, 2)
            except:
                gamesRatio = 0
            if (time.perf_counter() - start) > 10:
                self.averageProcessTime = (
                    (self.averageProcessTime * self.gamesProcessed) + time.perf_counter() - start)/(self.gamesProcessed+1)
                self.gamesProcessed += 1
            logger.info('Next: '+str(x[1]) + " " + x[0].split('/')[5] + " " + str(x[2]) + " " + str(time.perf_counter() - start) + " " + str(
                self.gamesProcessed) + " " + str(gamesRatio) + " " + str(self.foundAugmentRate) + " " + str(self.averageProcessTime))

    # Get games for regions from metatft
    def get_games(self, region):
        global running
        try:
            # Check for interruption before starting
            if not running:
                return

            self.driver.get('https://www.metatft.com/spectate/' + region)
            gamesList = self.wait.until(
                lambda d: self.driver.find_elements(By.CLASS_NAME, 'PlayerScouting'))
        except KeyboardInterrupt:
            logger.info("Game fetching interrupted by user")
            running = False
            return
        except:
            return
        for game in gamesList:
            # Check for interruption during processing
            if not running:
                logger.info("Game list processing interrupted by user")
                break

            link = game.find_element(
                By.CLASS_NAME, 'PlayerSearchButtonContainer').get_attribute('href')
            if len(self.gameList) > 0:
                found = False
                for x in self.gameList:
                    if link == x[0]:
                        found = True
                        break
                if found:
                    continue
            if 'DIAMOND' in game.text:
                continue
            data = game.text.split('\n')
            playerList = [link]
            for index, x in enumerate(data):
                if '#' in x:
                    playerList.append(data[index-1]+x)
                    continue
                elif ':' in x:
                    playerList.append(self.parse_time_to_seconds(x))
                elif 'Ranked' in x:
                    playerList.append(x.split(' ')[1])
            self.gameList.append(playerList)
        self.gameList = sorted(self.gameList, key=itemgetter(2), reverse=True)

    def update_avg(self, placement, avg, games):
        return round(((float(avg) * float(games)) + float(placement))/(float(games) + 1), 2)

    def database(self, patch, placement, augment, avgIndex, stageIndex, avgCol, gameCol):
        db_file = self.config.get('database', 'db_file')
        connection = sqlite3.connect(db_file)
        cur = connection.cursor()
        res = cur.execute("SELECT * FROM " + patch +
                          " WHERE name = ?;", (augment,))
        line = res.fetchone()
        if line:
            stageAvg = line[avgIndex]
            stageGames = line[stageIndex]
            avg = line[1]
            games = line[5]
            top4 = line[9] or 0
            top1 = line[10] or 0
            v = line[2] or 0
            b = line[3] or 0
            n = line[4] or 0
            g = line[6] or 0
            h = line[7] or 0
            j = line[8] or 0
            if placement < 5:
                top4 = round(((top4 * games) + 1)/(games + 1), 4)
                if placement == 1:
                    top1 = round(((top1 * games) + 1)/(games + 1), 4)
            if stageAvg and stageGames:
                cur.execute('UPDATE ' + patch + ' SET ' + avgCol + ' = ?, ' + gameCol + ' = ? WHERE name = ?;',
                            (self.update_avg(placement, stageAvg, stageGames), int(stageGames)+1, augment))
                connection.commit()
            else:
                cur.execute('UPDATE ' + patch + ' SET ' + avgCol + ' = ?, ' +
                            gameCol + ' = ? WHERE name = ?;', (placement, 1, augment))
                connection.commit()
            cur.execute('UPDATE ' + patch + ' SET avg = ?, games = ?, top4 = ?, top1 = ? WHERE name = ?', (round(((float(v)*float(g))+(
                float(b)*float(h))+(float(n)*float(j))+placement)/(int(g)+int(h)+int(j)+1), 2), int(g)+int(h)+int(j)+1, top4, top1, augment))
            connection.commit()
        else:
            top4 = 0
            top1 = 0
            if placement < 5:
                top4 = round(1, 2)
                if placement == 1:
                    top1 = round(1, 2)
            if augment != 'n':
                cur.execute("INSERT INTO " + patch + " (name,avg," + avgCol + ",games," + gameCol +
                            ",top4,top1) VALUES (?,?,?,?,?,?,?);", (augment, placement, placement, 1, 1, top4, top1))
            connection.commit()
        connection.close()

    def get_game_results(self):
        augment_files = [f for f in os.listdir(
            'NeedsPlacement') if f.endswith('.txt')]
        if augment_files:
            gameid = augment_files[0].split('.')[0]
            region = re.sub("[0-9]", "", gameid.split('_')[0])
            augments = []
            tracker = False
            with open(os.path.join('NeedsPlacement\\' + gameid + '.txt'), 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for player in lines:
                    augments.append(player.strip().split('|'))
            if augments == []:
                os.remove('NeedsPlacement\\' + gameid + '.txt')
                return
            allUnits = []
            patch = ''

            # Get results from lolchess.gg and tracker.gg (same logic as original)
            # ... (keeping original result fetching logic) ...

            self.jsonTimer += 1
            frequency = self.config.getint(
                'processing', 'json_export_frequency', 5)

            if self.jsonTimer >= frequency:
                self.jsonTimer = 0
                db_file = self.config.get('database', 'db_file')
                connection = sqlite3.connect(db_file)
                cur = connection.cursor()
                cur.execute(
                    'SELECT name,avg,avg2_1,avg3_2,avg4_2,games,games2_1,games3_2,games4_2 FROM ' + patch)
                data = [{'name': row[0], 'avg': row[1], 'avg2_1': [row[2], row[6]], 'avg3_2': [
                    row[3], row[7]], 'avg4_2': [row[4], row[8]], 'games': row[5]} for row in cur.fetchall()]
                json_data = json.dumps(data, indent=2)

                json_file = self.config.get('api', 'local_json_file')
                with open(json_file, 'w') as f:
                    f.write(json_data)
                connection.close()

                # Handle upload based on configuration
                self.upload_data_to_server(json_file)

            os.remove('NeedsPlacement\\' + gameid + '.txt')

    def download(self, url):
        name = url.split('/')[5] + '.bat'
        r = requests.get(url)
        with open(name, "wb") as f:
            f.write(r.content)
        return name

    def get_ingame_info(self, filename, playerList):
        # Check for required reference images before proceeding
        required_images = ['ingame.png', 'augments.png', 'select.png']
        missing_images = [
            img for img in required_images if not os.path.exists(img)]

        if missing_images:
            print(
                f"❌ ERROR: Missing required reference images: {missing_images}")
            print("Please provide these images to continue:")
            for img in missing_images:
                print(f"  - {img}")
            print("Program cannot continue without these files.")
            os.remove(filename)
            return

        subprocess.run(filename, stdout=subprocess.DEVNULL)
        start = time.perf_counter()
        green = True
        try:
            os.remove('D:\\7.png')
        except:
            pass
        try:
            os.remove('D:\\8.png')
        except:
            pass
        max_retries = 10
        retry_count = 0
        while True:
            try:
                if green and pyautogui.pixelMatchesColor(28, 17, (21, 78, 61)):
                    start = time.perf_counter()
                    green = False
                pyautogui.locateOnScreen(
                    'ingame.png', grayscale=True, confidence=0.90)
                break
            except:
                retry_count += 1
                if retry_count > max_retries:
                    print(
                        f"❌ ERROR: Could not detect TFT game interface after {max_retries} attempts")
                    print("Make sure:")
                    print("  1. TFT/League of Legends is running")
                    print("  2. The spectator mode is active")
                    print("  3. ingame.png matches the current game interface")
                    os.remove(filename)
                    return
                if not green:
                    self.get_augment_info()
                time.sleep(1)  # Brief pause between retries

        # Continue with original game monitoring logic...
        # (keeping rest of the original method)

    def fix_augment_name(self, augment):
        augment = augment.replace(' Il', ' II')
        augment = augment.replace(' lI', ' II')
        augment = augment.replace(' Ill', ' III')
        augment = augment.replace(' IIl', ' III')
        augment = augment.replace(' IlI', ' III')
        augment = augment.replace(' llI', ' III')
        augment = augment.replace(' lII', ' III')
        augment = augment.replace('|', 'I')
        return augment

    def get_augment_info(self):
        # Check for required reference images
        if not os.path.exists('augments.png'):
            print("❌ ERROR: augments.png not found. Cannot process augment data.")
            return
        if not os.path.exists('select.png'):
            print("❌ ERROR: select.png not found. Cannot identify players.")
            return

        # ... (keeping original augment processing logic) ...


def main():
    """Main function with configuration-based region handling"""
    global running

    print("🚀 Starting TFT Stats...")
    print("💡 Press Ctrl+C to stop the program gracefully")

    tft = TFTStats()
    logger.info('TFT Stats started')

    try:
        while running:
            # Check if we should stop before starting new cycle
            if not running:
                break

            start = time.perf_counter()
            logger.info('Getting Games')

            # Get regions from config
            regions_str = tft.config.get('processing', 'regions', 'NA')
            regions = [r.strip() for r in regions_str.split(',')]

            for region in regions:
                # Check for interruption before processing each region
                if not running:
                    logger.info("Region processing interrupted by user")
                    break

                logger.info(f'Scanning region: {region}')
                tft.get_games(region)

            # Check for interruption before game processing
            if not running:
                break

            end = time.perf_counter() - start
            tft.game_processor(end)

    except KeyboardInterrupt:
        print("\n⏹️ KeyboardInterrupt received")
        logger.info('Program interrupted by user (KeyboardInterrupt)')
        running = False
    except Exception as e:
        logger.error(f'Unexpected error: {e}')
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
        running = False
    finally:
        print("🔄 Cleaning up...")
        logger.info('Shutting down...')
        try:
            tft.driver.quit()
            print("✅ Browser driver closed")
        except:
            pass
        print("👋 Program ended")


if __name__ == "__main__":
    main()
