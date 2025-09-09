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

logger = logging.getLogger(__name__)


class TFTStats:
    def __init__(self):
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
        for x in self.gameList:
            x[2] += end
        y = 0
        for x in self.gameList:
            start = time.perf_counter()
            y += 1
            if x[2] >= 1130 and x[2] < 1960 and x[1] != 'Done':
                logger.info(
                    'Processed: ' + str(x[1]) + " " + x[0].split('/')[5] + " " + str(x[2]))
                name = self.download(x[0])
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
                # if os.path.exists('Augments\\' + x[0].split('/')[5] + '.txt'):
                #     # shutil.copy('Augments\\' + x[0].split('/')[5] + '.txt', 'augmentcopy\\' + x[0].split('/')[5] + '.txt')
                #     shutil.move('Augments\\' + x[0].split('/')[5] + '.txt', 'NeedsPlacement\\' + x[0].split('/')[5] + '.txt')
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

    # Get games for NA from metatft
    def get_games(self, region):
        try:
            self.driver.get('https://www.metatft.com/spectate/' + region)
            gamesList = self.wait.until(
                lambda d: self.driver.find_elements(By.CLASS_NAME, 'PlayerScouting'))
        except:
            return
        for game in gamesList:
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
            # [1204, 'Appies', 'vclf', 'Stellar Minhee', 'MrBombastic', 'VIT setsuko', 'iniko', 'Darth Nub', 'TOR Relic']
            # print(data)
            for index, x in enumerate(data):
                if '#' in x:
                    playerList.append(data[index-1]+x)
                    continue
                elif ':' in x:
                    playerList.append(self.parse_time_to_seconds(x))
                elif 'Ranked' in x:
                    playerList.append(x.split(' ')[1])
            # print(playerList)
            self.gameList.append(playerList)
        self.gameList = sorted(self.gameList, key=itemgetter(2), reverse=True)
        # print(self.gameList)

    def update_avg(self, placement, avg, games):
        return round(((float(avg) * float(games)) + float(placement))/(float(games) + 1), 2)

    def database(self, patch, placement, augment, avgIndex, stageIndex, avgCol, gameCol):
        connection = sqlite3.connect('tft.db')
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
            # (name,avg,avg2_1,avg3_2,avg4_2,games,games2_1,games3_2,games4_2,top4,top1)
            if stageAvg and stageGames:
                cur.execute('UPDATE ' + patch + ' SET ' + avgCol + ' = ?, ' + gameCol + ' = ? WHERE name = ?;',
                            (self.update_avg(placement, stageAvg, stageGames), int(stageGames)+1, augment))
                connection.commit()
            else:
                cur.execute('UPDATE ' + patch + ' SET ' + avgCol + ' = ?, ' +
                            gameCol + ' = ? WHERE name = ?;', (placement, 1, augment))
                connection.commit()
            # cur.execute('UPDATE ' + patch + ' SET avg = ?, games = ?, top4 = ?, top1 = ? WHERE name = ?;', (self.update_avg(placement, avg,games),int(games)+1,top4,top1,augment))
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

    # tracker.gg placements
    # lolchess.gg patch number
    def get_game_results(self):
        # start_time = time.perf_counter()
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
            for tries in range(2):
                try:
                    found = True
                    self.driver.get('https://lolchess.gg/profile/' +
                                    region + '/' + augments[0][0].replace('#', '-'))
                    self.driver.find_element(
                        By.CSS_SELECTOR, 'button.updateRecord').click()
                    for x in range(10):
                        try:
                            if self.driver.find_element(By.CSS_SELECTOR, 'button.updateRecord').text == 'Recent':
                                break
                        except:
                            time.sleep(1)
                    self.driver.get('https://lolchess.gg/profile/' +
                                    region + '/' + augments[0][0].replace('#', '-'))
                    matches = self.wait.until(lambda d: self.driver.find_elements(
                        By.CSS_SELECTOR, 'section.match-total'))
                    for game in matches:
                        usernames = self.wait.until(
                            lambda d: game.find_elements(By.CSS_SELECTOR, 'a.username'))
                        x = 0
                        y = 0
                        for player in augments:
                            name = player[0].split("#")[0]
                            x += 1
                            for _ in usernames:
                                if name == _.text:
                                    usernames.remove(_)
                                    y += 1
                        if x == y:
                            self.wait.until(lambda d: game.find_element(
                                By.CSS_SELECTOR, 'button.open-btn')).click()
                            rows = self.wait.until(
                                lambda d: self.driver.find_elements(By.TAG_NAME, 'tr'))
                            for row in rows[1:]:
                                temp = []
                                username = self.wait.until(lambda d: row.find_element(
                                    By.CSS_SELECTOR, 'a.username')).text
                                temp.append(username)
                                placement = self.wait.until(lambda d: row.find_element(
                                    By.CSS_SELECTOR, 'td.num.css-0')).text
                                temp.append(placement)
                                allUnits.append(temp)
                            patch = self.wait.until(lambda d: self.driver.find_element(
                                By.CLASS_NAME, 'play-time-label')).text.split(' ')[2]
                            found = False
                            break
                    if not found:
                        break
                except Exception as e:
                    # logger.info(e)
                    # if tries == 2:
                    #     logger.info('Game result not found')
                    #     os.remove('NeedsPlacement\\' + gameid + '.txt')
                    #     return
                    pass
            if found:
                self.driver.get('https://tracker.gg/tft/match/' + gameid)
                rows = self.driver.find_elements(By.TAG_NAME, 'tr')
                if rows:
                    tracker = True
                if tracker:
                    for data in rows[1:]:
                        temp = []
                        username = data.get_attribute('data-key')
                        temp.append(username)
                        placement = data.find_element(
                            By.CLASS_NAME, 'truncate').text
                        temp.append(placement)
                        # unitPictures = data.find_element(By.CSS_SELECTOR, "div[class='flex justify-start gap-1']")
                        # units = unitPictures.find_elements(By.CSS_SELECTOR, "div[class='flex flex-col items-center relative rounded-1']")
                        # for unit in units:
                        #     unitItems = unit.find_elements(By.TAG_NAME, 'img')
                        #     temp1 = []
                        #     for unit_Items in unitItems:
                        #         temp1.append(unit_Items.get_attribute('alt'))
                        #     temp.append(temp1)
                        allUnits.append(temp)
                    while True:
                        try:
                            self.driver.get(
                                'https://lolchess.gg/profile/' + region + '/' + augments[0][0].replace('#', '-'))
                            break
                        except Exception as e:
                            time.sleep(1)
                    # self.wait.until(lambda d: self.driver.get('https://lolchess.gg/profile/' + region + '/' + allUnits[0][0].replace('#', '-')) or True)
                    self.wait.until(lambda d: self.driver.find_element(
                        By.CSS_SELECTOR, 'button.open-btn')).click()
                    patch = self.wait.until(lambda d: self.driver.find_element(
                        By.CLASS_NAME, 'play-time-label')).text.split(' ')[2]
                else:
                    logger.info('Game result not found')
                    os.remove('NeedsPlacement\\' + gameid + '.txt')
                    return
            patch = re.sub("[^0-9.v]", "", patch)
            patch = patch.replace('.', 'dot')
            connection = sqlite3.connect('tft.db')
            cur = connection.cursor()
            cur.execute(
                'SELECT name,avg,avg2_1,avg3_2,avg4_2,games FROM ' + patch)
            try:
                cur.execute(
                    "CREATE TABLE "+patch+" (name,avg,avg2_1,avg3_2,avg4_2,games,games2_1,games3_2,games4_2,top4,top1)")
                connection.close()
            except:
                pass
            for x in allUnits:
                player = x[0]
                placement = float(x[1])
                for y in augments:
                    if y[0].split('#')[0] == player.split('#')[0]:
                        augment1 = y[1]
                        if augment1:
                            self.database(patch, placement, augment1,
                                          2, 6, 'avg2_1', 'games2_1')
                        augment2 = y[2]
                        if augment2:
                            self.database(patch, placement, augment2,
                                          3, 7, 'avg3_2', 'games3_2')
                        augment3 = y[3]
                        if augment3:
                            self.database(patch, placement, augment3,
                                          4, 8, 'avg4_2', 'games4_2')
                        # database(self, cur, connection, patch, placement, augment, stageAvg, stageGames, avg, games, avgCol, gameCol)
            self.jsonTimer += 1
            if self.jsonTimer > 4:
                self.jsonTimer = 0
                connection = sqlite3.connect('tft.db')
                cur = connection.cursor()
                cur.execute(
                    'SELECT name,avg,avg2_1,avg3_2,avg4_2,games,games2_1,games3_2,games4_2 FROM ' + patch)
                data = [{'name': row[0], 'avg': row[1], 'avg2_1': [row[2], row[6]], 'avg3_2': [
                    row[3], row[7]], 'avg4_2': [row[4], row[8]], 'games': row[5]} for row in cur.fetchall()]
                json_data = json.dumps(data)
                with open('data.json', 'w') as json_file:
                    json_file.write(json_data)
                connection.close()
                subprocess.run(['scp', '-i', 'tftstats.pem', 'data.json',
                               'ubuntu@138.2.239.13:~/api/stats2.json'])
                # scp -i tftstats.pem data.json ubuntu@138.2.239.13:~/api/stats2.json
            # print('SQL commited')
            os.remove('NeedsPlacement\\' + gameid + '.txt')
        # print(time.perf_counter() - start_time)

    def download(self, url):
        name = url.split('/')[5] + '.bat'
        r = requests.get(url)
        # print(r)
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
        # self.get_augment_info()
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
                if (time.perf_counter() - start) > 50:
                    try:
                        pyautogui.locateOnScreen(
                            'ingame.png', grayscale=True, confidence=0.90)
                        break
                    except:
                        os.system(
                            'taskkill /f /IM \"League of Legends.exe\" >nul 2>&1')
                        subprocess.run(filename, stdout=subprocess.DEVNULL)
                        start = time.perf_counter()
                        self.get_game_results()
                        self.get_game_results()
                        self.get_game_results()
                        while True:
                            try:
                                pyautogui.locateOnScreen(
                                    'ingame.png', grayscale=True, confidence=0.9)
                                break
                            except:
                                time.sleep(1)
                                if (time.perf_counter() - start) > 50:
                                    pyautogui.screenshot(
                                        'Timeout1 '+datetime.datetime.now().strftime('%a %d %b %Y, %I-%M%p')+'.png')
                                    os.system(
                                        'taskkill /f /IM \"League of Legends.exe\" >nul 2>&1')
                                    subprocess.run(
                                        filename, stdout=subprocess.DEVNULL)
                                    start = time.perf_counter()
                                    while True:
                                        try:
                                            pyautogui.locateOnScreen(
                                                'ingame.png', grayscale=True, confidence=0.9)
                                            break
                                        except:
                                            if (time.perf_counter() - start) > 30:
                                                pyautogui.screenshot(
                                                    'Timeout3 '+datetime.datetime.now().strftime('%a %d %b %Y, %I-%M%p')+'.png')
                                                os.system(
                                                    'taskkill /f /IM \"League of Legends.exe\" >nul 2>&1')
                                                os.remove(filename)
                                                return
        start = time.perf_counter()
        while True:
            try:
                if (time.perf_counter() - start) > 150:
                    subprocess.Popen(
                        ['pskill', '\\\\192.168.0.6', '-u', 'tim', '-p', 'ukalien1324', 'tvnviewer.exe'])
                    pyautogui.screenshot(
                        'Timeout2 '+datetime.datetime.now().strftime('%a %d %b %Y, %I-%M%p')+'.png')
                    os.system(
                        'taskkill /f /IM \"League of Legends.exe\" >nul 2>&1')
                    os.remove(filename)
                    return
                assert (os.path.isfile('D:\\1.png') == True)
                assert (os.path.isfile('D:\\2.png') == True)
                assert (os.path.isfile('D:\\3.png') == True)
                assert (os.path.isfile('D:\\4.png') == True)
                assert (os.path.isfile('D:\\5.png') == True)
                assert (os.path.isfile('D:\\6.png') == True)
                assert (os.path.isfile('D:\\7.png') == True)
                assert (os.path.isfile('D:\\8.png') == True)
                time.sleep(2)
                os.system('taskkill /f /IM \"League of Legends.exe\" >nul 2>&1')
                break
            except:
                pass
        os.remove(filename)
        folder = 'Games\\' + filename.split('.')[0]
        os.makedirs(folder, exist_ok=True)
        shutil.move('D:\\1.png', folder)
        shutil.move('D:\\2.png', folder)
        shutil.move('D:\\3.png', folder)
        shutil.move('D:\\4.png', folder)
        shutil.move('D:\\5.png', folder)
        shutil.move('D:\\6.png', folder)
        shutil.move('D:\\7.png', folder)
        shutil.move('D:\\8.png', folder)
        with open(os.path.join(folder, 'playerList.txt'), 'w', encoding='utf-8') as f:
            for player in playerList:
                f.write(f"{player}\n")
        # shutil.copytree(folder,'gamescopy\\' + folder)
        # Once every 4 runs, for avoiding game crash
        # if self.repairTimer > 99:
        #     self.repairTimer = 0
        #     self.fix_game()

    def fix_game(self):
        pyautogui.click(841, 864)
        time.sleep(1)
        pyautogui.click(830, 673)
        time.sleep(5)
        for x in range(30):
            try:
                assert (pyautogui.pixelMatchesColor(
                    869, 660, (14, 14, 14)) == True)
                break
            except:
                time.sleep(1)
        pyautogui.click(869, 650)

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

    # Gets Augment info from screenshots
    def get_augment_info(self):
        # Check for required reference images
        if not os.path.exists('augments.png'):
            print("❌ ERROR: augments.png not found. Cannot process augment data.")
            return
        if not os.path.exists('select.png'):
            print("❌ ERROR: select.png not found. Cannot identify players.")
            return

        # start = time.perf_counter()
        names = []
        names_compare = []
        players_left = []
        names_found = []
        names_full = []
        username_and_augments = []
        games_folder = 'Games'
        first_folder = None
        gameID = ''
        folders = [f for f in os.listdir(games_folder) if os.path.isdir(
            os.path.join(games_folder, f))]
        if folders:
            first_folder = folders[0]
            with open('Games\\' + first_folder + '\\playerList.txt', 'r', encoding='utf-8') as f:
                gameID = f.readline().strip().split('/')[5]
                lines = f.readlines()[2:]
                for line in lines:
                    # print(line)
                    names.append(line.strip().split('#')[0])
                    names_compare.append(line.strip().split('#')[0])
                    names_full.append(line.strip())
            # print(names_compare)
            for player in range(1, 9):
                file = 'Games\\' + first_folder + '\\' + str(player) + '.png'
                try:
                    loc = pyautogui.locate(
                        'augments.png', file, grayscale=True, confidence=0.8)
                except Exception as e:
                    print(e)
                    continue
                image = Image.open(file)
                augment1 = crop(image, int(loc.top+135),
                                int(loc.left-3), 45, 186)
                augment2 = crop(image, int(loc.top+207),
                                int(loc.left-3), 45, 186)
                augment3 = crop(image, int(loc.top+282),
                                int(loc.left-3), 45, 186)
                selected = crop(image, 205, 1912, 520, 8)
                try:
                    namelocation = pyautogui.locate(
                        'select.png', selected, grayscale=True, confidence=0.9)
                    yVal = self.take_closest(
                        [184, 255, 328, 400, 472, 544, 616, 688], int(namelocation.top)+205)
                except:
                    match player:
                        case 1:
                            yVal = 184
                        case 2:
                            yVal = 255
                        case 3:
                            yVal = 328
                        case 4:
                            yVal = 400
                        case 5:
                            yVal = 472
                        case 6:
                            yVal = 544
                        case 7:
                            yVal = 616
                        case 8:
                            yVal = 688
                usernamePic = crop(image, yVal, 1620, 40, 195)
                augment1.save('img1.png')
                augment2.save('img2.png')
                augment3.save('img3.png')
                usernamePic.save('img4.png')
                reader = easyocr.Reader(['en', 'vi'])
                result1 = reader.readtext(
                    'img1.png', detail=0, mag_ratio=2.0, paragraph=True)
                result2 = reader.readtext(
                    'img2.png', detail=0, mag_ratio=2.0, paragraph=True)
                result3 = reader.readtext(
                    'img3.png', detail=0, mag_ratio=2.0, paragraph=True)
                result4 = reader.readtext('img4.png', detail=0, mag_ratio=2.0)
                if result1:
                    result1[0] = self.fix_augment_name(result1[0])
                    augment1_match = process.extractOne(
                        result1[0], self.newAugmentSet2_1, scorer=fuzz.ratio)
                    augment1 = augment1_match[0] if augment1_match and augment1_match[1] > 70 else 'none'
                else:
                    augment1 = 'none'
                if result2:
                    result2[0] = self.fix_augment_name(result2[0])
                    augment2_match = process.extractOne(
                        result2[0], self.newAugmentSet3_2, scorer=fuzz.ratio)
                    augment2 = augment2_match[0] if augment2_match and augment2_match[1] > 70 else 'none'
                else:
                    augment2 = 'none'
                if result3:
                    result3[0] = self.fix_augment_name(result3[0])
                    augment3_match = process.extractOne(
                        result3[0], self.newAugmentSet4_2, scorer=fuzz.ratio)
                    augment3 = augment3_match[0] if augment3_match and augment3_match[1] > 70 else 'none'
                else:
                    augment3 = 'none'
                username = None
                if result4:
                    username_match = process.extractOne(
                        result4[0], names, scorer=fuzz.ratio)
                    if username_match and username_match[1] > 70:
                        username = username_match[0]
                    else:
                        username = None
                else:
                    result4 = ['']
                if username and username in names_found:
                    username = None
                # print(result1[0], augment1)
                # print(result2[0], augment2)
                # print(result3[0], augment3)
                # print(username)
                if username:
                    # print(username)
                    names_compare.remove(username)
                    names_found.append(username)
                    for x in names_full:
                        if x.split('#')[0] == username:
                            username_and_augments.append(
                                [x, augment1, augment2, augment3])
                            names_full.remove(x)
                else:
                    players_left.append(
                        [result4[0], augment1, augment2, augment3])
            if len(players_left) == 1 and len(names_compare) == 1:
                for x in names_full:
                    if x.split('#')[0] == names_compare[0]:
                        username_and_augments.append(
                            [x, players_left[0][1], players_left[0][2], players_left[0][3]])
            if len(username_and_augments) > 1:
                with open(os.path.join('Augments\\' + gameID + '.txt'), 'w', encoding='utf-8') as f:
                    for player in username_and_augments:
                        # print(player)
                        for item in player:
                            f.write(item + '|')
                        f.write('\n')
            self.foundAugmentRate = round(
                ((self.foundAugmentRate * self.gamesProcessed) + len(username_and_augments))/(self.gamesProcessed+1), 2)
            # shutil.copy('Augments\\' + gameID + '.txt', 'augmentcopy\\' + gameID + '.txt')
            shutil.rmtree('Games\\' + folders[0])
            # print('Time:', time.perf_counter() - start)


if __name__ == "__main__":
    logging.basicConfig(filename='runtime.log',
                        level=logging.INFO, format='%(asctime)s - %(message)s')
    tft = TFTStats()
    logger.info('Started')
    try:
        while True:
            start = time.perf_counter()
            logger.info('Getting Games')
            tft.get_games('NA')
            # tft.get_games('EUW')
            # tft.get_games('VN')
            # tft.get_games('SEA')
            end = time.perf_counter() - start
            gameList = tft.game_processor(end)
    except Exception as e:
        traceback.print_exc()
        tft.driver.quit()
    tft.driver.quit()
