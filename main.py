import math
import pickle
import random
import time

from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
import json
import tkinter as tk
from io import BytesIO
from PIL import Image, ImageTk
import base64


def short_sleep():
    interval = random.uniform(1, 2)
    time.sleep(interval)


def long_sleep():
    interval = random.uniform(60, 120)
    time.sleep(interval)


def login_dialog(captcha) -> tuple:
    root = tk.Tk()
    root.title('登录')

    try:
        with open('userinfo.pkl', 'rb') as f:
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

    image_bytes = base64.b64decode(captcha.split(',')[1])
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
        captcha = captcha_entry.get()
        root.destroy()

    captcha_entry.bind("<Return>", login_button_click)

    login_button = tk.Button(root, text='Login', command=login_button_click)
    login_button.grid(row=3, column=0, padx=5, pady=5)
    root.mainloop()

    if username and password:
        userinfo['name'] = username
        userinfo['password'] = password
        with open('userinfo.pkl', 'wb') as f:
            pickle.dump(userinfo, f)

    return username, password, captcha


def auto_study():
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


if __name__ == '__main__':
    auto_study()
