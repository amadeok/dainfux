import platform
windows= None; linux = None
if platform.system() == 'Linux': linux = True; 
elif platform.system() == 'Windows': windows = True;
else: print("Unknown platform")
if linux:
    import termios, tty,sys
    tty.setcbreak(sys.stdin)
elif windows:
    #import keyboard
    import msvcrt
    import ctypes
   #ctypes.windll.shcore.SetProcessDpiAwareness((1))    
    ret = ctypes.windll.shcore.SetProcessDpiAwareness(2)
    if ret == 0: print("Dpi awareness set correctly")
    else: print("Error settings Dpi awareness")



import pyautogui, time, os, sys, argparse, mss, numpy, cv2, threading
from PIL import Image
from draw_cursor import generate_cursor, draw_cursor

parser = argparse.ArgumentParser(description='bot')
parser.add_argument('--xywh', type = str, default = '1920:0:1200:1000:0:0.6', help='x y width height, windo x offset, scale')
parser.add_argument('--sleep', type = float, default = 5, help='loop sleep time')
parser.add_argument('--images', type = str, default = 'colab_captcha1.png!-234!8:riconetti9.png!0!0', help='images to find and click')
parser.add_argument('--imshow', type = int, default = 1, help='show capture')

args = parser.parse_args()

xywh = args.xywh.split(":")

x = int(xywh[0]); y = int(xywh[1]); w = int(xywh[2]); h = int(xywh[3])
window_x_of = int(xywh[4]); scale = float(xywh[5])

images = args.images.split(":")
print(images)

for g in range (len(images)):
    images[g] = images[g].split("!")
    images[g][1] = int(images[g][1])
    images[g][2] = int(images[g][2])
    images[g][0] = Image.open(images[g][0])
    images[g].append(None)

generate_cursor()
class c2:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.w = 0
        self.h = 0
        self.scale =scale
        self.changed = 1
        self.sleep  = args.sleep
sizes = c2()
exit = 0
def ter():
    P = subprocess.Popen([f'taskkill', "/PID", f"{os.getpid()}", '/F'])
def check_key_presses(c2):
    x = 0
    global exit; global changed
    while 1 and exit == 0:  # ESC
        if linux:
            x = sys.stdin.read(1)[0]
        elif windows:
            x = msvcrt.getch().decode('UTF-8')
        if exit: break
        if x == 'q':
            exit = 1
            sys.exit()
            pass#P = subprocess.Popen([f'taskkill', "/PID", f"{os.getpid()}", '/F'])
        elif x == 'a': c2.x -= 10
        elif x == 'd': c2.x += 10
        elif x == 'w': c2.y -= 10
        elif x == 's': c2.y += 10
        elif x == '1': c2.w -= 10
        elif x == '2': c2.w += 10
        elif x == '3': c2.h -= 10
        elif x == '4': c2.h += 10
        elif x == '5': c2.scale -= 0.1
        elif x == '6': c2.scale += 0.1
        elif x == '7': c2.sleep -= 0.01
        elif x == '8': c2.sleep += 0.01
        c2.changed = 1

thread = threading.Thread(target=check_key_presses, args=(sizes,))
thread.start()

if args.imshow:
    name = "mirror"
    cv2.namedWindow(name)
    cv2.moveWindow(name, window_x_of, 0)

with mss.mss() as sct:
    while 1:
    # Take a screenshot of a region out of monitor bounds
        rect = {"left": x+sizes.x, "top": y+sizes.y, "width": w+sizes.w, "height": h+sizes.h}
        if sizes.changed:
            print(rect, "Scale:", sizes.scale, "Sleep: ", sizes.sleep); sizes.changed = 0
        try:  scren_shot = sct.grab(rect)
        except:
            details = sct.get_error_details()
            print(details)
        draw_cursor(sizes, scren_shot, x, y, w, h)
        heystack =  Image.frombytes(
            "RGB", scren_shot.size, scren_shot.bgra, "raw", "RGBX")

        for n in range(len(images)):
            images[n][3] = pyautogui.locate(images[n][0], heystack, grayscale=True, confidence=0.70)    
        if args.imshow:

            img = numpy.asarray(scren_shot)
            img = cv2.resize(img, (int((w)*scale), int((h)*scale)))   
            cv2.imshow("mirror", img)
            if cv2.waitKey(25) & 0xFF == ord("q") or exit:
                cv2.destroyAllWindows()
                exit = 1; 
                break
        for n in range(len(images)):
            if images[n][3]: 
                print(images[n][0].filename ,images[n][3])
                pyautogui.click(images[n][3][0]+images[n][3][2]//2+images[n][1] + x, images[n][3][1]+images[n][3][3]//2+images[n][2] + y)
        time.sleep(args.sleep)
        










    # from selenium import webdriver
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support import expected_conditions as EC
# options = webdriver.ChromeOptions() 
# options.add_argument("start-maximized")
# options.add_experimental_option("excludeSwitches", ["enable-automation"])
# options.add_experimental_option('useAutomationExtension', False)
# driver = webdriver.Chrome(options=options, executable_path=r'/usr/bin/chromedriver')
# driver.get("https://www.inipec.gov.it/cerca-pec/-/pecs/companies")
# WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR,"iframe[name^='a-'][src^='https://www.google.com/recaptcha/api2/anchor?']")))
# WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//span[@id='recaptcha-anchor']"))).click()

