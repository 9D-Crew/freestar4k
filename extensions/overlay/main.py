#extension system test
#draws some text over LDL mode from a special file
file = open("extensions/overlay/ldlmode.txt", "r")
overlay = file.read()
file.close()
file2 = open("extensions/overlay/ldlfmt.txt", "r")
formatting = file2.read().strip().split("\n")
file2.close()

print("Overlay extension loaded.")

#will be called at the end of drawing the screen

drawshadow = None
drawpage = None
drawpage_fmt = None
wraptext = None

def init(functions):
    #functions get passed to init
    global drawshadow, drawpage, drawpage_fmt, wraptext
    drawshadow = functions['drawshadow']
    drawpage = functions['drawpage']
    drawpage_fmt = functions['drawpage_fmt']
    wraptext = functions['wraptext']

def post_draw(window, data={}):
    #data contains various variables from main program
    #data['ldlmode'] is whether LDL mode is active
    if data.get('ldlmode', False):
        #draw overlay text unformatted
        drawpage_fmt(wraptext(overlay), formatting)