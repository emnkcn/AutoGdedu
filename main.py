import math
import pickle
import random
import re
import time

from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import json
import tkinter as tk
from io import BytesIO
from PIL import Image, ImageTk
import base64

from selenium.webdriver.support.wait import WebDriverWait

scene = 0

def short_sleep():
    interval = random.uniform(2, 4)
    time.sleep(interval)


def long_sleep():
    interval = random.uniform(30, 60)
    time.sleep(interval)


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

    def login_button_click(e=None):
        nonlocal username, password, captcha
        username = username_entry.get()
        password = password_entry.get()
        if image_base64 is not None:
            captcha = captcha_entry.get()
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
    chrome_options = uc.ChromeOptions()
    # chrome_options.add_argument('--headless')
    driver = uc.Chrome(options=chrome_options,
                       driver_executable_path='./undetected_chromedriver.exe')

    # 登录页
    driver.get('https://jsglpt.gdedu.gov.cn/login.jsp')
    short_sleep()
    captcha_image_element = driver.find_element(by=By.ID, value='loginCaptcha')
    captcha_image_base64 = captcha_image_element.get_attribute('src')

    username, password, captcha = login_dialog(captcha_image_base64)
    if username and password and captcha:
        pass
    else:
        print('未输入全部信息')
        return

    username_element = driver.find_element(by=By.ID, value="userName")
    username_element.send_keys(username)
    password_element = driver.find_element(by=By.ID, value="password")
    password_element.send_keys(password)
    captcha_element = driver.find_element(by=By.ID, value='captcha')
    captcha_element.send_keys(captcha)

    submit_button = driver.find_element(by=By.CSS_SELECTOR, value='.main-btn1.btn')
    submit_button.click()
    short_sleep()

    # 检查是否登录成功
    login_hint = driver.find_elements(by=By.CSS_SELECTOR, value='.login-popup-hint')
    if len(login_hint) > 0:
        hint = ''.join(list(map(lambda e: e.text, login_hint)))
        print(f'登录失败：{hint}')
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

    public_required_course_button = driver.find_element(by=By.CSS_SELECTOR, value='#menu_publicStudy > a')
    public_required_course_button.click()

    # 切换到公需课页面
    driver.switch_to.window(driver.window_handles[-1])
    course_list_handle = driver.current_window_handle
    # driver.save_screenshot('public_required_course.png')

    start_course_buttons = driver.find_elements(by=By.LINK_TEXT, value='开始学习')
    print(f'未完成学习课程数量：{len(start_course_buttons)}')
    for start_course_button in start_course_buttons:
        course_name = start_course_button.find_element(by=By.XPATH, value='./preceding-sibling::*[3]').text
        print(f'开始学习课程《{course_name}》')
        short_sleep()
        start_course_button.click()
        # 切换到课程页面
        driver.switch_to.window(driver.window_handles[-1])
        # driver.save_screenshot(f'{course_name}.png')
        toc = driver.find_elements(by=By.CSS_SELECTOR, value='.section.tt-s')
        chapter_total = len(toc)
        print(f'共{chapter_total}个章节')
        # TODO: change back to 0
        for i in range(20, chapter_total):
            # 规避刷新页面后element失效导致的selenium.common.exceptions.StaleElementReferenceException
            toc = driver.find_elements(by=By.CSS_SELECTOR, value='.section.tt-s')
            chapter = toc[i]
            short_sleep()
            heading = chapter.find_element(by=By.XPATH, value='../../child::*[1]')
            if heading.get_attribute('class') != 'z-crt':
                if not heading.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView();", heading)
                heading.click()
                short_sleep()
            chapter_name = heading.text + '/' + chapter.text
            if not chapter.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView();", chapter)
            chapter.click()
            prompt = driver.find_element(by=By.CSS_SELECTOR, value='.g-study-prompt')
            if '您已完成观看' in prompt.text:
                print(f'{chapter_name} 已完成')
            else:
                try:
                    driver.find_element(by=By.ID, value='playerDiv')
                except NoSuchElementException:
                    #  TODO: 处理答题页面
                    print(f'{chapter_name} 章节无视频，跳过')
                    continue
                print(f'{chapter_name} 开始学习')
                short_sleep()
                driver.execute_script('player.playOrPause();player.videoMute();')
                time.sleep(5)
                while True:
                    meta = json.loads(driver.execute_script('return JSON.stringify(player.getMetaDate());'))
                    duration = meta['duration']
                    cur_time = driver.execute_script('return player.time')
                    # driver.save_screenshot(f'{chapter.text}_{cur_time}.png')
                    print(f'{chapter_name} 播放进度：{cur_time}/{duration}')
                    if math.isclose(cur_time, duration, abs_tol=0.1):
                        print(f'{chapter_name} 已完成观看')
                        break

                    # 有时会播放时间错误，导致没有播完就暂停
                    if meta['paused']:
                        driver.execute_script('player.playOrPause();player.videoMute();')

                    try:
                        # 出现答题弹窗
                        driver.find_element(by=By.ID, value='questionDiv')
                        driver.execute_script("$('#questionDiv').stopTime('C');$('.mylayer-closeico').trigger("
                                              "'click');player.videoPlay();")
                    except NoSuchElementException:
                        pass

                    long_sleep()
        print(f'课程《{course_name}》学习完成')
        driver.close()
        driver.switch_to.window(course_list_handle)
    print(f'全部完成')


def happy_holiday():
    chrome_options = uc.ChromeOptions()
    # chrome_options.add_argument('--headless')
    driver = uc.Chrome(options=chrome_options,
                       driver_executable_path='./undetected_chromedriver.exe')

    # 登录页
    driver.get('https://teacher.higher.smartedu.cn/h/subject/teaching/')
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
    # driver.switch_to.default_content()
    # 登录成功
    short_sleep()
    print(driver.find_element(By.CSS_SELECTOR, '#realname_text').text)
    # 课程列表
    classes = driver.find_elements(By.CSS_SELECTOR, 'body > div.content > div.layout > div.news > ul > li')
    class_list_handle = driver.current_window_handle
    # TODO: 学完一个课程后classes是否会失效？
    for class_element in classes:
        class_title = class_element.find_element(By.CSS_SELECTOR, 'div.news_wrap > div.news_content > a > h2').text
        hours_desc = class_element.find_element(By.CSS_SELECTOR, 'div.news_time > div:nth-child(3)').text
        pattern = r'\d+'
        numbers = re.findall(pattern, hours_desc)
        print(f'{class_title} {hours_desc}')
        if numbers[0] == numbers[1]:
            continue
        class_link_element = class_element.find_element(By.CSS_SELECTOR, 'div.news_wrap > div.news_content > a')
        if not class_link_element.is_displayed():
            driver.execute_script("arguments[0].scrollIntoView();", class_link_element)
        class_link_element.click()
        short_sleep()
        # 切换到课程目录页面
        driver.switch_to.window(driver.window_handles[-1])
        # 开始学习
        driver.find_element(By.CSS_SELECTOR, '#startStudy').click()
        short_sleep()
        # 处理学习指南弹窗
        try:
            driver.find_element(By.CSS_SELECTOR, '#notice-dialog > div.guide-footer > label > input').click()
            driver.find_element(By.CSS_SELECTOR, '#guideKnow').click()
            time.sleep(10)
            guide_know_element = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#guideKnow')))
            guide_know_element.click()
        except NoSuchElementException:
            print('no notice')

        short_sleep()
        # 处理提示弹窗
        try:
            driver.find_element(By.CSS_SELECTOR, 'div.layui-layer-btn > a').click()
        except NoSuchElementException:
            pass

        # 遍历目录
        toc = driver.find_elements(By.CSS_SELECTOR, 'div.video-title')
        for i in range(len(toc)):
            lesson = toc[i]
            chapter_title = lesson.parent.find_element(By.CSS_SELECTOR, '.chapter-title').text
            name = lesson.find_element(By.CSS_SELECTOR, 'span.two').text
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

            try:
                driver.find_element(By.CSS_SELECTOR, 'div.layui-layer-btn > a').click()
            except NoSuchElementException:
                pass

            while True:

                # 答题
                try:
                    number = ''
                    answer = 1
                    while True:
                        question_wrapper = driver.find_element(By.CSS_SELECTOR, 'div.question-wrapper')
                        # 答题结束后这个div也不会删除
                        if not question_wrapper.is_displayed():
                            break
                        current_number = question_wrapper.find_element(By.CSS_SELECTOR, "span.number").text
                        if current_number != number:
                            number = current_number
                            answer = 1
                        print(f'{chapter_title}/{name} 课堂练习 {number}')
                        print(f'{question_wrapper.find_element(By.CSS_SELECTOR, "div.question-body").text}')
                        print(f'尝试选择答案{answer}')
                        question_wrapper.find_element(By.CSS_SELECTOR, f'div.question-body > ul > li:nth-child({answer}) > i').click()
                        question_wrapper.find_element(By.CSS_SELECTOR, '#submit').click()
                        question_wrapper = driver.find_element(By.CSS_SELECTOR, 'div.question-wrapper')
                        if 'success' not in question_wrapper.find_element(By.CSS_SELECTOR, '#my-answer').get_attribute('class'):
                            print('回答错误')
                            answer = answer + 1
                        question_wrapper.find_element(By.CSS_SELECTOR, '#submit').click()
                        # 全部回答完毕，自动跳到下一章，同时弹窗
                        try:
                            driver.find_element(By.CSS_SELECTOR, 'div.layui-layer-btn > a').click()
                        except NoSuchElementException:
                            pass
                except NoSuchElementException:
                    pass

                video_player = driver.find_element(By.CSS_SELECTOR, '#video-Player')
                if 'xgplayer-pause' in video_player.get_attribute('class'):
                    video_player.find_element(By.CSS_SELECTOR, 'xg-start').click()
                    short_sleep()
                # TODO: how to get time?
                time_e = video_player.find_element(By.CSS_SELECTOR, 'xg-time')
                time_current1 = video_player.find_element(By.CSS_SELECTOR, 'xg-controls > xg-time > '
                                                                          'span.xgplayer-time-current')
                time_total1 = video_player.find_element(By.CSS_SELECTOR, 'xg-controls > xg-time > span:nth-child(2)')
                time_current = video_player.find_element(By.CSS_SELECTOR, 'xg-controls > xg-time > '
                                                                          'span.xgplayer-time-current').text
                time_total = video_player.find_element(By.CSS_SELECTOR, 'xg-controls > xg-time > span:nth-child(2)').text
                print(f'{chapter_title}/{name} {time_current}/{time_total}')

                if time_current and time_total1 and time_current == time_total:
                    print(f'{chapter_title}/{name} 已完成')
                    continue
                long_sleep()
            toc = driver.find_elements(By.CSS_SELECTOR, 'div.video-title')

        driver.close()
        driver.switch_to.window(class_list_handle)

    short_sleep()
    input('hi')
    time.sleep(60)


if __name__ == '__main__':
    print(r'''
1. 公需课
2. 暑期教师研修班
    ''')
    scene = input('选择：')
    if scene == '1':
        public_required_course()
    else:
        happy_holiday()
