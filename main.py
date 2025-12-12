#!/usr/bin/env python3
import datetime as dt
import os
import random as rd
import threading as th
import time as tm
import math as m
import pygame as pg
import requests as r
from io import BytesIO
import runpy

VERSION = "1.1.2"

audiorate = 44100
widescreen = False
lfmusic = False
lsort = False
smoothscale = False

pg.display.init()
pg.font.init()

###options###

##time text position
#0    post-1993
#1    1991-1993
#2    pre-1991 (4k)
#3    pre-1991 (3000/jr)

textpos = 0

##star time drawing delay
timedrawing = False

##ldl drawing delay
ldldrawing = True

##1993 uppercase text
veryuppercase = False

##mesonet climate product id
afos_climate = "CLIJFK"

##music path
musicpath = None

##ldl over video
ldlmode = False
ldlfeed = "udp://@:1234"
##ldl mode static background (set to None for chroma key)
ldlbg = "4000bg.jpg"

##shows pressure as XX.XX in if false, otherwise XX.XX R/F/S depending on pressure trend
pressuretrend = True

##various misc old settings

old = {
    ""
}

##main location
loc="John F. Kennedy International Airport"
locname = "Kennedy Arpt"
efname = "New York Metro"

##Local Observations locations ["search name", "display name"]
obsloc = [
    ["Bridgeport, CT", "Bridgeport"],
    ["Islip, NY", "Islip"],
    ["John F. Kennedy International Airport", "Kennedy Arpt"],
    ["La Guardia Airport", "La Guardia Apt"],
    ["Newark, NJ", "Newark"],
    ["Teterboro, NJ", "Teterboro"],
    ["Westchester County, NY", "Westchester Co"]
]

outputs = None
extensions = []

crawls = []

extraldltext = ""

#############

seconds = 60
minutes = 60*60
hours = 60*60*60

crawlintervaltime = 15*minutes
crawlinterval = crawlintervaltime*1

forever = False

schedule = []

sm2 = True

compress = False

jr = True

sockets = False

radarint = 0.26
radarhold = 2.74

ldllf = False

adevice = None

vencoder = "libx264"

mute = False

crawllen = 40

try:
    import conf
    #you can sorta tell what order we implemented these in
    textpos = conf.textpos
    timedrawing = conf.timedrawing
    ldldrawing = conf.ldldrawing
    veryuppercase = conf.veryuppercase
    pressuretrend = conf.pressuretrend
    loc = conf.mainloc
    locname = conf.mainloc2
    flavor = conf.flavor
    flavor_times = conf.flavor_times
    flavor_un = [(f, flavor_times[i]) for i, f in enumerate(flavor) if not f.startswith("disabled")]
    flavor = [f[0] for f in flavor_un]
    flavor_times = [f[1] for f in flavor_un]
    musicpath = conf.musicdir
    afos_climate = conf.mesoid
    extraldltext = conf.extra
    crawlintervaltime = [15*minutes, 30*minutes, 1*hours, 2*hours, 3*hours, 4*hours, 6*hours, 8*hours, 12*hours, 24*hours][conf.crawlint]
    crawlinterval = crawlintervaltime*1
    crawls = [c[0] for c in conf.crawls if (c[1] and c[0])]

    lsort = getattr(conf, "lsort", False)
    obsloc = [o for o in conf.obsloc if o[0] and o[1]]
    if lsort:
        obsloc = sorted(obsloc, key=lambda o : o[1])
    outputs = [o for o in conf.outputs if not o.startswith("#")]
    ldlfeed = conf.ldlfeed
    ldlbg = conf.ldlbg
    old = conf.old
    ldlmode = conf.ldlmode
    forever = conf.forever
    foreverldl = conf.foreverldl
    schedule = conf.schedule
    sm2 = conf.aspect
    smode = conf.smode
    sockets = conf.socket
    radarint = conf.radarint
    radarhold = conf.radarhold
    ldllf = conf.ldllf
    efname = conf.efname
    mainlogo = conf.mainlogo
    radarlogo = conf.radarlogo
    extensions = conf.extensions
    adevice = conf.audiodevice
    metric = conf.metric
    borderless = conf.borderless
    vencoder = conf.vencoder
    mute = conf.mute
    widescreen = conf.widescreen
    #all of these were added after release, so i actually have to check for them. fun!
    compress = getattr(conf, "compress", False)
    radarsetting = getattr(conf, "radarsetting", False)
    lfmusic = getattr(conf, "musicsetting", 0)
    smoothscale = getattr(conf, "smoothscale", True)
    crawllen = getattr(conf, "crawllen", 40)
except ModuleNotFoundError:
    print("Configuration not found! Try saving your configuration again.")
    exit(1)
os.chdir(os.path.dirname(os.path.abspath(__file__))) #do this or everything explodes
if not mute:
    pg.mixer.init(audiorate, devicename=(adevice if adevice != "Default" else None))

if outputs and not mute:
    from pygame._sdl2.mixer import set_post_mix

colorbug_started = False
colorbug_nat = (flavor[-1] in ["lr", "cr"])

temp_symbol = ["F", "C"][metric]
speed_unit = ["MPH", "KM/H"][metric]
long_dist = ["mi.", "km."][metric]
short_dist = ["ft.", "m."][metric]

if sockets:
    import socket
    import os
    server_addr = ("127.0.0.1", 4000)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

screenw = 768 if not widescreen else 1024

win = pg.Surface((screenw, 480))
rwidth = screenw if not compress else int(screenw//1.2)
rwin = pg.display.set_mode((rwidth, 480), flags=(borderless*pg.NOFRAME)|pg.RESIZABLE)

pg.display.set_caption(f"FreeStar 4000 v{VERSION}")
icon = pg.image.load("mwsicon.png")
pg.display.set_icon(icon)

ext_loaded = []
for ext in extensions:
    ext_loaded.append(runpy.run_path(f"extensions/{ext}/main.py")) #load extension

ldlfeedactive = (ldlfeed is not None and ldlfeed)

avscale = (640 if not widescreen else 853, 480)

if ldlfeedactive:
    try:
        import cv2
    except ModuleNotFoundError:
        print("Install the opencv-python module to use feed input!")
        ldlfeed = None
        ldlfeedactive = False

if outputs:
    try:
        import av
        avevent = th.Event()
        avbuffer = pg.Surface(avscale)
    except ModuleNotFoundError:
        print("Install the av module to use stream output!")
        outputs = None

showing = 0

wxdata = None
# with open(os.path.expanduser("~/wxdata.json"), "r") as f:
#     wxdata = json.loads(f.read())

aldata = {"sun": {}, "moon": []}

# wxdata = {
#     "current": {
#         "info": {
#             "iconCode": 30,
#             "phraseLong": "Showers in the Vicinity",
#             "phraseShort": "Showers Near",
#             "dayOrNight": "D"
#         },
#         "conditions": {
#             "temperature": 999,
#             "humidity": 101,
#             "dewPoint": 0,
#             "feelsLike": 998,
#             "pressure": 30.01,
#             "pressureTendency": 1,
#             "cloudCeiling": None,
#             "visibility": 10,
#             "windSpeed": 1,
#             "windGusts": 99,
#             "windCardinal": "VAR"
#         }
#     },
#     "extended": {
#         "daypart": [
#             {
#                 "dayOrNight": "D",
#                 "temperature": 999,
#                 "name": "Today",
#                 "narration": "This is the text for today",
#                 "phraseLong": "Today Text"
#             },
#             {
#                 "dayOrNight": "N",
#                 "temperature": 0,
#                 "name": "Tonight",
#                 "narration": "This is the text for tonight",
#                 "phraseLong": "Tonight Text"
#             },
#             {
#                 "dayOrNight": "D",
#                 "temperature": 999,
#                 "name": "Tomorrow",
#                 "narration": "This is the text for tomorrow",
#                 "phraseLong": "Tomorrow Text"
#             },
#             {
#                 "dayOrNight": "N",
#                 "temperature": 0,
#                 "name": "Tomorrow Night",
#                 "phraseLong": "Tmrw Nght Text"
#             },
#             {
#                 "dayOrNight": "D",
#                 "temperature": 999,
#                 "name": "Day 3",
#                 "phraseLong": "Day 3 Text"
#             },
#             {
#                 "dayOrNight": "N",
#                 "temperature": 0,
#                 "name": "Day 3 Night",
#                 "phraseLong": "D3 Night Text"
#             },
#             {
#                 "dayOrNight": "D",
#                 "temperature": 999,
#                 "name": "Day 4",
#                 "phraseLong": "Day 4 Text"
#             },
#         ]
#     }
# }
clidata = None
lfdata = None

radartime = radarhold+radarint*6

#4000 colors
_gray = [104, 104, 104]
_smptewhite = [180, 180, 180]
_yellow = [180, 180, 16]
_cyan = [16, 180, 180]
_green = [16, 180, 16]
_magenta = [180, 16, 180]
_red = [180, 16, 16]
_blue = [16, 16, 180]
_black = [16, 16, 16]
_white = [235, 235, 235]

test_grad = [_yellow, _white, _black, _blue, _red, _magenta, _green, _cyan, _yellow, _white, _white]

for l in obsloc:
    l.append(None)

def draw_palette_gradient(rect : pg.Rect, colors, fuzzy=0.5):
    surface = pg.Surface(rect.size)
    x, y, w, h = rect
    num_steps = len(colors) - 1
    if num_steps <= 0:
        pg.draw.rect(surface, colors[0], rect)
        return

    step_height = h / num_steps

    for step in range(num_steps):
        c1 = colors[step]
        c2 = colors[step + 1]
        y_start = int(y + step * step_height)
        y_end = int(y + (step + 1) * step_height)

        for j in range(y_start, y_end):
            # how far along we are between the two step colors
            t = (j - y_start) / (y_end - y_start)
            # probability of using the second color increases with t
            prob_c2 = t

            for i in range(x, x + w):
                if rd.random() < prob_c2:
                    surface.set_at((i, j), c2)
                else:
                    surface.set_at((i, j), c1)

    return surface

oldgrad = False
#theme
bg_c = [(64, 33, 98),  (80, 39, 88), (98, 47, 75), (117, 55, 62), (134, 62, 51), (153, 70, 38), (168, 77, 28), (184, 83, 17), (209, 94, 0)]
#bg_c = [(44, 24, 112), (64, 33, 98), (80, 39, 88), (98, 47, 75), (117, 55, 62), (134, 62, 51), (153, 70, 38), (168, 77, 28), (184, 83, 17)]
ban_c = [(209, 94, 0), (184, 83, 17), (168, 77, 28), (153, 70, 38), (117, 55, 62), (98, 47, 75), (80, 39, 88), (64, 33, 98)]
ban_c = list(reversed(bg_c))
box_c = [(52, 88, 168), (52, 80, 152), (48, 72, 140), (44, 64, 124), (40, 46, 112)]
ldl_c = (40, 56, 112)
outer_c = (44, 24, 112)

def get_color_steps(c1, c2, steps):
    stepss = []
    #steps is the amount of steps generated
    for i in range(steps):
        stepss.append((
            c1[0] + (c2[0] - c1[0]) * (i / (steps-1)),
            c1[1] + (c2[1] - c1[1]) * (i / (steps-1)),
            c1[2] + (c2[2] - c1[2]) * (i / (steps-1))
        ))
    return stepss

# box_c, ban_c = get_color_steps(ban_c[0], ban_c[-4], len(box_c)), get_color_steps(box_c[0], box_c[-1], len(ban_c))
# bg_c = get_color_steps(ban_c[2], ban_c[-1], len(bg_c))
# ldl_c = (153, 70, 38)
# outer_c = (112, 44, 24)

bg_g = draw_palette_gradient(pg.Rect(0, 0, screenw, 315), [*bg_c, bg_c[-1]])

al_g = draw_palette_gradient(pg.Rect(0, 0, screenw, 96), bg_c)

def draw_bg(top_offset=0, bh_offset=0, all_offset=0, special=None, box=True):
    win.fill(_gray)
    if special == "al":
        win.fill((64, 64, 64))
    if special != "al":
        if oldgrad:
            pg.draw.rect(win, bg_c[0], pg.Rect(0, 90-all_offset, screenw, 45))
            pg.draw.rect(win, bg_c[1], pg.Rect(0, 135-all_offset, screenw, 45))
            pg.draw.rect(win, bg_c[2], pg.Rect(0, 180-all_offset, screenw, 45))
            pg.draw.rect(win, bg_c[3], pg.Rect(0, 225-all_offset, screenw, 45))
            pg.draw.rect(win, bg_c[4], pg.Rect(0, 270-all_offset, screenw, 45))
            pg.draw.rect(win, bg_c[5], pg.Rect(0, 315-all_offset, screenw, 45))
            pg.draw.rect(win, bg_c[6], pg.Rect(0, 360-all_offset, screenw, 45))
        else:
            win.blit(bg_g, (0, 90-all_offset))
    if not special and box:
        xoff = (screenw-768)//2
        pg.draw.rect(win, box_c[0], pg.Rect(62+xoff, 90-all_offset, 622, 310-bh_offset))
        pg.draw.rect(win, box_c[1], pg.Rect(66+xoff, 94-all_offset, 614, 302-bh_offset))
        pg.draw.rect(win, box_c[2], pg.Rect(70+xoff, 98-all_offset, 606, 294-bh_offset))
        pg.draw.rect(win, box_c[3], pg.Rect(74+xoff, 102-all_offset, 598, 286-bh_offset))
        pg.draw.rect(win, box_c[4], pg.Rect(78+xoff, 106-all_offset, 590, 278-bh_offset))
    if special == "al":
        if "oldal" not in old:
            win.blit(al_g, (0, 91-all_offset))
        else:
            pg.draw.rect(win, bg_c[1], pg.Rect(0, 91-all_offset, screenw, 48+3))
            pg.draw.rect(win, bg_c[2], pg.Rect(0, 91+48+3-all_offset, screenw, 48+3))
    if special == "df":
        xoff = (screenw-768)//2
        adjust = -6
        for i  in range(4):
            pg.draw.rect(win, box_c[0], pg.Rect(62+xoff, 90-all_offset+77*i+9, 622, 76+adjust))
            pg.draw.rect(win, box_c[1], pg.Rect(65+xoff, 93-all_offset+77*i+9, 616, 70+adjust))
            pg.draw.rect(win, box_c[2], pg.Rect(68+xoff, 96-all_offset+77*i+9, 610, 64+adjust))
            pg.draw.rect(win, box_c[3], pg.Rect(71+xoff, 99-all_offset+77*i+9, 604, 58+adjust))
            pg.draw.rect(win, box_c[4], pg.Rect(74+xoff, 102-all_offset+77*i+9, 598, 52+adjust))
    
    pg.draw.rect(win, ldl_c, pg.Rect(0, 400-all_offset-bh_offset, screenw, 80+all_offset+bh_offset))
    pg.draw.rect(win, (33, 26, 20), pg.Rect(0, 400-all_offset-bh_offset, screenw, 2))
    pg.draw.rect(win, (120, 120, 222), pg.Rect(0, 402-all_offset-bh_offset, screenw, 2))
    
    pg.draw.rect(win, outer_c, pg.Rect(0, 0-all_offset, screenw, 90))
    pg.draw.rect(win, ban_c[0], pg.Rect(0, 30-all_offset, screenw, 9))
    pg.draw.rect(win, ban_c[1], pg.Rect(0, 38-all_offset, screenw, 9))
    pg.draw.rect(win, ban_c[2], pg.Rect(0, 46-all_offset, screenw, 9))
    pg.draw.rect(win, ban_c[3], pg.Rect(0, 54-all_offset, screenw, 9))
    pg.draw.rect(win, ban_c[4], pg.Rect(0, 62-all_offset, screenw, 11))
    pg.draw.rect(win, ban_c[5], pg.Rect(0, 72-all_offset, screenw, 9))
    pg.draw.rect(win, ban_c[6], pg.Rect(0, 80-all_offset, screenw, 7))
    pg.draw.rect(win, ban_c[7], pg.Rect(0, 85-all_offset, screenw, 6))
    
    pg.draw.polygon(win, outer_c, [[screenw-148-top_offset, -all_offset], [screenw, -all_offset], [screenw, 90-all_offset], [screenw-238-top_offset,90-all_offset]])

def clear_profile():
    global profiling
    profiling = {
        "text": 0,
        "ops": 0
    }

profile = False

clear_profile()
def profiling_sect(section):
    def profiling_wrap(func):
        def wrapper(*args, **kwargs):
            if profile:
                start = tm.perf_counter()
                val = func(*args, **kwargs)
                end = tm.perf_counter()
                diff = end - start
                profiling[section] += diff
                return val
            else:
                return func(*args, **kwargs)
        return wrapper
    return profiling_wrap

pr_start = tm.perf_counter()
def profiling_start():
    global pr_start
    pr_start = tm.perf_counter()

def profiling_end(section):
    profiling[section] += (tm.perf_counter() - pr_start)

alertdata = [None, []]
alertactive = 0

icontable = [
    None,
    None,
    None,
    "Thunderstorm",
    "Thunderstorm",
    "Rain-Snow",
    "Rain-Sleet",
    "Wintry-Mix",
    "Shower",
    "Shower",
    "Freezing-Rain",
    "Shower",
    "Rain",
    "Light-Snow",
    "Heavy-Snow",
    "Blowing-Snow",
    "Heavy-Snow",
    "Sleet",
    "Sleet",
    "Fog",
    "Fog",
    "Fog",
    "Fog",
    "Windy",
    "Windy",
    "Blowing-Snow",
    "Cloudy",
    "Partly-Clear",
    "Mostly-Cloudy",
    "Mostly-Clear",
    "Partly-Cloudy",
    "Clear",
    "Sunny",
    "Mostly-Clear",
    "Partly-Cloudy",
    "Rain-Sleet",
    "Sunny",
    "Thunderstorm",
    "Thunderstorm",
    "Shower",
    "Shower",
    "Heavy-Snow",
    "Heavy-Snow",
    "Heavy-Snow",
    "Partly-Cloudy", #N/A is partly cloudy by default
    "Shower",
    "Heavy-Snow",
    "Thunderstorm"
]

regionalicontable = [
    None,
    None,
    None,
    "Thunderstorm",
    "Thunderstorm",
    "Rain-Snow-1992",
    "Rain-Sleet",
    "Wintry-Mix-1992",
    "Freezing-Rain-1992 ",
    "Rain-1992",
    "Freezing-Rain-1992",
    "Shower",
    "Rain-1992",
    "Light-Snow",
    "Heavy-Snow-1994",
    "Blowing Snow",
    "Light-Snow",
    "Sleet",
    "Sleet",
    "Smoke",
    "Fog",
    "Haze",
    "Smoke",
    "Wind",
    "Wind",
    "Cold",
    "Cloudy",
    "Mostly-Cloudy-Night-1994",
    "Mostly-Cloudy-1994",
    "Partly-Cloudy-Night",
    "Partly-Cloudy",
    "Clear-1992",
    "Sunny",
    "Partly-Cloudy-Night",
    "Partly-Cloudy",
    "Rain-Sleet",
    "Hot",
    "Scattered-Tstorms-1994",
    "Scattered-Tstorms-1994",
    "Scattered-Showers-1994",
    "Shower",
    "Scattered-Snow-Showers-1994",
    "Heavy-Snow-1994",
    "Heavy-Snow-1994",
    "Partly-Cloudy", #na
    "Shower",
    "Heavy-Snow-1994",
    "Thunderstorm"
]

xficontable = [
    None,
    None,
    None,
    "Thunderstorms",
    "Thunderstorms",
    "Rain-Snow",
    "Rain-Sleet",
    "Wintry-Mix",
    "Freezing-Rain-Sleet",
    "Rain",
    "Freezing-Rain",
    "Showers",
    "Rain",
    "Light-Snow",
    "Heavy-Snow",
    "Blowing-Snow",
    "Heavy-Snow",
    "Sleet",
    "Sleet",
    "Fog",
    "Fog",
    "Fog",
    "Fog",
    "Windy",
    "Windy",
    "Blowing-Snow",
    "Cloudy",
    "Mostly-Cloudy",
    "Mostly-Cloudy",
    "Partly-Cloudy",
    "Partly-Cloudy",
    "Sunny",
    "Sunny",
    "Partly-Cloudy",
    "Partly-Cloudy",
    "Rain-Sleet",
    "Sunny",
    "Isolated-Tstorms",
    "Scattered-Tstorms",
    "Scattered-Showers",
    "Showers",
    "Scattered-Snow-Showers",
    "Heavy-Snow",
    "Heavy-Snow",
    "Partly-Cloudy",
    "Scattered-Showers",
    "Scattered-Snow-Showers",
    "Scattered-Tstorms"
]

icon_offset = {"Rain": (10, 10), "Sunny": (0, 10), "Fog": (0, 15)}

mainicon = pg.image.load_animation("icons_cc/Partly-Cloudy.gif")
ldllficon = pg.image.load_animation("icons_reg/Partly-Cloudy.gif")
xficons = [None, None, None, None, None, None]

radardata = None

radar_provider = "apollo"

def splubby_the_return(tx):
    if tx[0] == "0":
        return tx[1:]
    else:
        return tx

if "al" in flavor:
    import ephem

import traceback as tb

def sign(n):
    if n > 0:
        return 1
    if n < 0:
        return -1
    return 0

dficons = [[] for _ in range(12)]

#commercial pre-roll, commercial on-air, unused, warning, unused
switches = [False, False, False, False, False] #this emulates the 4000's logic switches. why? as baldi once said, historicality
#warning is the only one of these i can actually control :wilted_flower:

#i'd take a deep breath here but i don't need to because i'm typing this :D
#in order:

#satellite video, (green)
#satellite data, (green)
#local video, (green)
#not assigned, (green)
#commercial pre-roll, (amber)
#commercial on-air, (amber)
#modem in-use, (amber)
#not assigned, (red)
#not assigned, (red)
#system error, (red)
#ring indicator, (green)
#carrier detect, (green)
#charging indicator (red)
leds = [False, False, False, False, False, False, False, False, False, False, False, sockets, True]

connections = []

def sendtoall(data):
    for connection in connections:
        connsendall(connection, data)

def getdata():
    ix = 0
    global wxdata
    global clidata
    global alertdata
    global mainicon, ldllficon
    global radardata
    global aldata
    global leds
    datagot = False
    
    while True:
        if datagot:
            ix += 1
            ix %= 60
        leds[6] = True
        sendtoall(f"led 6 1\n".encode())
        try:
            wxdata = r.get(f"https://wx.lewolfyt.cc/?loc={loc}"+("" if not metric else "&units=m")+"&extendeddays=10").json()

            if icontable[wxdata['current']['info']['iconCode']] is None:
                mainicon = [(pg.Surface((1, 1), pg.SRCALPHA), None)]
            else:
                micon = pg.image.load_animation(f"icons_cc/{icontable[wxdata['current']['info']['iconCode']]}.gif")
                nmicon = []
                for fr, ftime in micon:
                    nmicon.append((fr.convert_alpha(), ftime))
                mainicon = nmicon
            dn = (wxdata["extended"]["daypart"][0]["dayOrNight"] == "N")
            if regionalicontable[wxdata['extended']['daypart'][dn]['iconCode']] is None:
                mainicon = [(pg.Surface((1, 1), pg.SRCALPHA), None)]
            else:
                micon = pg.image.load_animation(f"icons_reg/{regionalicontable[wxdata['extended']['daypart'][dn]['iconCode']]}.gif")
                nricon = []
                for fr, ftime in micon:
                    nricon.append((fr.convert_alpha(), ftime))
                ldllficon = nricon

            for i in range(12):
                ic = regionalicontable[wxdata['extended']['daypart'][i+4]['iconCode']]
                if ic:
                    dficons[i] = [(s.convert_alpha(), ft) for s, ft in pg.image.load_animation(f"icons_reg/{ic}.gif")]
                else:
                    dficons[i] = []
            
            az = [None, []]
            if wxdata["current"]["alerts"]:
                for alert in wxdata["current"]["alerts"]:
                    az[1].append(alert["headline"])
            alertdata = az
            
            for i in range(6):
                ix = i*2+4-(wxdata["extended"]["daypart"][0]["dayOrNight"] == "N")
                if xficontable[wxdata['extended']['daypart'][ix]['iconCode']] is None:
                    ficon = [(pg.Surface((1, 1), pg.SRCALPHA), None)]
                else:
                    xficon = pg.image.load_animation(f"icons_xf/{xficontable[wxdata['extended']['daypart'][ix]['iconCode']]}.gif")
                    ficon = []
                    for fr, ftime in xficon:
                        ficon.append((fr.convert_alpha(), ftime))
                xficons[i] = ficon
            leds[1] = True
        except:
            print(tb.format_exc())
        
        try:
            report = r.get(f"https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?&pil={afos_climate}&center=&limit=1&sdate=&edate=&ttaaii=&order=desc").text

            rline = report[report.index("MONTH TO DATE"):].split("\n")[0]
            
            #get outlook data
            templine = report[report.index("DEGREE DAYS"):]
            templine = templine[templine.index("MONTH TO DATE"):].split("\n")[0]
            
            for section in rline.split(" "):
                if section.strip() == "":
                    continue
                try:
                    float(section)
                except:
                    pass
                else:
                    break
            
            ix = 0
            for ts in templine.split(" "):
                if ts.strip() == "":
                    continue
                try:
                    float(ts)
                except:
                    pass
                else:
                    ix += 1
                    if ix == 2:
                        normt = float(ts)
                    if ix == 3:
                        break
            ts = float(ts)
            ix = 0
            for rs in rline.split(" "):
                if rs.strip() == "":
                    continue
                try:
                    float(rs)
                except:
                    pass
                else:
                    ix += 1
                    if ix == 2:
                        normp = float(rs)
                    if ix == 3:
                        break
            rs = float(rs)
            dev1 = (abs(ts/normt) > 0.15)
            dev2 = (abs(rs/normp) > 0.15)
            
            clidata = {"month_precip": section, "temp_outlook": dev1*sign(ts), "precip_outlook": dev2*sign(rs)}
            datagot = True
            leds[1] = True
        except:
            print(tb.format_exc())
        if "al" in flavor:
            startdt = dt.date.today()
            moons = sorted([
                ("new", ephem.localtime(ephem.next_new_moon(startdt))),
                ("lq",  ephem.localtime(ephem.next_last_quarter_moon(startdt))),
                ("fq",  ephem.localtime(ephem.next_first_quarter_moon(startdt))),
                ("full",  ephem.localtime(ephem.next_full_moon(startdt)))
            ], key=(lambda p : p[1]))
            mooninfo = [(
                {"new": "New", "fq": "First", "lq": "Last", "full": "Full"}[p[0]],
                p[1].strftime("%h ")+splubby_the_return(p[1].strftime("%d"))
            ) for p in moons]
            aldata["moon"] = mooninfo
            if wxdata:
                lat, long = wxdata["current"]["info"]["geocode"]
                sr1 = r.get(f"https://api.sunrisesunset.io/json?lat={lat}&lng={long}&time_format=unix").json()["results"]
                sr2 = r.get(f"https://api.sunrisesunset.io/json?lat={lat}&lng={long}&time_format=unix&date=tomorrow").json()["results"]
                aldata["sun"] = {
                    "sunrise1": int(sr1["sunrise"]),
                    "sunset1": int(sr1["sunset"]),
                    "sunrise2": int(sr2["sunrise"]),
                    "sunset2": int(sr2["sunset"])
                }

        def get_obsloc(l):
            global leds
            try:
                l[2] = r.get(f"https://wx.lewolfyt.cc/?loc={l[0]}"+("" if not metric else "&units=m")).json()
                leds[1] = True
            except:
                print(tb.format_exc())
        for l in obsloc:
            th.Thread(target=get_obsloc, args=(l,)).start()
        
        if "lr" in flavor:
            try:
                if radar_provider == "apollo":
                    radardt = pg.image.load_animation(BytesIO(r.get(f"http://apollo.us.com:8008/radar_composite_animate.gif").content))
                    radardata2 = []
                    lat, long = wxdata["current"]["info"]["geocode"]
                    x, y = mapper((mappoint1, mappoint2), lat, long)
                    x = max(x, 0)
                    y = max(y, 0)
                    x = min(x, radardt[0][0].get_width()-screenw//2)
                    y = min(y, radardt[0][0].get_height()-240)
                    for rad, t in radardt:
                        r2 = pg.Surface((screenw//2, 240))
                        r2.blit(rad, (0, 0), pg.Rect(x, y, screenw//2, 240))
                        radardata2.append((pg.transform.scale_by(r2, (2, 2)), t))
                    radardata = radardata2
                leds[1] = True
            except:
                print(tb.format_exc())
        elif "cr" in flavor:
            try:
                if radar_provider == "apollo":
                    radardt = pg.image.load(BytesIO(r.get(f"http://apollo.us.com:8008/radar_composite.png").content))
                    radardata2 = []
                    lat, long = wxdata["current"]["info"]["geocode"]
                    x, y = mapper((mappoint1, mappoint2), lat, long)
                    x = max(x, 0)
                    y = max(y, 0)
                    x = min(x, radardt.get_width()-screenw//2)
                    y = min(y, radardt.get_height()-240)
                    r2 = pg.Surface((screenw//2, 240))
                    r2.blit(radardt, (0, 0), pg.Rect(x, y, screenw//2, 240))
                    radardata2.append((pg.transform.scale_by(r2, (2, 2)), 0))
                    radardata = radardata2
                leds[1] = True
            except:
                print(tb.format_exc())
        leds[6] = False
        sendtoall(f"led 6 0\n".encode())
        for i in range(300):
            tm.sleep(1)
th.Thread(target=getdata, daemon=True).start()

musicfiles = []
if musicpath:
    for file in os.listdir(musicpath):
        if file.endswith((".mp3", ".wav", ".flac", ".xm", ".mod", ".ogg")) and not file.startswith("."):
            musicfiles.append(os.path.join(musicpath, file))

char_list = {}
def frender(font, text, aa, color):
    if (font, text, aa, color) in char_list:
        return char_list[(font, text, aa, color)]
    r = font.render(text, aa, color)
    char_list[(font, text, aa, color)] = r
    return r

fw = 1.1

scalecache = {}

def scalec(og, font, text, color, w):
    if (font, text, color, w) not in scalecache:
        sl = pg.transform.smoothscale_by(og, w)
        scalecache[(font, text, color, w)] = sl
        return sl
    else:
        return scalecache[(font, text, color, w)]

def renderoutline(font, text, x, y, width, color=(0, 0, 0), surface=win, og=None, ofw=None):
    if og is None:
        og = frender(font, text, True, (0, 0, 0))
        og = scalec(og, font, text, color, (fw if ofw is None else ofw, 1))
    surface.blit(og, (x-width, y-width))
    surface.blit(og, (x+width, y-width))
    surface.blit(og, (x-width, y+width))
    surface.blit(og, (x+width, y+width))

def time_fmt(time):
    if time >= minutes:
        return str(int(time/minutes)) + " minutes " + str(int((time/seconds) % 60)) + " seconds"
    else:
        return str(int(time/seconds)) + " seconds"

char_offsets_default = {
    ":": -3,
    ".": -6
}

def shorten_phrase(phrase : str):
    if len(phrase) < 9:
        return phrase
    replacelist = {"Ice Crystals": "Ice"}
    if phrase in replacelist:
        return replacelist[phrase]
    if "Shower" in phrase:
        t = phrase.replace("Shower", "Shwr")
        if len(t) < 9:
            return t
        t = phrase.replace("Showers", "Shwr")
        if len(t) < 9:
            return t
        t = phrase.replace("Shower", "Shw")
        if len(t) < 9:
            return t.replace("Snow Shw", "Hvy Snow").replace("Rain Shw", "Hvy Rain")
        t = phrase.replace("Showers", "Shw")
        if len(t) < 9:
            return t.replace("Snow Shw", "Hvy Snow").replace("Rain Shw", "Hvy Rain")
        return phrase.replace("Showers", "Shw")
    if "Light" in phrase:
        return phrase.replace("Light", "Lgt")
    if "Cldy" in phrase:
        if phrase[1] == " ":
            phrase = f'{phrase[0]} Cloudy'
        else:
            phrase = "Cloudy"
    if "Heavy" in phrase:
        return phrase.replace("Heavy", "Hvy")
    if phrase.endswith("/Wind"):
        return phrase.split("/")[0]
    if phrase.split(" ")[-1] == "Showers":
        return "Showers"
    return phrase

smallfont = pg.font.Font("Small.ttf", 32)
largefont32 = pg.font.Font("Large.ttf", 33)
startitlefont = pg.font.Font("Main.ttf", 33)
starfont32 = pg.font.Font("Main.ttf", 34)
extendedfont = pg.font.Font("Extended.ttf", 33)

font_tallest = {largefont32: 0, smallfont: 0, starfont32: 0}
for char in "qwertyuiopasdfghjklzxcvbnm1234567890QWERTYUIOPASDFGHJKLZXCVBNM-":
    c = largefont32.size(char)[1]
    if c > font_tallest[largefont32]:
        font_tallest[largefont32] = c
for char in "qwertyuiopasdfghjklzxcvbnm1234567890QWERTYUIOPASDFGHJKLZXCVBNM-":
    c = smallfont.size(char)[1]
    if c > font_tallest[smallfont]:
        font_tallest[smallfont] = c
for char in "qwertyuiopasdfghjklzxcvbnm1234567890QWERTYUIOPASDFGHJKLZXCVBNM-":
    c = starfont32.size(char)[1]
    if c > font_tallest[starfont32]:
        font_tallest[starfont32] = c

chars        = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[°]^_'abcdefghijklmnopqrstuvwxyz{|}~"
chars_symbol = " ↑↓"

def loadjrfont(name):
    return (pg.image.load(f"jrfonts/fill/{name}.png").convert_alpha(), pg.image.load(f"jrfonts/shadow/{name}.png").convert_alpha())
jrfontnormal = loadjrfont("normal")

jrfontradaralert = loadjrfont("normal")
jrfontradaralert[0].fill((198, 178, 154, 255), special_flags=pg.BLEND_RGBA_MULT)
jrfontradaralert[1].fill((4, 68, 4, 0), special_flags=pg.BLEND_RGBA_ADD)

jrfonticon = loadjrfont("icon")
jrfontsmall = loadjrfont("small")
jrfonttall = loadjrfont("tall")
jrfontsymbol = loadjrfont("symbol")
jrfonttravel = loadjrfont("travel")

charset_col = {}

def drawchar(char, cset, x, y, color):
    if char.strip() == "":
        return
    if char in chars:
        ix = chars.index(char)
    elif char in chars_symbol:
        ix = chars_symbol.index(char)
    else:
        ix = 0
    
    if color is None:
        cset2 = cset
    else:
        if (cset, color) in charset_col:
            cset2 = charset_col[(cset, color)]
        else:
            cset2 = cset.copy()
            cset2.fill(color, special_flags=pg.BLEND_RGBA_MULT)
            charset_col[(cset, color)] = cset2
    
    win.blit(cset2, (x, y), pg.Rect((ix*32)%cset.get_width(), int(ix*32//cset.get_width())*(cset.get_height()//6), 32, cset.get_height()//6))

white = (215, 215, 215)

@profiling_sect("text")
def drawshadow(font, text, x, y, offset, color=white, surface=win, mono=0, ofw=None, bs=False, char_offsets=char_offsets_default, upper=False, jr_override=None, shadow=True):
    if text == "":
        return
    if not jr:
        t = [c for ch in text if c not in "±≠"]
        text = "".join(t)
    if jr:
        fx = [[], []] #shake, nofill
        fxa = [False, False]
        sheet = jrfontnormal
        y += 6
        if font == largefont32:
            sheet = jrfonttravel
        elif font == smallfont:
            sheet = jrfontsmall
            y += 10
        elif font == extendedfont:
            sheet = jrfonticon
        if jr_override:
            sheet = jr_override
        if bs:
            if shadow:
                for i, char in enumerate(text):
                    drawchar(char, sheet[1], x+i*m.floor(mono)+2+char_offsets.get(char, 0), y+2, None)
            for i, char in enumerate(text):
                drawchar(char, sheet[0], x+i*m.floor(mono)+2+char_offsets.get(char, 0), y+2, color if type(color) != list else color[i])
        io = 0
        ic = 0
        if shadow:
            for i, char in enumerate(text):
                if char == "±":
                    io += 1
                    fxa[0] = not fxa[0]
                    continue
                if char == "≠":
                    io += 1
                    fxa[1] = not fxa[1]
                    continue
                fxo = (0, 0)
                if fxa[0]:
                    fxo = (rd.randint(-1, 1), rd.randint(-1, 1))
                    fx[0].append(fxo)
                drawchar(char, sheet[1], x+fxo[0]+(i-io)*m.floor(mono)+char_offsets.get(char, 0), y+fxo[1], None)
        fxa = [False, False]
        io = 0
        for i, char in enumerate(text):
            if char == "±":
                io += 1
                fxa[0] = not fxa[0]
                continue
            if char == "≠":
                io += 1
                fxa[1] = not fxa[1]
                continue
            if fxa[1]:
                continue
            fxo = (0, 0)
            if fxa[0]:
                fxo = fx[0][ic]
                ic += 1
            drawchar(char, sheet[0], x+fxo[0]+(i-io)*m.floor(mono)+char_offsets.get(char, 0), y+fxo[1], color if type(color) != list else color[i])
        
        return
    
    text=str(text)
    if upper:
        text = text.upper()
    if mono == 0:
        og = frender(font, text, True, (0, 0, 0))
        og = scalec(og, font, text, (0, 0, 0), (fw if ofw is None else ofw, 1))
        if not bs:
            surface.blit(og, (x+offset, y+offset))
        else:
            for i in range(offset):
                surface.blit(og, (x+i+1, y+i+1))
        renderoutline(font, text, x, y, 1, og=og, ofw=ofw)
        surface.blit(scalec(frender(font, text, True, color), font, text, color, (fw if ofw is None else ofw, 1)), (x, y))
    else:
        if type(color[0]) in [int, float]:
            col = color
        for i, char in enumerate(text):
            if char == " ":
                continue
            coffset = 0
            if char in char_offsets:
                coffset = char_offsets[char]
            og = frender(font, char, True, (0, 0, 0))
            og = scalec(og, font, char, (0, 0, 0), (fw if ofw is None else ofw, 1))
            coffset2 = 0
            if font in font_tallest:
                coffset2 = font_tallest[font] - font.size(char)[1]
            if not bs:
                surface.blit(og, (x+mono*i+offset+coffset, y+offset+coffset2))
            else:
                for j in range(offset):
                    surface.blit(og, (x+mono*i+j+2+coffset, y+j+2+coffset2))
                    surface.blit(og, (x+mono*i+j+2+coffset, y+j+coffset2))
                    surface.blit(og, (x+mono*i+j+coffset, y+j+2+coffset2))
            renderoutline(font, char, x+mono*i+coffset, y+coffset2, 1, og=og, ofw=ofw)
            #surface.blit(scalec(frender(font, char, True, col), font, char, col, (fw if ofw is None else ofw, 1)), (x+mono*i, y))
        for i, char in enumerate(text):
            if type(color[0]) in [list, tuple]:
                col = color[i]
            if char == " ":
                continue
            coffset = 0
            if char in char_offsets:
                coffset = char_offsets[char]
            coffset2 = 0
            if font in font_tallest:
                coffset2 = font_tallest[font] - font.size(char)[1]
            surface.blit(scalec(frender(font, char, True, col), font, char, col, (fw if ofw is None else ofw, 1)), (x+mono*i+coffset, y+coffset2))

@profiling_sect("ops")
def drawingfilter(text, idx):
    finaltext = ""
    left = idx*1
    for char in text:
        if char == " ":
            finaltext += " "
            continue
        left -= 1
        if left == 0:
            break
        finaltext += char

if ldlbg:
    ws2 = pg.image.load(ldlbg)
else:
    ws2 = pg.Surface((1, 1), pg.SRCALPHA)

#ws2 = pg.transform.smoothscale(pg.image.load("almanacref2b.png"), (768, 480))

noaa = pg.image.load("noaa.gif").convert_alpha()

logo = pg.image.load(mainlogo)
logorad = pg.image.load(radarlogo)

logorad = pg.transform.scale(logorad, (768, 480))

ui = True
linespacing = 40.25

ldl_y = 0
if textpos >= 2:
    ldl_y = -16

ldlreps = 0

def mapper(ref_points, lat, lon):
    (lat1, lon1), (x1, y1) = ref_points[0]
    (lat2, lon2), (x2, y2) = ref_points[1]

    scale_lat = (y2 - y1) / (lat2 - lat1)
    scale_lon = (x2 - x1) / (lon2 - lon1)

    x_offset = x1 - lon1 * scale_lon
    y_offset = y1 - lat1 * scale_lat

    x = lon * scale_lon + x_offset
    y = lat * scale_lat + y_offset
    return (x, y)


bbox = (-127.680, 21.649, -66.507, 50.434)
mappoint1 = [(bbox[3], bbox[0]), (-screenw//4, -120)]
mappoint2 = [(bbox[1], bbox[2]), (4100-screenw//4, 1920-120)]

def connsendall(conn, data):
    try:
        conn.sendall(data)
    except BrokenPipeError:
        pass

if sockets and sock:
    def socket_handler():
        sock.bind(server_addr)
        sock.listen(1)
        global ldlmode, ldlon, ldlreps, ldlidx, switches, connections, leds
        while True:
            conn, addr = sock.accept()
            connections.append(conn)
            try:
                while True:
                    data = conn.recv(1024)
                    if data:
                        dt = data.decode().strip().rstrip()
                        
                        args = dt.split(" ")
                        
                        if args[0] == "cue":
                            if ldlmode:
                                connsendall(conn, f"accepted\n".encode())
                                ldlmode = False
                            else:
                                connsendall(conn, f"no change\n".encode())
                        elif args[0] == "cueldl":
                            if not ldlon:
                                reps = 1
                                if len(args) > 1:
                                    try:
                                        reps = int(args[1])
                                    except:
                                        pass
                                connsendall(conn, f"accepted\n".encode())
                                ldlon = True
                                ldlreps = reps
                                ldlidx = 0
                            else:
                                connsendall(conn, f"no change\n".encode())
                        elif args[0] == "uncue":
                            if not ldlmode:
                                connsendall(conn, f"accepted\n".encode())
                                ldlmode = True
                            else:
                                connsendall(conn, f"no change\n".encode())
                        elif args[0] == "uncueldl":
                            if ldlon:
                                connsendall(conn, f"accepted\n".encode())
                                ldlon = False
                            else:
                                connsendall(conn, f"no change\n".encode())
                        elif args[0] == "status":
                            status = ""
                            status += f"ldlmode {'ON' if ldlmode else 'OFF'}\n"
                            status += f"ldl {'ON' if ldlon else 'OFF'}\n"
                            status += f"feed {'ON' if ldlfeed else 'OFF'}\n"
                            status += f"crawltime {crawlinterval}\n"
                            status += f"crawlidx {crawlactive}\n"
                            status += f"wxdata {'OK' if wxdata else 'NONE'}\n"
                            status += f"clidata {'OK' if clidata else 'NONE'}\n"
                            lfct = 0
                            for l in obsloc:
                                if l[2]:
                                    lfct += 1
                            status += f"lfdata {lfct}/{len(obsloc)}\n"
                            switchest = "".join([["0", "1"][e] for e in switches])
                            status += f"switches {switchest}\n"
                            ledst = "".join([["0", "1"][e] for e in leds])
                            status += f"leds {ledst}\n"
                            status += "statusend\n"
                            connsendall(conn, status.encode())
                        elif dt.strip() == "":
                            continue
                        else:
                            connsendall(conn, f"rejected\n".encode())

                    else:
                        break
            finally:
                conn.close()
                connections.remove(conn)
    th.Thread(target=socket_handler, daemon=True).start()

gmono = 18.15
yeller = (215, 215, 0)
yeller = (187, 182, 45)
def drawpage_fmt(lines : list, formatting : list):
    yy = 109-linespacing*4
    fmt = [1, "W"]
    colors = {
        "W": white,
        "R": (255, 0, 0),
        "G": (0, 255, 0),
        "B": (0, 0, 255),
        "C": (0, 255, 255),
        "M": (255, 0, 255),
        "K": (0, 0, 0)
    }
    if len(formatting) < len(lines):
        formatting.extend([None for _ in range(len(lines)-len(formatting))])
    xoff = (screenw-768)//2
    for i, line in enumerate(lines):
        yo = 0
        
        if formatting[i]:
            fmmt = formatting[i].split("_")
            fmt = [int(fmmt[0]), fmmt[1]]
        
        coll = colors[fmt[1]]
        
        if fmt[0] == 1:
            drawshadow(starfont32, line, 80+xoff, 109+yy+ldl_y*1.25+yo, 3, mono=gmono, char_offsets={}, color=coll)
            yy += linespacing
        elif fmt[0] == 0:
            yo = -8
            drawshadow(smallfont, line, 80+xoff, 109+yy+ldl_y*1.25+yo, 3, mono=gmono, char_offsets={}, color=coll)
            yy += linespacing/2
        elif fmt[0] == 2:
            drawshadow(largefont32, line, 80+xoff, 109+yy+ldl_y*1.25+yo, 3, mono=gmono, char_offsets={}, color=coll, jr_override=jrfonttall)
            yy += linespacing

def drawpage(lines : list, smalltext="", shift=0, vshift=0):
    clines : list = lines[(shift*7):(shift*7+7)].copy()
    ss = 0
    st = True
    xoff = (screenw-768)//2
    for i, line in enumerate(clines):
        if line == '' and st:
            ss += 1
        else:
            st = False
        drawshadow(starfont32, line, 80+xoff, 109+linespacing*(i-ss)+ldl_y*1.25+vshift, 3, mono=gmono, char_offsets={})
    if smalltext:
        drawshadow(smallfont, smalltext, 80+xoff, 109-32+ldl_y+vshift, 3, mono=gmono, char_offsets={})

def lerp(x, y, n):
    return x * n + y * (1-n)

def drawpage2(lines : list, smalltext="", shift=0):
    clines : list = lines[(shift*7):(shift*7+7)].copy()
    ss = 0
    st = True
    
    startline = 109+ldl_y*1.25
    endline = 109+linespacing*(6)+ldl_y*1.25
    xoff = (screenw-768)//2
    for i, line in enumerate(clines):
        if line == '' and st:
            ss += 1
        else:
            st = False
        drawshadow(starfont32, line, 80+xoff, lerp(endline, startline, i/(len(lines)-1)), 3, mono=gmono, char_offsets={})
    if smalltext:
        drawshadow(smallfont, smalltext, 80+xoff, 109-32+ldl_y, 3, mono=gmono, char_offsets={})

def wraptext(text, ll=32):
    final = []
    paragraphs = text.split("\n")
    for pgh in paragraphs:
        if pgh == '':
            final.append('')
            continue
        words = pgh.split(" ")
        nl = ""
        for word in words:
            if (len(nl) + len(word)) > ll:
                final.append(nl + "")
                nl = ""
            nl += word
            nl += " "
        final.append(nl.strip())
    return final

def drawing(text, amount, ram=False):
    final = ""
    am = amount*1
    for char in text:
        if am <= 0:
            break
        if char == " ":
            final += char
            continue
        am -= 1
        final += char
    if (am % 1) != 0 and amount < len(text):
        txl = list(final)
        txl.insert(-1, "≠")
        final = "".join(txl)
    if ram:
        return final, am
    return final

crawling = False

ldlon = not not foreverldl

crawlactive = 0
crawlscroll = 0

crawltime = 60*40
ldlidx = 0
ldlintervaltime = 4*seconds
ldlinterval = ldlintervaltime*1
slideinterval = flavor_times[0]*seconds
slideidx = 0

cl = pg.time.Clock()
lastlasttime = 0
lasttime = 0
ldldrawidx = 0
generaldrawidx = 0

slide = "cc"

noreport = [
    "",
    "",
    "       No Report Available"
]

@profiling_sect("ops")
def padtext(text, l):
    text = str(text)
    if len(text) >= l:
        return text
    final = " "*(l-len(text))
    final += text
    return final

nextcrawlready = False
@profiling_sect("ops")
def textmerge(t1, t2):
    final = ""
    for i in range(max(len(t1), len(t2))):
        if i >= len(t1):
            final += t2[i]
        elif i >= len(t2):
            final += t1[i]
        elif t1[i] == " ":
            final += t2[i]
        elif t2[i] == " ":
            final += t1[i]
        else:
            final += t1[i]
    return final

quit_requested = False

def parse_ext_action(action):
    #this is a system for extensions to do things to the main program
    #action is a list of lists
    if action is None:
        return
    for act in action:
        if act[0] == "set_variable":
            varname = act[1]
            value = act[2]
            globals()[varname] = value #set a variable (e.g. ldlmode = True if an extension wants to manually intervene)
        elif act[0] == "call_function":
            funcname = act[1]
            args = act[2]
            func = globals()[funcname]
            func(*args) #call a function that isn't one that's passed to init
        elif act[0] == "get_variable":
            varname = act[1]
            destvar = act[2]
            value = globals()[varname]
            globals()[destvar] = value #get a variable from main program and store it in an extension-accessible variable
        elif act[0] == "execute_code":
            code = act[1]
            exec(code) #execute arbitrary code (use with caution)
        elif act[0] == "quit":
            global quit_requested
            quit_requested = True
        #more can be added soon

if mute:
    musicch = None
    voicech = None
    beepch = None
else:
    musicch = pg.mixer.Channel(0)
    voicech = pg.mixer.Channel(1)
    beepch = pg.mixer.Channel(2)

for ext in ext_loaded:
    if 'init' in ext:
        ext_action = ext['init']({
            'drawshadow': drawshadow,
            'drawpage': drawpage,
            'drawpage_fmt': drawpage_fmt,
            'wraptext': wraptext,
            'padtext': padtext,
            'textmerge': textmerge,
            'musicch': musicch,
            'voicech': voicech,
            'pygame': pg
        }) #allow extensions to run init code and access some important functions
        parse_ext_action(ext_action)

if not mute:
    beep = pg.Sound("beep.ogg")
radarx = ['', '99'][radarsetting]
radarHeader = pg.transform.scale(pg.image.load(f"radar{radarx}.png"), (768, 480))
radarHeaderC = pg.transform.scale(pg.image.load(f"radarc{radarx}.png"), (768, 480))
if screenw > 768:
    radarLeft = pg.transform.scale(radarHeader.subsurface(pg.Rect(0, 0, 1, radarHeader.get_height())), (m.ceil((screenw-768)/2), radarHeader.get_height()))
    radarRight = pg.transform.scale(radarHeader.subsurface(pg.Rect(radarHeader.get_width()-1, 0, 1, radarHeader.get_height())), (m.ceil((screenw-768)/2), radarHeader.get_height()))
if screenw > 768:
    radarLeftC = pg.transform.scale(radarHeaderC.subsurface(pg.Rect(0, 0, 1, radarHeaderC.get_height())), (m.ceil((screenw-768)/2), radarHeaderC.get_height()))
    radarRightC = pg.transform.scale(radarHeaderC.subsurface(pg.Rect(radarHeaderC.get_width()-1, 0, 1, radarHeaderC.get_height())), (m.ceil((screenw-768)/2), radarHeaderC.get_height()))

latestframe = pg.Surface((1, 1))
vidcap = None

moon_full = pg.image.load("moon/Full-Moon.gif").convert_alpha()
moon_lq = pg.image.load("moon/Last-Quarter.gif").convert_alpha()
moon_fq = pg.image.load("moon/First-Quarter.gif").convert_alpha()
moon_new = pg.image.load("moon/New-Moon.gif").convert_alpha()

def domusic():
    if mute:
        return
    while True:
        musicon = True
        if ldlmode and lfmusic:
            musicon = False
        if musicon:
            if not musicch.get_busy():
                musicch.play(pg.mixer.Sound(rd.choice(musicfiles)))
        else:
            musicch.stop()
        tm.sleep(0.02)

import queue as q
audio_queue = q.Queue()

capframes = []

ffps = 0
flock = th.Lock()
def omnomnomimeatingtheframes():
    global latestframe
    global capframes
    next_time = tm.perf_counter()
    while True:
        if ffps == 0:
            tm.sleep(0.01)
            next_time = tm.perf_counter()
            continue

        interval = 1.0 / float(ffps)
        next_time += interval
        if len(capframes) == 0:
            tm.sleep(0.01)
            next_time = tm.perf_counter()
            continue
        with flock:
            try:
                latestframe = capframes.pop(0)
            except:
                next_time = tm.perf_counter()
                continue
            if len(capframes) > 1200:
                capframes = capframes[600:]
                print("clipped capture frames! running slow?")

        #all programs need their sleep
        sleep_time = next_time - tm.perf_counter()
        if sleep_time > 0:
            tm.sleep(sleep_time)
        else:
            if -sleep_time > 1.0:
                next_time = tm.perf_counter()

def docapture():
    global vidcap
    global ffps
    global leds
    if ldlfeedactive:
        vidcap = cv2.VideoCapture(ldlfeed)
        if not vidcap.isOpened():
            vidcap = None
            print("Video could not be opened!")
        print("Capture active!")
    #last = tm.time()
    
    ret_counter = 0
    reconnects = 0
    while True:
        if vidcap:
            ret, frame = vidcap.read()
            fps = vidcap.get(cv2.CAP_PROP_FPS)
            ffps = fps
            if not leds[0]:
                leds[0] = True
                sendtoall(f"led 0 1\n".encode())
        else:
            ret = False
            fps = 0
            if leds[0]:
                leds[0] = False
                sendtoall(f"led 0 0\n".encode())
        if fps == 0:
            tm.sleep(0.01)
            continue
        if not ret:
            if ret_counter <= 4:
                tm.sleep(2)
                ret_counter += 1
                print(f"no ret [{ret_counter}]")
            if ret_counter > 4:
                if ret_counter == 5:
                    print("too many losses! reconnecting...")
                vidcap.release()
                vidcap = cv2.VideoCapture(ldlfeed)
                reconnects += 1
                ss = "s" if reconnects > 1 else ""
                if not vidcap.isOpened():
                    vidcap = None
                    print(f"reconnect failed! [{reconnects} attempt{ss}]")
                else:
                    print(f"reconnect success! [after {reconnects} attempt{ss}]")
                    reconnects = 0
                    ret_counter = 0
            continue
        else:
            ret_counter = 0
        
        frame2 = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame2 = cv2.transpose(frame2)
        if smode == 0:
            scaled = cv2.resize(frame2, (480, screenw))
        fr_size = (vidcap.get(cv2.CAP_PROP_FRAME_WIDTH), vidcap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if smode == 1:
            scaled = cv2.resize(frame2, (int(480 * fr_size[1] / fr_size[0] * (4/3 if sm2 else 1)), screenw))
        if smode == 2:
            scaled = cv2.resize(frame2, (480, int(fr_size[0]/fr_size[1]*(1.2 if sm2 else 1)*480)))
        latestframe = pg.surfarray.make_surface(scaled)
        
        with flock:
            capframes.append(latestframe)
        

frame_idx_actual = 0
if outputs is not None:
    import fractions as frac
    streams = []
    audio_ready_event = th.Event()
    aq = q.Queue()

p_counter = 0
resetup = set() #if a url is in this list it will be set back up asap
def setupstream(url):
    s = av.open(url, mode="w", format="flv")
    st = s.add_stream(vencoder, rate=60)
    at = None
    if not mute:
        at = s.add_stream("aac", rate=audiorate)
        at.layout = "stereo"
    st.width = avscale[0]
    st.height = avscale[1]
    st.pix_fmt = "yuv420p"
    return (s, st, at, url)

framelists = {}
audlists = {}

frame_start_evt = th.Event()

def dowrite_th(strea : tuple, url):
    global resetup
    stream = tuple(strea)
    frame_start_evt.wait()
    while True:
        if stream in resetup:
            st = stream[3]
            try:
                stream[0].close()
            except:
                pass
            stream = setupstream(st)
            print(f"Reset stream {st[:20]}...")
            resetup.remove(stream)
        
        if len(framelists[url]) > 0:
            frame = framelists[url].pop(0)
        else:
            tm.sleep(0.01)
            continue
        
        if not mute:
            while len(audlists[url]) > 0:
                try:
                    af = audlists[url].pop(0)
                except:
                    break
                try:
                    for packet in stream[2].encode(af):
                        stream[0].mux(packet)
                except (av.BrokenPipeError, av.EOFError):
                    resetup.add(url)
        
        try:
            for packet in stream[1].encode(frame):
                stream[0].mux(packet)
        except (av.BrokenPipeError, av.EOFError):
            resetup.add(url)
        
        
def dowrite():
    global streams
    
    streams2 = {}
    threads = []

    for out in outputs:
        stre = setupstream(out)
        streams2[out] = (stre, len(streams))
        #streams.append(stre)
        framelists[out] = []
        audlists[out] = []
        h = th.Thread(target=dowrite_th, args=(stre, out))
        h.start()
        threads.append(h)
    
    frame_start_evt.set()
    audio_ready_event.set()
    last_p = 0
    while True:
        avevent.wait()
        avevent.clear()
        
        if last_p == p_counter:
            avevent.clear()
            continue
        sdata = pg.surfarray.array3d(avbuffer).transpose([1, 0, 2])
        frame = av.VideoFrame.from_ndarray(sdata, format="rgb24")
        frame = frame.reformat(format="yuv420p")
        frame.pts = frame_idx_actual
        frame.time_base = frac.Fraction(1, 60)
        for out in outputs:
            framelists[out].append(frame)
        last_p = p_counter * 1

def dowriteaudio():
    if mute:
        return
    audio_ready_event.wait()
    while True:
        try:
            buf = audio_queue.get_nowait()
        except:
            tm.sleep(0.01)
            continue
        
        
        n_int = len(buf) // 4
        af = av.AudioFrame(format="s16", layout="stereo", samples=n_int)
        af.sample_rate = audiorate
        af.planes[0].update(buf)
        af.time_base = frac.Fraction(1, 60)
        af.pts = frame_idx_actual
        for out in outputs:
            audlists[out].append(af)

def postmix(dev, mem):
    audio_queue.put_nowait(bytes(mem))
if musicpath:
    th.Thread(target=domusic, daemon=True).start()
if ldlfeedactive:
    th.Thread(target=docapture, daemon=True).start()
    th.Thread(target=omnomnomimeatingtheframes, daemon=True).start()

if outputs:
    th.Thread(target=dowrite, daemon=True).start()
    if not mute:
        set_post_mix(postmix)
        th.Thread(target=dowriteaudio, daemon=True).start()

xfbg = pg.image.load("xfbg.png")

def safedivide(x, y):
    if y == 0:
        return 0
    else:
        return x/y

subpage = 0

testmov = 0

iconidx = 0
iconidx2 = 0
iconidx3 = 0

def windreduce(text):
    rep = {"NNE": "NE", "ENE": "NE", "ESE": "SE", "SSE": "SE", "SSW": "SW", "WSW": "SW", "WNW": "NW", "NNW": "NW"}
    if text in rep:
        return rep[text]
    return text

class AccuraterClock():
    def __init__(self):
        #next_frame holds the target time for the next frame (perf_counter)
        self.next_frame = tm.perf_counter()
        #amount of time in seconds to sleep before switching wait method
        self.spin_threshold = 0.002
    def tick(self, fps):
        now = tm.perf_counter()
        frame_duration = 1.0 / float(fps)

        if now - self.next_frame > 0.5:
            #reset timer
            self.next_frame = now + frame_duration

        #if we're behind, speed up a little
        if self.next_frame <= now:
            self.next_frame = now + frame_duration
            return 1000.0 / float(fps)

        #wait time
        wait = self.next_frame - now

        if wait > self.spin_threshold:
            tm.sleep(max(0.0, wait - self.spin_threshold))

        while tm.perf_counter() < self.next_frame:
            pass

        # schedule next frame
        self.next_frame += frame_duration

        return 1000.0 / float(fps)

class AccurateClock():
    def __init__(self):
        self.drift = 0
        self.last = tm.perf_counter()
    def tick(self, fps):
        #last frame took 8ms?
        diff = tm.perf_counter()-self.last
        #8ms diff
        self.drift += diff
        #add 8ms to drift
        self.drift -= 1/fps
        #subtract frame time
        #diff is negative, wait
        self.drift = min(self.drift, -1/fps)
        self.drift = max(self.drift, 2)
        if self.drift < 0:
            tm.sleep(-self.drift)
            self.drift = 0
        self.last = tm.perf_counter()
        return 1000/fps

working = True
cl = AccuraterClock()

serial = False
fired = False
diag = [0, tm.perf_counter()]
alerting = False
txoff = (screenw-768)//2
with open("introtext.txt") as f:
    intros = f.read().strip().rstrip().split("\n")
def drawreg(surf, pos, ix=0):
    if surf:
        win.blit(surf[ix][0], (pos[0]-surf[ix][0].get_width()//2, pos[1]-surf[ix][0].get_height()//2))
while working:
    for event in pg.event.get():
        if event.type == pg.MOUSEBUTTONDOWN:
            showing += 1
            showing %= 2
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_s:
                pg.image.save(win, "screenshot.png")
                pg.image.save(pg.transform.smoothscale_by(win, (1/1.2, 1)), "screenshot_scaled.png")
                if ldlfeedactive:
                    pg.image.save(latestframe, "latestframe.png")
                continue
            elif event.key == pg.K_j:
                cl.drift = 0
            elif event.key == pg.K_ESCAPE:
                working = False
            elif event.key == pg.K_u:
                veryuppercase = not veryuppercase
            elif event.key == pg.K_t:
                textpos += 1
                textpos %= 4
            elif event.key == pg.K_F3:
                serial = not serial
            else:
                #ui = not ui
                pass
        elif event.type == pg.QUIT:
            working = False
    if not ldlmode:
        colorbug_started = True
    if schedule:
        mn = int(dt.datetime.now().strftime("%M"))
        if mn not in schedule:
            fired = False
        if not fired and mn in schedule:
            fired = True
            ldlmode = False
    your = "Your " if ("oldtitles" in old and textpos > 1) else ""
    delta = cl.tick(60) / 1000
    
    radartime -= delta
    if radartime < 0:
        radartime = radarint*6 + radarhold
    if radartime > radarint*6:
        radaridx = 0
    else:
        radaridx = m.ceil(6-radartime/radarint)
    
    if slide != "intro":
        intropicked = False
    
    def nextslide():
        global slideinterval
        global slideidx
        global ldlmode
        global bg_g
        global radartime
        global crawling
        global ldlon
        global generaldrawidx
        generaldrawidx = 0
        radartime = radarint*6 + radarhold
        slideidx += 1
        bg_g = draw_palette_gradient(pg.Rect(0, 0, screenw, 315), [*bg_c, bg_c[-1]])
        for ext in ext_loaded:
            if 'slide_change' in ext:
                ext_action = ext['pre_draw'](win, {
                    'textpos': textpos,
                    'ldlmode': ldlmode,
                    'ui': ui,
                    'slide': slide,
                    'slideidx': slideidx,
                    'veryuppercase': veryuppercase,
                    'wxdata': wxdata,
                    'clidata': clidata,
                    'radardata': radardata,
                    'locname': locname,
                    'crawlactive': crawlactive,
                    'crawlscroll': crawlscroll,
                    'ldlidx': ldlidx,
                    'alertdata': alertdata,
                    'alertactive': alertactive,
                    'frame_idx_actual': frame_idx_actual #this one isn't as useful but it provides a frame count
                })
                parse_ext_action(ext_action)
        if forever:
            slideidx %= len(flavor)
            slideinterval = flavor_times[slideidx]*seconds
        else:
            if slideidx >= len(flavor):
                ldlmode = True
                crawling = False
                if not foreverldl:
                    ldlon = False
                slideidx = 0
                slideinterval = flavor_times[0]*seconds
            else:
                slideinterval = flavor_times[slideidx]*seconds
    if slideinterval <= 0 and not ldlmode:
        if slide in ["lf", "df"]:
            subpage += 1
            if subpage > 2:
                subpage = 0
                nextslide()
            else:
                slideinterval = flavor_times[slideidx]*seconds
        else:
            nextslide()
    elif ldlmode:
        pass
    else:
        slideinterval -= delta*seconds
    
    slide = flavor[slideidx]
    
    if slide == "intro" and not intropicked:
        introtx = rd.choice(intros)
        intropicked = True
    
    try:
        sanitize = (lambda tx : tx.replace("in the Vicinity", "Near").replace("Thunderstorm", "T'Storm"))
        ccphrase = sanitize(wxdata["current"]["info"]["phraseLong"])
        if len(ccphrase) > len(" Partly Cloudy "): #sorry i had no better text reference
            ccphrase = sanitize(wxdata["current"]["info"]["phraseMedium"])
            if len(ccphrase) > len(" Partly Cloudy "):
                ccphrase = sanitize(wxdata["current"]["info"]["phraseShort"])
    except:
        ccphrase = ""
    
    iconidx += 0.125*delta*seconds
    iconidx %= len(mainicon)
    iconidx2 += 0.125*delta*seconds
    iconidx2 %= max(len(ldllficon), max([len(i) for i in dficons]))
    iconidx3 += 0.125*delta*seconds
    iconidx3 %= 7
    #delta = cl.get_fps()
    crawlinterval -= delta * seconds
    profiling_start()
    if crawlinterval <= 0 and nextcrawlready and crawls:
        crawlactive += 1
        crawlinterval = crawlintervaltime*1
    if crawls:
        crawlactive %= len(crawls)
    if not working or quit_requested:
        for ext in ext_loaded:
            if 'quit' in ext:
                ext_action = ext['quit'](win, {}) #allow extensions to cleanup
                parse_ext_action(ext_action)
        pg.quit()
        break
    for ext in ext_loaded:
        if 'pre_draw' in ext:
            ext_action = ext['pre_draw'](win, {
                'textpos': textpos,
                'ldlmode': ldlmode,
                'ui': ui,
                'slide': slide,
                'veryuppercase': veryuppercase,
                'wxdata': wxdata,
                'clidata': clidata,
                'radardata': radardata,
                'locname': locname,
                'crawlactive': crawlactive,
                'crawlscroll': crawlscroll,
                'ldlidx': ldlidx,
                'alertdata': alertdata,
                'alertactive': alertactive,
                'frame_idx_actual': frame_idx_actual #this one isn't as useful but it provides a frame count
            }) #allow extensions to run code before drawing each frame
            parse_ext_action(ext_action)
    ao = 0
    if textpos >= 2:
        ao = 16
    ldl_y = 0
    if textpos >= 2:
        ldl_y = -16
    if ldlmode:
        win.fill((255, 0, 255))
        win.blit(ws2, (0, 0))
        if ldlfeedactive and latestframe is not None:
            win.fill((0, 0, 0))
            win.blit(latestframe, (screenw//2-latestframe.width/2, 240-latestframe.height/2))
    else:
        if (slide == "oldcc"):
            #win.blit(ws1b, (0, 0))
            draw_bg(top_offset=(192*("fullOldCC" not in old)), all_offset=ao, bh_offset=ao//2)
        else:
            #win.blit(ws1, (0, 0))
            spec = ["al", "df"]
            draw_bg(all_offset=ao, bh_offset=ao//2, special=(slide if slide in spec else None), box=(slide != "xf"))
            if slide == "xf":
                for i in range(3+widescreen):
                    win.blit(xfbg, (46+230*i+13*widescreen, 101-round(ao*1.5)))
    profiling_end("ops")
    if not ldlmode:
        win.blit(logo, (txoff//3, ldl_y))
    
    if ui and not ldlmode:
        if slide in ["cc", "oldcc"]:
            if slide == "oldcc":
                #commented out for now, i need to decide how historically accurate i want this to be
                #see: twcarchive ws4000 timeline (february 20, 1991 update)
                # if textpos >= 2:
                if True:
                    ln = f"Now at {locname}"
                    if veryuppercase:
                        ln = ln.upper()
                    drawshadow(startitlefont, ln, 194+txoff//3, 30, 3, mono=18, ofw=1.07)
                # else:
                #     drawshadow(startitlefont, "Current", 194+txoff//3, 25+ldl_y, 3, color=yeller, mono=18, ofw=1.07, bs=True, upper=veryuppercase)
                #     drawshadow(startitlefont, "Conditions", 194+txoff//3, 52+ldl_y, 3, color=yeller, mono=18, ofw=1.07, bs=True, upper=veryuppercase)
                if wxdata is None:
                    if veryuppercase:
                        drawpage(["NO REPORT AVAILABLE"])
                    else:
                        drawshadow(starfont32, "       No Report Available", 80+txoff, 109+linespacing*2.5+ldl_y, 3, mono=gmono)
                else:
                    page = [
                        ccphrase
                    ]
                    if wxdata["current"]["conditions"]["feelsLike"] == wxdata["current"]["conditions"]["temperature"]:
                        additional = ""
                    elif wxdata["current"]["conditions"]["feelsLike"] < wxdata["current"]["conditions"]["temperature"]:
                        additional = "               Wind Chill:"
                        additional += (padtext(wxdata["current"]["conditions"]["feelsLike"], 3) + "°"+temp_symbol)
                    else:
                        additional = "               Heat Index:"
                        additional += (padtext(wxdata["current"]["conditions"]["feelsLike"], 3) + "°"+temp_symbol)
                    page.append(textmerge(f'Temp:{padtext(wxdata["current"]["conditions"]["temperature"], 3)}°'+temp_symbol,
                                        additional))
                    page.append(textmerge(f'Humidity: {wxdata["current"]["conditions"]["humidity"]}%',
                                    f'                 Dewpoint:{padtext(wxdata["current"]["conditions"]["dewPoint"], 3)}°'+temp_symbol))
                    
                    if metric:
                        bp = f'{wxdata["current"]["conditions"]["pressure"]/10:.1f}'
                    else:
                        bp = f'{wxdata["current"]["conditions"]["pressure"]:5.2f}'
                    bptext = f'Barometric Pressure: {bp}'
                    pt = wxdata["current"]["conditions"]["pressureTendency"]
                    if pressuretrend == False:
                        bptext += " in." if not metric else "kPa"
                    elif pt == 0:
                        bptext += " S"
                    elif pt in [1, 3]:
                        bptext += " R"
                    elif pt in [2, 4]:
                        bptext += " F"
                    page.append(bptext)
                    
                    wndtext = textmerge(f'Wind: {padtext(wxdata["current"]["conditions"]["windCardinal"], 3)}',
                                    f'          {wxdata["current"]["conditions"]["windSpeed"]} {speed_unit}')
                    if wxdata["current"]["conditions"]["windSpeed"] == 0:
                        wndtext = "Wind: Calm"
                
                    if wxdata["current"]["conditions"]["windGusts"] is not None:
                        wndtext = textmerge(wndtext, f'                  Gusts to  {wxdata["current"]["conditions"]["windGusts"]}')
                    page.append(wndtext)
                    
                    ceil = f':{padtext(wxdata["current"]["conditions"]["cloudCeiling"], 5)}{short_dist}'
                    if wxdata["current"]["conditions"]["cloudCeiling"] is None:
                        ceil = " Unlimited"
                        if "ceiling_colon" in old:
                            ceil = ":" + ceil[1:]
                    else:
                        ceil = padtext(f'{wxdata["current"]["conditions"]["cloudCeiling"]} {short_dist}', 10)
                    cltext = f'Visib:  {padtext(int(wxdata["current"]["conditions"]["visibility"]), 2)} {long_dist} Ceiling' + ceil
                    page.append(cltext)
                    
                    if veryuppercase:
                        page = [p.upper() for p in page]
                    drawpage(page)
                
            else:
                if textpos >= 2:
                    ln = f"Now at {locname}"
                    if veryuppercase:
                        ln = ln.upper()
                    drawshadow(startitlefont, ln, 194+txoff//3, 46+ldl_y, 3, mono=18, ofw=1.07)
                else:
                    drawshadow(startitlefont, "Current", 194+txoff//3, 25+ldl_y, 3, color=yeller, mono=18, ofw=1.07, bs=True, upper=veryuppercase)
                    drawshadow(startitlefont, "Conditions", 194+txoff//3, 52+ldl_y, 3, color=yeller, mono=18, ofw=1.07, bs=True, upper=veryuppercase)
                
                if not wxdata:
                    drawshadow(starfont32, "       No Report Available", 80+txoff, 109+linespacing*2.5, 3, mono=gmono)
                else:
                    drawshadow(starfont32, locname, 367+txoff, 91+ldl_y, 3, color=yeller, ofw=1.07, mono=15, upper=veryuppercase)
                    
                    drawshadow(starfont32, "Humidity:", 394+txoff, 133+ldl_y, 3, ofw=1.07, mono=15, upper=veryuppercase)
                    drawshadow(starfont32, f"{padtext(wxdata['current']['conditions']['humidity'], 3)}%", 576+txoff, 133+ldl_y, 3, mono=19, upper=veryuppercase)
                    
                    drawshadow(starfont32, "Dewpoint:", 394+txoff, 176+ldl_y, 3, ofw=1.07, mono=15, upper=veryuppercase)
                    drawshadow(starfont32, f"{padtext(wxdata['current']['conditions']['dewPoint'], 3)}°", 576+txoff, 176+ldl_y, 3, mono=19, upper=veryuppercase)
                    
                    drawshadow(starfont32, "Ceiling:", 394+txoff, 219+ldl_y, 3, ofw=1.07, mono=14.5, upper=veryuppercase)
                    
                    if wxdata["current"]["conditions"]["cloudCeiling"] is None:
                        drawshadow(starfont32, "Unlimited", 519+txoff, 219+ldl_y, 3, ofw=1.07, mono=14.5, upper=veryuppercase, char_offsets={})
                    else:
                        ceil = padtext(f'{wxdata["current"]["conditions"]["cloudCeiling"]}{short_dist}', 9)
                        drawshadow(starfont32, ceil, 526+txoff, 219+ldl_y, 3, ofw=1.07, mono=14.5, upper=veryuppercase, char_offsets={})
                    
                    drawshadow(starfont32, "Visibility:", 394+txoff, 261+ldl_y, 3, ofw=1.07, mono=14.5, upper=veryuppercase)
                    drawshadow(starfont32, f"  {padtext(round(wxdata['current']['conditions']['visibility']), 2)}{long_dist}", 540+txoff, 261+ldl_y, 3, mono=17.5, upper=veryuppercase)
                    
                    if metric:
                        bp = f'{wxdata["current"]["conditions"]["pressure"]/10:.2f}'
                    else:
                        bp = f'{wxdata["current"]["conditions"]["pressure"]:5.2f}'
                    drawshadow(starfont32, "Pressure :" if ("ccspace" in old and not metric) else "Pressure:", 394+txoff, 304+ldl_y, 3, ofw=1.07, mono=14.5, upper=veryuppercase)
                    drawshadow(starfont32, bp, 537-12*metric+txoff, 304+ldl_y, 3, mono=18, char_offsets={}, upper=veryuppercase)
                    pt = wxdata["current"]["conditions"]["pressureTendency"]
                    if pt == 0:
                        drawshadow(starfont32, f"     S", 543+txoff, 304+ldl_y, 3, mono=18, color=yeller, char_offsets={}, upper=veryuppercase)
                    elif pt in [1, 3]:
                        drawshadow(starfont32, f"     ↑", 543+txoff, 304+ldl_y, 3, mono=18, color=yeller, char_offsets={}, upper=veryuppercase, jr_override=jrfontsymbol)
                    elif pt in [2, 4]:
                        drawshadow(starfont32, f"     ↓", 543+txoff, 304+ldl_y, 3, mono=18, color=yeller, char_offsets={}, upper=veryuppercase, jr_override=jrfontsymbol)
                    
                    if wxdata["current"]["conditions"]["feelsLike"] == wxdata["current"]["conditions"]["temperature"]:
                        additional = ""
                    elif wxdata["current"]["conditions"]["feelsLike"] < wxdata["current"]["conditions"]["temperature"]:
                        additional = "Wind Chill:"
                    else:
                        additional = ""
                    if additional:
                        drawshadow(starfont32, additional, 394+txoff, 347+ldl_y, 3, ofw=1.07, mono=15, upper=veryuppercase)
                        drawshadow(starfont32, f"{padtext(wxdata['current']['conditions']['feelsLike'], 3)}°", 576+txoff, 347+ldl_y, 3, mono=19, upper=veryuppercase)
                    
                    drawshadow(largefont32, f"{padtext(wxdata['current']['conditions']['temperature'], 3)}°", 170+txoff, 99+ldl_y, 3, ofw=1.125, mono=22.1, char_offsets={}, upper=veryuppercase)
    
                    
                    mm = pg.transform.smoothscale_by(mainicon[m.floor(iconidx) % len(mainicon)][0], (1.2, 1))
                    ioff = (0, 0)
                    if icontable[wxdata['current']['info']['iconCode']] in icon_offset:
                        ioff = icon_offset[icontable[wxdata['current']['info']['iconCode']]]
                    win.blit(mm, (220-mm.width//2+ioff[0]+txoff, 215-mm.height//2+ioff[1]+ldl_y))
                    
                    cctx = ccphrase
                    drawshadow(extendedfont, cctx, 168-18*(m.floor(len(cctx)/2)-2)+9+txoff, 139+ldl_y, 3, ofw=1.1, mono=18.9, char_offsets={":": 2, "i":2}, upper=veryuppercase)
                    if wxdata["current"]["conditions"]["windSpeed"] == 0:
                        drawshadow(extendedfont, f"Wind: Calm", 95+txoff, 303+ldl_y, 3, ofw=1.1, mono=18.9, char_offsets={":": 2, "i":2}, upper=veryuppercase)
                    else:
                        drawshadow(extendedfont, f"Wind: {padtext(wxdata['current']['conditions']['windCardinal'], 3)}  {padtext(wxdata['current']['conditions']['windSpeed'], 2)}", 95+txoff, 303+ldl_y, 3, ofw=1.1, mono=19, char_offsets={":": -3}, upper=veryuppercase)
                    if wxdata['current']['conditions']['windGusts'] is not None:
                        drawshadow(extendedfont, f"Gusts to", 95+txoff, 345+ldl_y, 3, ofw=1, mono=18.9, char_offsets={"u": 3, "s": 2}, upper=veryuppercase)
                        drawshadow(extendedfont, padtext(wxdata['current']['conditions']['windGusts'], 2), 272+txoff, 345+ldl_y, 3, ofw=1.1, mono=24, char_offsets={}, upper=veryuppercase)
                
        elif slide == "lo":
            drawshadow(startitlefont, "Latest Observations", 181+txoff//3, 39+ldl_y, 3, color=yeller, mono=15.5, ofw=1.07, bs=True, upper=veryuppercase)
            page = []
            for l in obsloc:
                if l[2] == None:
                    page.append(textmerge(l[1], "                  No Report"))
                else:
                    ol = textmerge(l[1], f"              {padtext(l[2]['current']['conditions']['temperature'], 3)} {shorten_phrase(l[2]['current']['info']['phraseShort'])}")
                    ws = l[2]['current']['conditions']['windSpeed']
                    if ws > 9:
                        ol = textmerge(ol, f"                            {windreduce(l[2]['current']['conditions']['windCardinal'])}")
                        page.append(textmerge(ol, f"                              {ws}"))
                    elif ws == 0:
                        page.append(textmerge(ol, f"                            Calm"))
                    else:
                        ol = textmerge(ol, f"                            {l[2]['current']['conditions']['windCardinal']}")
                        page.append(textmerge(ol, f"                               {ws}"))
            # drawpage(["Cincinnati Apt 63 Cloudy    S 23",
            #         "Birmingham     63 T'Storm   S 16",
            #         "Mobile         74 Cloudy    S 24",
            #         "Montgomery     67 Fair      S 10",
            #         "New Orleans    75 Cloudy    SW13",
            #         "Panama City    70 Fair      S 10",
            #         "Pensacola Arpt 73 P Cloudy  S 23"],
            #         "               °F WEATHER   WIND")
            
            if veryuppercase:
                page = [p.upper() for p in page]
            drawpage2(page, f"               °{temp_symbol} WEATHER   WIND")
        elif slide == "ro":
            drawshadow(startitlefont, your+"Latest Observations", 181, 39+ldl_y, 3, color=yeller, mono=15.5, ofw=1.07, bs=True, upper=veryuppercase)
            drawpage(["Cincinnati Apt 63 Cloudy    S 23",
                    "Birmingham     63 T'Storm     16",
                    "Mobile         74 Cloudy      24",
                    "Montgomery     67 Fair        10",
                    "New Orleans    75 Cloudy      13",
                    "Panama City    70 Fair        10",
                    "Pensacola Arpt 73 P Cloudy    23"],
                    f"                    WEATHER   °{temp_symbol}")
        elif slide == "lf":
            drawshadow(startitlefont, your+"Local Forecast" if not ("your" in old) else "Your Local Forecast", 181+txoff//3, 39+ldl_y, 3, color=yeller, mono=15.5, ofw=1.07, bs=True, upper=veryuppercase)
            #win.blit(pg.transform.smoothscale_by(noaa, (1.2, 1)), (412, 40))
            
            if wxdata:
                fcsts = wxdata["extended"]["daypart"]
                # txt = ""
                # for fcst in fcsts[:3]:
                #     txt += (fcst["name"][0].upper() + fcst["name"][1:].lower()) + "..." + fcst["narration"]
                #     txt += "\n"
                text = (fcsts[subpage]["name"][0].upper() + fcsts[subpage]["name"][1:].lower()) + "..." + fcsts[subpage]["narration"]
                if veryuppercase:
                    text = text.upper()
                
                drawpage(wraptext(text))
        elif slide == "lr":
            if radardata:
                win.blit(radardata[radaridx][0], (0, 0))
            if screenw > 768:
                win.blit(radarLeft, (0, 0))
                win.blit(radarRight, (screenw-radarRight.get_width(), 0))
            win.blit(radarHeader, (screenw//2 - radarHeader.get_width()//2, 0))
            win.blit(logorad, (screenw//2 - radarHeader.get_width()//2, 0))
        elif slide == "cr":
            if radardata:
                win.blit(radardata[0][0], (0, 0))
            if screenw > 768:
                win.blit(radarLeftC, (0, 0))
                win.blit(radarRightC, (screenw-radarRightC.get_width(), 0))
            win.blit(radarHeaderC, (screenw//2 - radarHeaderC.get_width()//2, 0))
            win.blit(logorad, (screenw//2 - radarHeaderC.get_width()//2, 0))
        elif slide == "al":
            def supper(text):
                if "uppercaseAMPM" in old:
                    return text.upper()
                return text
            drawshadow(startitlefont, "Almanac", 181+txoff//3, 39+ldl_y, 3, color=yeller, mono=18, ofw=1.07, bs=True, upper=veryuppercase)
            if aldata["sun"]:
                drawshadow(starfont32, "Sunrise:", 76+txoff, 114+ldl_y, 3, mono=gmono, char_offsets={})
                drawshadow(starfont32, " Sunset:", 76+txoff, 144+ldl_y, 3, mono=gmono, char_offsets={})
                
                d1 = dt.date.today().strftime("%A")
                drawshadow(starfont32, d1, 286+18*4.5-len(d1)*18/2+txoff, 85+ldl_y, 3, mono=gmono, char_offsets={}, color=yeller)
                d2 = ( dt.date.today()+dt.timedelta(days=1)).strftime("%A")
                drawshadow(starfont32, d2, 213+286+18*4.5-len(d2)*18/2+txoff, 85+ldl_y, 3, mono=gmono, char_offsets={}, color=yeller)

                sunrise1 = dt.datetime.fromtimestamp(aldata["sun"]["sunrise1"])
                sunset1 = dt.datetime.fromtimestamp(aldata["sun"]["sunset1"])
                sunrise2 = dt.datetime.fromtimestamp(aldata["sun"]["sunrise2"])
                sunset2 = dt.datetime.fromtimestamp(aldata["sun"]["sunset2"])
                
                drawshadow(starfont32, supper(splubby_the_return(sunrise1.strftime("%I:%M %p"))), 305+txoff, 114+ldl_y, 3, mono=gmono, char_offsets={})
                drawshadow(starfont32, supper(splubby_the_return(sunset1.strftime("%I:%M %p"))), 305+txoff, 144+ldl_y, 3, mono=gmono, char_offsets={})
                
                drawshadow(starfont32, supper(splubby_the_return(sunrise2.strftime("%I:%M %p"))), 518+txoff, 114+ldl_y, 3, mono=gmono, char_offsets={})
                drawshadow(starfont32, supper(splubby_the_return(sunset2.strftime("%I:%M %p"))), 518+txoff, 144+ldl_y, 3, mono=gmono, char_offsets={})
            if aldata["moon"]:
                drawshadow(starfont32, "Moon Data:", 76+txoff, 191+ldl_y, 3, mono=gmono, char_offsets={}, color=yeller)
                for i in range(4):
                    moondt = aldata["moon"][i]
                
                    mt = moondt[0]
                    xx = i*151
                    drawshadow(starfont32, mt, 112+18*1.5-len(mt)*9+xx+txoff, 224+ldl_y, 3, mono=gmono, char_offsets={})

                    dat = padtext(moondt[1], 6)
                    mn = pg.transform.smoothscale_by({"New": moon_new, "First": moon_fq, "Full": moon_full, "Last": moon_lq}[mt], (1.2, 1))

                    win.blit(mn, (80+xx+txoff, 265+ldl_y))
                    
                    drawshadow(starfont32, dat, 76+xx+txoff, 354+ldl_y, 3, mono=gmono, char_offsets={})
        elif slide == "xf":
            drawshadow(startitlefont, efname, 180+txoff//3, 23+ldl_y, 3, mono=15, ofw=1.07, upper=veryuppercase)
            drawshadow(startitlefont, "Extended Forecast", 180+txoff//3, 49+ldl_y, 3, mono=15, ofw=1.07, upper=veryuppercase, color=yeller)
            def sane(text):
                text = text.replace("Thunderstorm", "T'Storm")
                if len(wraptext(text, 10)) > 2:
                    if "/" in text:
                        tl = list(text)
                        tl.insert(text.index("/")+1, " ")
                        text = "".join(tl)
                        return text
                for tx in text.split(" "):
                    if len(tx) > 10:
                        break
                else:
                    return text
                if "/" in text:
                    tl = list(text)
                    tl.insert(text.index("/")+1, " ")
                    text = "".join(tl)
                
                return text
            to = 13*widescreen
            yo = -round(ao*1.5)
            for i in range(3+widescreen):
                drawshadow(starfont32, "Lo", 118+i*230-18*2+to, 314+yo, 3, mono=gmono, color=(120, 120, 222))
                drawshadow(starfont32, "Hi", 118+i*230+18*3+to, 314+yo, 3, mono=gmono, color=yeller)
            if wxdata:
                for i in range(3+widescreen):
                    d = dt.date.today() + dt.timedelta(days=(i+2+subpage*3))
                    colow = {"color": yeller} if "whiteXF" not in old else {}
                    drawshadow(starfont32, d.strftime("%a").upper(), 118+i*230+to, 106+yo, 3, mono=gmono, **colow)
                    ix = i*2+4+subpage*6-(wxdata["extended"]["daypart"][0]["dayOrNight"] == "N")
                    fctx = sane(wxdata["extended"]["daypart"][ix]["phraseLong"])
                    fctx = wraptext(fctx, 10)
                    fctx = [f.strip().rstrip() for f in fctx]
                    for j, l in enumerate(fctx):
                        drawshadow(starfont32, l, 118+i*230+27-len(l)*9+to, 245+j*36+yo, 3, mono=gmono)
                    lo = str(wxdata["extended"]["daypart"][ix+1]["temperature"])
                    drawshadow(largefont32, lo, 114+i*230-18*2+24-len(lo)*12+to, 344+yo, 3, mono=25)
                    
                    hi = str(wxdata["extended"]["daypart"][ix]["temperature"])
                    drawshadow(largefont32, hi, 114+i*230+18*3+24-len(hi)*12+to, 344+yo, 3, mono=25)
                    if xficons[i+subpage*3]:
                        xi = xficons[i+subpage*3][int(iconidx3%len(xficons[i+subpage*3]))][0]
                        xi = pg.transform.smoothscale_by(xi, (1.2, 1))
                        win.blit(xi, (120+i*230+27-xi.get_width()/2+to, 200-xi.get_height()/2+yo))
            else:
                drawshadow(starfont32, "Temporarily Unavailable", 177, 218, 3, mono=gmono)
        elif slide == "ol":
            drawshadow(startitlefont, "Outlook", 194+txoff//3, 39+ldl_y, 3, color=yeller, mono=16, ofw=1.07, bs=True, upper=veryuppercase)
            if clidata:
                drawpage([
                    "\n",
                    "        30 Day Outlook",
                    f"           {dt.date.today().strftime('%B').upper()}",
                    "",
                    f"Temperatures:  {['Normal', 'Above normal', 'Below normal'][clidata['temp_outlook']]}",
                    "",
                    f"Precipitation: {['Normal', 'Above normal', 'Below normal'][clidata['precip_outlook']]}"
                ], vshift=-20)
        elif slide == "sf":
            drawshadow(startitlefont, "School", 194+txoff//3, 25+ldl_y, 3, color=yeller, mono=18, ofw=1.07, bs=True, upper=veryuppercase)
            drawshadow(startitlefont, "Forecast", 194+txoff//3, 52+ldl_y, 3, color=yeller, mono=18, ofw=1.07, bs=True, upper=veryuppercase)
            
            if wxdata is None:
                drawshadow(starfont32, "       No Report Available", 80+txoff, 109+linespacing*2.5, 3, mono=gmono)
            else:
                fcsts = wxdata["hourly"]
                page = []
                times = []
                for fcst in fcsts:
                    dat = dt.datetime.fromtimestamp(fcst["valid"])
                    hour = dat.hour
                    if hour in [6, 7, 8, 13, 14, 15, 16]:
                        times.append((fcst, dat.strftime("%I:%M %p")[1:]))
                for time in times:
                    line = time[1]
                    line = textmerge(line, f"        {shorten_phrase(time[0]['phraseShort'])}")
                    line = textmerge(line, f"                  {round(time[0]['temperature'])}")
                    line = textmerge(line, f"                     {min(round(time[0]['rainChance']+time[0]['snowChance']+time[0]['sleetChance']+time[0]['freezingRainChance']), 100)}%")
                    precip_type = None
                    ch = [(time[0]['snowChance'], 'Snow'), (time[0]['sleetChance'], 'Sleet'), (time[0]['freezingRainChance'], 'FrzRn'), (time[0]['rainChance'], 'Rain')]
                    ch2 = sorted(ch, key=lambda x: x[0], reverse=True)
                    if ch2[0][0] == 0:
                        precip_type = ""
                    else:
                        precip_type = ch2[0][1]
                    line = textmerge(line, f"                          {precip_type}")
                    
                    page.append(line)
                drawpage(page, f"        WEATHER   °{temp_symbol} PRECIP")
        elif slide == "df":
            drawshadow(startitlefont, "Daypart Forecast", 181+txoff//3, 39+ldl_y, 3, color=yeller, mono=15.5, ofw=1.07, bs=True, upper=veryuppercase)
            if not wxdata:
                drawshadow(starfont32, "       No Report Available", 80, 109+linespacing*2.5+ldl_y, 3, mono=gmono)
            else:
                for i  in range(4):
                    j = i+4+subpage*4
                    header = wxdata["extended"]["daypart"][j]["name"].upper()
                    header = textmerge(header, f"                {'HI' if wxdata['extended']['daypart'][j]['dayOrNight'] == 'D' else 'LO'}  WIND")
                    drawshadow(smallfont, header, 62+14+txoff, 84+ldl_y+77*i+9, 3, mono=gmono)
                    ps = wxdata["extended"]["daypart"][j]["phraseShort"]
                    pl = wxdata["extended"]["daypart"][j]["phraseLong"]
                    drawshadow(starfont32, ps if len(pl) > 14 else pl, 62+14+txoff, 96+14+ldl_y+77*i+9, 3, mono=gmono)
                    drawshadow(starfont32, str(wxdata["extended"]["daypart"][j]["temperature"]), 62+14+txoff+18*16, 96+14+ldl_y+77*i+9, 3, mono=gmono)
                    ws = wxdata["extended"]["daypart"][j]["windSpeed"]
                    wc = wxdata["extended"]["daypart"][j]["windCardinal"]
                    if ws > 9:
                        wt = textmerge(windreduce(wc), f"  {ws}")
                    elif ws == 0:
                        wt = "Calm"
                    else:
                        wt = textmerge(wc, f"   {ws}")
                    drawshadow(starfont32, wt, 62+14+txoff+18*20, 96+14+ldl_y+77*i+9, 3, mono=gmono)
                    drawreg(dficons[i], (640, 96+14+ldl_y+77*i+24), ix=(m.floor(iconidx2) % len(dficons[i])))
        elif slide == "intro":
            drawshadow(startitlefont, "Welcome!", 181+txoff//3, 39+ldl_y, 3, color=yeller, mono=15.5, ofw=1.07, bs=True, upper=veryuppercase)

            generaldrawidx += 3.5
            dr = generaldrawidx*1
            it = f"Hello, {locname}!"
            tx, dr = drawing(it, dr, True)
            drawshadow(largefont32, tx, 98+txoff, 109+linespacing/2+ldl_y, 3, mono=20)
            
            for i, line in enumerate(wraptext(introtx, 30)):
                tx, dr = drawing(line, dr, True)
                drawshadow(starfont32, tx, 98+txoff, 109+linespacing*1.75+32*i+ldl_y, 3, mono=gmono, char_offsets={})
                #dr -= len(line.replace(" ", ""))
        elif slide == "test":
            drawshadow(startitlefont, "Test Page", 181, 25+ldl_y, 3, color=yeller, mono=15.5, ofw=1.07, bs=True)
            drawshadow(startitlefont, "of Awesomeness", 181, 54+ldl_y, 3, color=yeller, mono=15.5, ofw=1.07, bs=True)
            drawshadow(starfont32, "       No Report Available", 80, 109+linespacing*2.5+ldl_y, 3, mono=gmono)
    
    nn = dt.datetime.now()
    al1 = False
    if not alerting:
        al1 = True
    alerting = (len(alertdata[1]) > 0)
    if alerting != switches[3]:
        switches[3] = alerting
        sendtoall(f"switch 3 {int(alerting)}\n".encode())
        
    if al1 and alerting and not mute:
        beepch.play(beep)
    if alerting:
        crawling = True
    if ldlon and ldlmode:
        colorbug_started = False
    #here for testing
    #pg.draw.rect(win, (187, 17, 0), pg.Rect(0, 404, screenw, 76))
    ldl_y_off = -2
    if (ldlon and not serial) or not ldlmode or alerting:
        if serial:
            drawshadow(smallfont, "SN: 000000v1.0 SW:00000000 DQ:100", 78, 402.5-8, 3, mono=gmono, char_offsets={})
            drawshadow(smallfont, "RLYS:0110 BAUD:9600 SENSORS:N/A", 78, 402.5+24, 3, mono=gmono, char_offsets={})
        elif not crawling and not ((slide in ["lr", "cr"]) and not ldlmode):
            profiling_start()
            ldltext = ""
            ooo = True
            ldlextra = (4 if screenw > 768 else 0)
            ldlspace = ((ldlextra * 2) * " ") if ldlextra else ""
            if ldlidx == 0:
                if not veryuppercase:
                    ldltext = f"Conditions at {locname}"
                else:
                    ldltext = f"CONDITIONS AT {locname}"
            elif ldlidx == 1:
                if wxdata is not None:
                    ldltext = ccphrase
            elif ldlidx == 2:
                if wxdata is not None:
                    if wxdata["current"]["conditions"]["feelsLike"] == wxdata["current"]["conditions"]["temperature"]:
                        additional = ""
                    elif wxdata["current"]["conditions"]["feelsLike"] < wxdata["current"]["conditions"]["temperature"]:
                        additional = ldlspace + "               Wind Chill:"
                        additional += (padtext(wxdata["current"]["conditions"]["feelsLike"], 3) + f"°{temp_symbol}")
                    else:
                        additional = ldlspace + "               Heat Index:"
                        additional += (padtext(wxdata["current"]["conditions"]["feelsLike"], 3) + f"°{temp_symbol}")
                    ldltext = textmerge(f'Temp:{padtext(wxdata["current"]["conditions"]["temperature"], 3)}°{temp_symbol}',
                                        additional)
            elif ldlidx == 3:
                if wxdata is not None:
                    ldltext = textmerge(f'Humidity: {wxdata["current"]["conditions"]["humidity"]}%',
                                        f'{ldlspace}                 Dewpoint:{padtext(wxdata["current"]["conditions"]["dewPoint"], 3)}°{temp_symbol}')
                    #ldltext = "Humidity: 100%   Dewpoint: 57°F"
            elif ldlidx == 4:
                if wxdata is not None:
                    if metric:
                        bp = f'{wxdata["current"]["conditions"]["pressure"]/10:.2f}'
                    else:
                        bp = f'{wxdata["current"]["conditions"]["pressure"]:5.2f}'
                    ldltext = f'Barometric Pressure: {bp}'
                    pt = wxdata["current"]["conditions"]["pressureTendency"]
                    if pressuretrend == False:
                        ldltext += " in." if not metric else "kPa"
                    elif pt == 0:
                        ldltext += " S"
                    elif pt in [1, 3]:
                        ldltext += " R"
                    elif pt in [2, 4]:
                        ldltext += " F"
            elif ldlidx == 5:
                if wxdata is not None:
                    ldltext = textmerge(f'Wind: {padtext(wxdata["current"]["conditions"]["windCardinal"], 3)}',
                                        f'          {wxdata["current"]["conditions"]["windSpeed"]} {speed_unit}')
                    if wxdata["current"]["conditions"]["windSpeed"] == 0:
                        ldltext = "Wind: Calm"
                    
                    if wxdata["current"]["conditions"]["windGusts"] is not None:
                        ldltext = textmerge(ldltext, f'{ldlspace}                  Gusts to  {wxdata["current"]["conditions"]["windGusts"]}')
            elif ldlidx == 6:
                if wxdata is not None:
                    ceil = f':{padtext(wxdata["current"]["conditions"]["cloudCeiling"], 5)}{short_dist}'
                    if wxdata["current"]["conditions"]["cloudCeiling"] is None:
                        if "ceiling_colon" in old:
                            ceil = ":Unlimited"
                        else:
                            ceil = " Unlimited"
                    ldltext = f'Visib:  {padtext(int(wxdata["current"]["conditions"]["visibility"]), 2)} {long_dist} {ldlspace}Ceiling' + ceil
            elif ldlidx == 7:
                if clidata is not None:
                    ldltext = f"{nn.strftime('%B')} Precipitation: {clidata['month_precip']}in"
            elif ldlidx == 8 and extraldltext:
                ldltext = extraldltext
            elif (ldlidx == 9 or (ldlidx == 8 and not extraldltext)):
                fc = (wxdata["extended"]["daypart"][0]["dayOrNight"] == "N")
                ooo = False
                xx = 72-ldlextra*18+txoff
                mm = pg.transform.smoothscale_by(ldllficon[m.floor(iconidx2) % len(ldllficon)][0], (1.2, 1))
                if fc == 0:
                    drawshadow(starfont32, "Today" , xx, 409, 3, mono=15, color=yeller)
                    drawshadow(starfont32, "'" , xx+72, 409, 3, mono=15, color=yeller)
                    drawshadow(starfont32, "s Forecast:" , xx+85, 409, 3, mono=15, color=yeller)
                    drawshadow(starfont32, "               High:" , xx+85+50+ldlextra*2*18, 409, 3, mono=18, color=yeller)
                    drawshadow(starfont32,f"                    {padtext(wxdata['extended']['daypart'][0]['temperature'], 3)}°{temp_symbol}" , xx+85+54+ldlextra*2*18, 409, 3, mono=18)
                    win.blit(mm, (xx+287-25, 418-15))
                elif fc == 1:
                    drawshadow(starfont32, "Tomorrow" , xx, 409, 3, mono=15, color=yeller)
                    drawshadow(starfont32, "'" , xx+72+50, 409, 3, mono=15, color=yeller)
                    drawshadow(starfont32, "s Forecast:" , xx+85+50, 409, 3, mono=15, color=yeller)
                    drawshadow(starfont32, "               High:" , xx+85+50+ldlextra*2*18, 409, 3, mono=18, color=yeller)
                    drawshadow(starfont32,f"                    {padtext(wxdata['extended']['daypart'][1]['temperature'], 3)}°{temp_symbol}" , xx+85+54+ldlextra*2*18, 409, 3, mono=18)
                    win.blit(mm, (xx+337-25, 418-15))
                
            if ldldrawing:
                ldldrawidx += 2.5
                if veryuppercase and ldlidx != 0:
                    ldltext = ldltext.upper()
                ldltext = drawing(ldltext, ldldrawidx)
            profiling_end("ops")
            if ui and ooo:
                drawshadow(starfont32, ldltext, 78+txoff-ldlextra*18, 403+ldl_y_off, 3, mono=gmono, char_offsets={})
            nextcrawlready = True
            
            ldlinterval -= delta*seconds
            if ldlinterval <= 0:
                ldlidx += 1
                ldlidx %= (8 + (ldlmode and bool(extraldltext)) + (ldllf and ldlmode))
                if ldlidx == 0 and not foreverldl:
                    ldlreps -= 1
                if ldlreps <= 0 and not foreverldl:
                    ldlon = False
                if ldlidx == 0 and not ldlmode and (len(crawls) > 0):
                    crawling = True
                    crawlscroll = 0
                ldlinterval = ldlintervaltime*1
                if (ldlidx == 9 or (ldlidx == 8 and not extraldltext)):
                    ldlinterval *= 3
                ldldrawidx = 0
        elif (not (slide in ["lr", "cr"])) or alerting:
            if alerting:
                alertactive %= len(alertdata[1])
                crawl = alertdata[1][alertactive].upper()
            else:
                if len(crawls) > 0:
                    crawl = crawls[crawlactive]
                else:
                    crawl = 0
            nextcrawlready = False
            crawlscroll += 2*delta*seconds
            if alerting:
                pg.draw.rect(win, ((187, 17, 0) if (slide not in ["lr", "cr"] or ("warnpalbug" not in old)) else (128, 16, 0)) if True or "ADVISORY" not in crawl else (126, 31, 0), pg.Rect(0, 404-ao-ao//2, screenw, 76+ao+ao//2))
            jrf = jrfontnormal
            if (((slide in ["lr", "cr"]) or (colorbug_started and colorbug_nat)) and ("warnpalbug" in old) and alerting):
                jrf = jrfontradaralert
            drawshadow(starfont32, crawl, round(screenw-crawlscroll), 403+ldl_y_off, 3, mono=gmono, char_offsets={}, jr_override=jrf)
            if not alerting:
                crawltime -= delta*seconds
            if crawlscroll >= (screenw+(len(crawl)+4)*(gmono if not jr else m.floor(gmono))):
                if alerting:
                    crawlscroll = 0
                    alertactive += 1
                    if not mute:
                        beepch.play(beep)
                else:
                    crawlscroll = 0
                    ldlidx = 0
                    ldldrawidx = 100
            if crawltime <= 0:
                crawltime = crawllen*seconds
                crawling = False
                nextcrawlready = True
    
    #debug mouse pos
    #drawshadow(smallfont, time_fmt(crawlinterval), 5, 440, 3)
    #drawshadow(smallfont, str(pg.mouse.get_pos()), 5, 440, 3)
    
    #timer
    time = " 7:09:14 AM"
    date = " THU MAY  6"
    
    time = splubby_the_return(nn.strftime("%I:%M:%S %p").upper())
    if len(time) < 11:
        time = " " + time
    
    day = splubby_the_return(nn.strftime("%d"))
    if len(day) < 2:
        day = " " + day
    date = nn.strftime(" %a %b ") + day
    
    
    if (type(lastlasttime) != int) and timedrawing:
        tcl = []
        for i, j in enumerate(time):
            if j == lastlasttime[i]:
                tcl.append(white)
            else:
                tcl.append((0, 0, 0))
    else:
        tcl = white
    
    if (ldlon and not serial) or not ldlmode:
        if not ui or ((slide in ["lr", "cr"]) and not ldlmode):
            pass
        elif ldlmode or textpos >= 2:
            txo = ((-6 if textpos <= 2 else ldl_y//2))
            drawshadow(smallfont, time.upper(), 465+round((screenw-768)*2/3), 375+txo, 3, mono=gmono, color=tcl, char_offsets={})
            drawshadow(smallfont, date.upper(), 60+round((screenw-768)/3), 375+txo, 3, mono=gmono, char_offsets={})
        elif slide == "oldcc" and not ldlmode and textpos < 2:
            pass
        elif textpos == 0:
            drawshadow(smallfont, time.upper(), 479+round((screenw-768)*2/3)-2, 35, 3, mono=gmono, color=tcl, char_offsets={})
            drawshadow(smallfont, date.upper(), 479+round((screenw-768)*2/3), 55, 3, mono=gmono, char_offsets={})
        elif textpos == 1:
            drawshadow(smallfont, time.upper(), 465+round((screenw-768)*2/3)-2, 28, 3, mono=gmono, color=tcl, char_offsets={})
            drawshadow(smallfont, date.upper(), 465+round((screenw-768)*2/3), 48, 3, mono=gmono, char_offsets={})

    for ext in ext_loaded:
        if 'post_draw' in ext:
            ext_action = ext['post_draw'](win, {
                'textpos': textpos,
                'ldlmode': ldlmode,
                'ui': ui,
                'slide': slide,
                'veryuppercase': veryuppercase,
                'wxdata': wxdata,
                'clidata': clidata,
                'radardata': radardata,
                'locname': locname,
                'crawlactive': crawlactive,
                'crawlscroll': crawlscroll,
                'ldlidx': ldlidx,
                'alertdata': alertdata,
                'alertactive': alertactive,
                'frame_idx_actual': frame_idx_actual #this one isn't as useful but it provides a frame count
            }) #allow extensions to run per-frame code
            parse_ext_action(ext_action)
    
    if type(lasttime) != int:
        lastlasttime = lasttime + ""
    lasttime = time + ""
    
    clear_profile()

    transform = (1/(1.2 if compress else 1), 1)
    if (rwin.get_width()/rwin.get_height() > (rwidth/480)): #wider
        sl = rwin.get_height()/480
        transform = (sl/(1.2 if compress else 1), sl)
    elif (rwin.get_width()/rwin.get_height() < (rwidth/480)): #taller
        sl = rwin.get_width()/rwidth
        transform = (sl/(1.2 if compress else 1), sl)

    if transform != (1, 1):
        if smoothscale:
            tr = pg.transform.smoothscale_by(win, transform)
        else:
            tr = pg.transform.scale_by(win, transform)
    else:
        tr = win

    rwin.fill((0, 0, 0))
    rwin.blit(tr, (rwin.get_width()/2-tr.get_width()/2, rwin.get_height()/2-tr.get_height()/2))
    pg.display.flip()
    if outputs:
        avbuffer = win.copy()
        avevent.set()
    frame_idx_actual += 1
    p_counter += 1
    p_counter %= 512
    # if tm.perf_counter() - diag[1] >= 1:
    #     print(f"Frames in last second: {diag[0]}", end="\r")
    #     diag = [0, tm.perf_counter()]
    # else:
    #     diag[0] += 1
    
pg.quit()
