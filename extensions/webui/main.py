#import the remoteui module
from extensions.webui.remoteui import RemoteUI

ui = RemoteUI(port=4000, size=(4, 6))
ui.add_img("extensions/webui/web-banner.png", position=(0, 0))

cmd_buffer = []
def pre_draw(win, data={}):
    global forcing_lf
    if cmd_buffer:
        commands = [cmd_buffer.pop(0) for _ in range(len(cmd_buffer))]
        return commands

def set_force():
    cmd_buffer.append(["set_variable", "ldlmode", False])
    cmd_buffer.append(["set_variable", "slideidx", 0])
def pull_the_plug():
    cmd_buffer.append(["quit"])

ui.add_button("Cue LF", "forcelf", set_force, position=(0, 1), size=(1, 1))

ui.add_button("PULL THE PLUG", "plug", pull_the_plug, position=(1, 1), size=(2, 1))

ui.start() #starts the web server thread