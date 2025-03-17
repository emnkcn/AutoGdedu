# 导入标准库
import json
import logging
import math
import random
import re
import sys
import time
import traceback

# 导入第三方库
from io import BytesIO
from PIL import Image, ImageTk
import base64
import pickle

# 导入Selenium相关库
from selenium import webdriver
from selenium.common import WebDriverException
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
    TimeoutException,
    ElementNotInteractableException
)
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

# 导入tkinter库
import tkinter as tk


scene = 0

# 配置 logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # 设置全局日志级别
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(name)s %(message)s'
)
file_handler = logging.FileHandler('error.log', mode='w')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.ERROR)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def short_sleep():
    interval = random.uniform(4, 8)
    time.sleep(interval)

def long_sleep():
    interval = random.uniform(30, 60)
    time.sleep(interval)

def until_ready():
    WebDriverWait(driver, 30).until(
        lambda driver: driver.execute_script('''
return document.readyState === 'complete' && 
       (typeof jQuery === 'undefined' || jQuery.active === 0) &&
       (typeof angular === 'undefined' || angular.element(document).injector().get('$http').pendingRequests.length === 0);
'''))

def login_dialog(image_base64=None) -> tuple:
    root = tk.Tk()
    root.title('登录')

    try:
        with open(f'userinfo_{scene}.pkl', 'rb') as f:
            userinfo = pickle.load(f)
    except FileNotFoundError:
        userinfo = {}

    username_label = tk.Label(root, text='Username:')
    username_label.grid(row=0, column=0, padx=5, pady=5)
    username_entry = tk.Entry(root)
    if 'name' in userinfo:
        username_entry.insert(0, userinfo['name'])
    username_entry.grid(row=0, column=1, padx=5, pady=5)

    password_label = tk.Label(root, text='Password:')
    password_label.grid(row=1, column=0, padx=5, pady=5)
    password_entry = tk.Entry(root, show='*')
    if 'password' in userinfo:
        password_entry.insert(0, userinfo['password'])
    password_entry.grid(row=1, column=1, padx=5, pady=5)

    if image_base64 is not None:
        image_bytes = base64.b64decode(image_base64.split(',')[1])
        image = Image.open(BytesIO(image_bytes))
        tk_image = ImageTk.PhotoImage(image)
        image_label = tk.Label(root, image=tk_image)
        image_label.grid(row=2, column=0, padx=5, pady=5)
        captcha_entry = tk.Entry(root)
        captcha_entry.grid(row=2, column=1, padx=5, pady=5)

    username = ''
    password = ''
    captcha = ''

    def login_button_click():
        nonlocal username, password, captcha
        username = username_entry.get()
        password = password_entry.get()
        if image_base64 is not None:
            captcha = captcha_entry.get()
        root.quit()
        root.destroy()

    if image_base64 is not None:
        captcha_entry.bind("<Return>", login_button_click)
    password_entry.bind("<Return>", login_button_click)

    login_button = tk.Button(root, text='Login', command=login_button_click)
    login_button.grid(row=3, column=0, padx=5, pady=5)
    root.mainloop()

    if username and password:
        userinfo['name'] = username
        userinfo['password'] = password
        with open(f'userinfo_{scene}.pkl', 'wb') as f:
            pickle.dump(userinfo, f)

    return username, password, captcha


def public_required_course():
    def answer_question():
        try:
            # 出现答题弹窗
            question = driver.find_element(by=By.ID, value='questionDiv')
            logger.debug(question.get_attribute('outerHTML'))
            function_code = driver.execute_script("return window.finishTest.toString();")
            # 提取if ('Choice0'.includes(',')) {中的 Choice0
            pattern = r"if \('([^']+)'\.includes"
            match = re.search(pattern, function_code)
            answer = ''
            if match:
                answer: str = match.group(1)
                logger.info(f"提取的答案是: {answer}")
            else:
                logger.error(f"提取答案失败 {function_code}")
            answer_list = [answer, ]
            if ',' in answer:
                answer_list = json.loads(answer)
            for choice in answer_list:
                driver.find_element(by=By.CSS_SELECTOR, value=f'input[name="response"][value="{choice}"]').click()
            driver.find_element(by=By.CSS_SELECTOR, value='#questionDiv > div > div > div > div > a > button').click()
        except NoSuchElementException:
            pass

    # 登录页
    driver.get('https://jsglpt.gdedu.gov.cn/login.jsp')
    until_ready()
    captcha_image_element = driver.find_element(by=By.ID, value='loginCaptcha')
    captcha_image_base64 = captcha_image_element.get_attribute('src')

    username, password, captcha = login_dialog(captcha_image_base64)
    if username and password and captcha:
        pass
    else:
        logger.error('未输入全部信息')
        return

    username_element = driver.find_element(by=By.ID, value="userName")
    username_element.send_keys(username)
    password_element = driver.find_element(by=By.ID, value="password")
    password_element.send_keys(password)
    captcha_element = driver.find_element(by=By.ID, value='captcha')
    captcha_element.send_keys(captcha)

    submit_button = driver.find_element(by=By.CSS_SELECTOR, value='.main-btn1.btn')
    submit_button.click()
    until_ready()
    short_sleep() # TODO: 各种显示等待都没搞定
    # 检查是否登录成功
    login_hint = driver.find_elements(By.CSS_SELECTOR, '.login-popup-hint')
    if len(login_hint) > 0:
        hint = ''.join(list(map(lambda e: e.text, login_hint)))
        logger.error(f'登录失败：{hint}')
        return

    # 登录成功页面
    # 改密码弹窗
    try:
        # 等待弹窗出现
        time.sleep(1)
        close_layer_element = driver.find_element(by=By.CSS_SELECTOR, value='.layui-layer-close')
        close_layer_element.click()
    except NoSuchElementException:
        pass

    public_required_course_button = driver.find_element(by=By.CSS_SELECTOR, value='#g-user-cont > div.g-mn > ul > li:nth-child(4) > a')
    window_num = len(driver.window_handles)
    public_required_course_button.click()
    WebDriverWait(driver, 30).until(lambda driver: len(driver.window_handles) != window_num)

    # 切换到公需课页面
    driver.switch_to.window(driver.window_handles[-1])
    course_list_handle = driver.current_window_handle
    until_ready()
    driver.save_screenshot('public_required_course.png')

    start_course_buttons = driver.find_elements(by=By.LINK_TEXT, value='开始学习')
    logger.info(f'未完成学习课程数量：{len(start_course_buttons)}')
    for start_course_button in start_course_buttons:
        course_name = start_course_button.find_element(by=By.XPATH, value='./preceding-sibling::*[3]').text
        logger.info(f'开始学习课程《{course_name}》')
        window_num = len(driver.window_handles)
        start_course_button.click()
        WebDriverWait(driver, 30).until(lambda driver: len(driver.window_handles) != window_num)
        # 切换到课程页面
        driver.switch_to.window(driver.window_handles[-1])
        until_ready()
        driver.save_screenshot(f'{course_name}.png')
        toc = driver.find_elements(by=By.CSS_SELECTOR, value='.section.tt-s')
        chapter_total = len(toc)
        logger.info(f'共{chapter_total}个章节')
        for i in range(0, chapter_total):
            # 规避刷新页面后element失效导致的selenium.common.exceptions.StaleElementReferenceException
            short_sleep()
            toc = driver.find_elements(by=By.CSS_SELECTOR, value='.section.tt-s')
            if i >= len(toc):
                break
            chapter = toc[i]
            heading = chapter.find_element(by=By.XPATH, value='../../child::*[1]')
            if heading.get_attribute('class') != 'z-crt':
                if not heading.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView();", heading)
                heading.click()
                WebDriverWait(driver, 30).until(
                    lambda driver: heading.get_attribute('class') == 'z-crt'
                )
                toc = driver.find_elements(by=By.CSS_SELECTOR, value='.section.tt-s')
                chapter = toc[i]
            chapter_name = heading.text + '/' + chapter.text
            if not chapter.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView();", chapter)
            chapter.click()
            until_ready()
            prompt = driver.find_element(by=By.CSS_SELECTOR, value='.g-study-prompt')
            if '您已完成观看' in prompt.text:
                logger.info(f'{chapter_name} 已完成')
            else:
                answer_question()
                try:
                    driver.find_element(by=By.ID, value='playerDiv')
                except NoSuchElementException:
                    logger.info(f'{chapter_name} 章节无视频，跳过')
                    continue
                logger.info(f'{chapter_name} 开始学习')
                driver.execute_script('player.playOrPause();player.videoMute();')
                while True:
                    meta = json.loads(driver.execute_script('return JSON.stringify(player.getMetaDate());'))
                    duration = meta['duration']
                    cur_time = driver.execute_script('return player.time')
                    logger.info(f'{chapter_name} 播放进度：{cur_time}/{duration}')
                    if math.isclose(cur_time, duration, abs_tol=0.1):
                        logger.info(f'{chapter_name} 已完成观看')
                        break

                    # 有时会播放时间错误，导致没有播完就暂停
                    if meta['paused']:
                        driver.execute_script('player.playOrPause();player.videoMute();')

                    answer_question()
                    driver.execute_script('player.videoMute();')
                    short_sleep()
        logger.info(f'课程《{course_name}》学习完成')
        driver.close()
        driver.switch_to.window(course_list_handle)
    logger.info(f'全部完成')


def happy_holiday():
    # 登录页
    if scene == 2:
        driver.get('https://teacher.higher.smartedu.cn/h/subject/winter2025/')
    elif scene == 3:
        driver.get('https://teacher.vocational.smartedu.cn/h/subject/winter2025/')
    else:
        return
    login_element = driver.find_element(By.CSS_SELECTOR, '#loginHtml > div > div.register > a')
    login_element.click()
    username, password, _ = login_dialog()
    if username and password:
        pass
    else:
        print('未输入全部信息')
        return

    login_iframe = driver.find_element(By.CSS_SELECTOR, 'body > div.content > div.layout > div.loginitme > iframe')
    driver.switch_to.frame(login_iframe)
    phone_element = driver.find_element(By.XPATH, '//input[@placeholder="请输入手机号"]')
    phone_element.send_keys(username)
    password_element = driver.find_element(By.XPATH, '//input[@placeholder="请输入密码"]')
    password_element.send_keys(password)
    submit_element = driver.find_element(By.XPATH, '//span[text()="登录"]').find_element(By.XPATH, '..')
    submit_element.click()
    driver.switch_to.default_content()
    # 登录成功
    short_sleep()
    print(driver.find_element(By.CSS_SELECTOR, '#realname_text').text)
    # 课程列表
    classes = driver.find_elements(By.CSS_SELECTOR, 'body > div.content > div.layout > div.news > ul > li')
    class_list_handle = driver.current_window_handle
    for class_element in classes:
        class_title = class_element.find_element(By.CSS_SELECTOR, 'div.news_wrap > div.news_content > a > h2').text
        hours_desc = class_element.find_element(By.CSS_SELECTOR, 'div.news_time > div:nth-child(3)').text
        pattern = r'\d+'
        numbers = re.findall(pattern, hours_desc)
        print(f'{class_title} {hours_desc}')
        if len(numbers) != 2 or numbers[0] == numbers[1]:
            continue
        time_needed = int(numbers[1]) * 60
        time_left = time_needed
        class_link_element = class_element.find_element(By.CSS_SELECTOR, 'div.news_wrap > div.news_content > a')
        if not class_link_element.is_displayed():
            driver.execute_script("arguments[0].scrollIntoView();", class_link_element)
        class_link_element.click()
        short_sleep()
        # 切换到课程目录页面
        driver.switch_to.window(driver.window_handles[-1])
        # 开始学习
        WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#startStudy'))).click()
        short_sleep()

        # 遍历目录
        toc = driver.find_elements(By.CSS_SELECTOR, 'div.video-title')
        for i in range(len(toc)):
            # 处理学习指南弹窗
            try:
                driver.find_element(By.CSS_SELECTOR, '#notice-dialog > div.guide-footer > label > input').click()
                time.sleep(10)
                guide_know_element = WebDriverWait(driver, 30).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '#guideKnow')))
                guide_know_element.click()
                short_sleep()
            except (NoSuchElementException, TimeoutException):
                pass

            # 处理提示弹窗
            try:
                driver.find_element(By.CSS_SELECTOR, 'div.layui-layer-btn > a').click()
                toc = driver.find_elements(By.CSS_SELECTOR, 'div.video-title')
                short_sleep()
            except NoSuchElementException:
                pass

            toc = driver.find_elements(By.CSS_SELECTOR, 'div.video-title')
            lesson = toc[i]
            chapter_title = lesson.parent.find_element(By.CSS_SELECTOR, '.chapter-title').text
            name = lesson.find_element(By.CSS_SELECTOR, 'span.two').text

            if time_left <= 0:
                print(f'{class_title} 已修够学时')
                break
            total_time = lesson.find_element(By.CSS_SELECTOR, 'span.three').text
            pattern = r'\d+'
            numbers = re.findall(pattern, total_time)
            total_time_minutes = int(numbers[1])
            time_left = time_left - total_time_minutes

            progress = lesson.find_element(By.CSS_SELECTOR, 'span.four').text
            if progress != '100%':
                print(f'{chapter_title}/{name} {progress} 开始学习')
            else:
                print(f'{chapter_title}/{name} {progress} 已完成')
                continue
            if not lesson.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView();", lesson)
            lesson.click()
            short_sleep()

            while True:
                lesson = driver.find_element(By.CSS_SELECTOR, 'div.video-title.on')
                chapter_title = lesson.parent.find_element(By.CSS_SELECTOR, '.chapter-title').text
                name = lesson.find_element(By.CSS_SELECTOR, 'span.two').text
                # 答题
                try:
                    number = ''
                    answer = 1
                    while True:
                        question_wrapper = driver.find_element(By.CSS_SELECTOR, 'div.question-wrapper')
                        # 答题结束后这个div也不会删除
                        if not question_wrapper.is_displayed():
                            break

                        number = ''
                        answer = 1
                        # 中间蹦出来的题目没有题号
                        try:
                            current_number = question_wrapper.find_element(By.CSS_SELECTOR, "span.number").text
                            if current_number != number:
                                number = current_number
                                answer = 1
                        except NoSuchElementException:
                            pass

                        print(f'{chapter_title}/{name} 课堂练习 {number}')
                        print(f'{question_wrapper.find_element(By.CSS_SELECTOR, "div.question-body").text}')
                        print(f'尝试选择答案{answer}')
                        question_wrapper.find_element(By.CSS_SELECTOR,
                                                      f'div.question-body > ul > li:nth-child({answer}) > i').click()
                        question_wrapper.find_element(By.CSS_SELECTOR, '#submit').click()
                        question_wrapper = driver.find_element(By.CSS_SELECTOR, 'div.question-wrapper')

                        if 'success' not in question_wrapper.find_element(By.CSS_SELECTOR, '#my-answer').get_attribute(
                                'class'):
                            print('回答错误')
                            answer = answer + 1
                        else:
                            print('回答正确')

                        # 最后一道题回答后可能出现弹窗
                        try:
                            driver.find_element(By.CSS_SELECTOR, 'div.layui-layer-btn > a').click()
                        except NoSuchElementException:
                            pass
                        short_sleep()
                        question_wrapper.find_element(By.CSS_SELECTOR, '#submit').click()
                        # 全部回答完毕，自动跳到下一章，同时弹窗
                        time.sleep(5)
                        try:
                            driver.find_element(By.CSS_SELECTOR, 'div.layui-layer-btn > a').click()
                        except NoSuchElementException:
                            pass
                except NoSuchElementException:
                    pass

                video_player = driver.find_element(By.CSS_SELECTOR, '#video-Player')
                actions = ActionChains(driver)
                if 'xgplayer-is-replay' in video_player.get_attribute('class'):
                    print(f'{chapter_title}/{name} 已完成')
                    break
                if 'xgplayer-pause' in video_player.get_attribute('class'):
                    try:
                        video_player.find_element(By.CSS_SELECTOR, 'xg-start').click()
                        short_sleep()
                    except ElementClickInterceptedException:
                        try:
                            driver.find_element(By.CSS_SELECTOR, 'div.layui-layer-btn > a').click()
                        except NoSuchElementException:
                            pass
                if 'xgplayer-volume-muted' not in video_player.get_attribute('class'):
                    try:
                        actions.move_to_element(video_player).perform()
                        video_player.find_element(By.CSS_SELECTOR, 'xg-controls > xg-volume').click()
                    except Exception:
                        pass
                # 二倍速
                try:
                    actions.move_to_element(video_player).perform()
                    playbackrate = video_player.find_element(By.CSS_SELECTOR, '#video-Player > xg-controls > xg-playbackrate > p')
                    if playbackrate.text == '1x':
                        actions.move_to_element(playbackrate)
                        actions.perform()
                        rate2 = video_player.find_element(By.CSS_SELECTOR, 'xg-controls > xg-playbackrate > ul > li:nth-child(1)')
                        #actions = ActionChains(driver).move_to_element(rate2)
                        #actions.perform()
                        rate2.click()
                except (NoSuchElementException, ElementNotInteractableException):
                    pass

                current_lesson = driver.find_element(By.CSS_SELECTOR, '#video-tabContent div.video-title.clearfix.on')
                progress = current_lesson.find_element(By.CSS_SELECTOR, '.four').text
                print(f'{chapter_title}/{name} {progress}')

                if progress == '100%':
                    print(f'{chapter_title}/{name} 已完成')
                    break

                #TODO:
                # 判断学时有没有修够，修够就换下一课
                toc = driver.find_elements(By.CSS_SELECTOR, 'div.video-title')
                total_viewed_time = 0
                for item in toc:
                    if 'on' in item.get_attribute('class'):
                        break
                    pattern = r'\d+'
                    numbers = re.findall(pattern, item.find_element(By.CSS_SELECTOR, 'span.three').text)
                    total_viewed_time += int(numbers[1]) + int(numbers[0]) * 60
                print(f'{chapter_title} 已修章节总时间/需修时间 {total_viewed_time}/{time_needed}')
                if total_viewed_time > time_needed:
                    break
                long_sleep()
        driver.close()
        driver.switch_to.window(class_list_handle)
    print(f'全部完成')


if __name__ == '__main__':
    options = webdriver.EdgeOptions()
    options.add_argument("--no-sandbox")
    # 禁用后台定时器限流
    options.add_argument("--disable-background-timer-throttling")
    # 禁用隐藏窗口的后台处理
    options.add_argument("--disable-backgrounding-occluded-windows")
    # 禁用渲染器后台化
    options.add_argument("--disable-renderer-backgrounding")
    # 禁用休眠
    options.add_argument("--disable-features=CalculateNativeWinOcclusion")
    driver = webdriver.Edge(options=options)

    try:
        print(r'''
1. 公需课
2. 教师研修班（本科）
3. 教师研修班（高职）
        ''')
        scene = input('选择：')
        if scene == '1':
            public_required_course()
        elif scene == '2' or scene == '3':
            happy_holiday()
        else:
            logger.error(f'Scene不存在:{scene}')
    except WebDriverException as e:
        logger.error(str(e))
        logger.error(traceback.format_exc())
        file_name = f'scene_{scene}'
        with open(f'{file_name}.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        driver.save_screenshot(f'{file_name}.png')
    except Exception as e:
        logger.error(str(e))
        logger.error(traceback.format_exc())
