import pygame

drawshadow = None
drawpage = None
drawpage_fmt = None
wraptext = None
overlay = None

def init(functions):
    #functions get passed to init
    global drawshadow, drawpage, drawpage_fmt, wraptext, overlay
    drawshadow = functions['drawshadow']
    drawpage = functions['drawpage']
    drawpage_fmt = functions['drawpage_fmt']
    wraptext = functions['wraptext']
    overlay = pygame.image.load("extensions/imgoverlay/overlay.png")

def post_draw(window, data={}):
    #data contains various variables from main program
    #data['ldlmode'] is whether LDL mode is active
    if overlay:
        window.blit(overlay, (0, 0))