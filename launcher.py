import wx
import wx.adv
import subprocess as sp
import os
import sys
import runpy
import sounddevice as sd

devices = ["Default"]
devices.extend([e["name"] for e in sd.query_devices() if e["max_output_channels"] > 0])

conf_exist = False
if os.path.exists("conf.py"):
    try:
        existing_conf = runpy.run_path("conf.py")
        conf_exist = True
    except:
        pass
sub = None
if not conf_exist:
    conf_exist = True
    existing_conf = {}

closesim = False

selected_extension_names = existing_conf.get("extensions", [])
extensions_possible = [d for d in os.listdir("extensions") if os.path.isdir(os.path.join("extensions", d))]

class TBIcon(wx.adv.TaskBarIcon):
    def __init__(self, frame):
        wx.adv.TaskBarIcon.__init__(self)
        icon1xi = wx.Icon("launcher/icon_32x32.png", wx.BITMAP_TYPE_PNG)
        self.SetIcon(icon1xi, 'task bar icon')
        self.frame = frame
        self.Bind(wx.EVT_MENU, self.Activate, id=1)
        self.Bind(wx.EVT_MENU, self.Deactivate, id=2)
        self.Bind(wx.EVT_MENU, self.Close, id=3)
    
    def CreatePopupMenu(self):
        menu = wx.Menu()
        menu.Append(1, 'Show Launcher')
        menu.Append(2, 'Hide Launcher')
        menu.AppendSeparator()
        menu.Append(3, 'Close Launcher + Sim')

        return menu
    
    def Close(self, event):
        global closesim
        closesim = True
        self.frame.Close()


    def Activate(self, event):
        if not self.frame.IsShown():
            self.frame.Show()


    def Deactivate(self, event):
        if self.frame.IsShown():
            self.frame.Hide()
    

class Launcher(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="FreeStar 4k Launcher", size=(768, 480))
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.nb = wx.Notebook(panel)
        
        icon05x = wx.Icon("launcher/icon_16x16.png", wx.BITMAP_TYPE_PNG)
        icon1x = wx.Bitmap("launcher/icon_32x32.png", wx.BITMAP_TYPE_PNG)
        icon2x = wx.Icon("launcher/icon_64x64.png", wx.BITMAP_TYPE_PNG)
        icon4x = wx.Icon("launcher/icon_128x128.png", wx.BITMAP_TYPE_PNG)
        
        icon1xi = wx.Icon("launcher/icon_32x32.png", wx.BITMAP_TYPE_PNG)
        self.SetIcon(icon1xi)
        self.taskic = TBIcon(self)
        
        ib = wx.IconBundle()
        ib.AddIcon(icon05x)
        icon1xi = wx.Icon()
        icon1xi.CopyFromBitmap(icon1x)
        ib.AddIcon(icon1xi)
        ib.AddIcon(icon2x)
        ib.AddIcon(icon4x)
        
        page1 = wx.Panel(self.nb)
        p1s = wx.BoxSizer(wx.VERTICAL)
        page1.SetSizer(p1s)
        
        tpa = wx.Panel(page1)
        tpas = wx.BoxSizer(wx.HORIZONTAL)
        
        tpa.SetSizer(tpas)
        
        pa = wx.Panel(tpa)
        pas = wx.BoxSizer(wx.VERTICAL)
        pa.SetSizer(pas)
        self.textpos = wx.Choice(pa, choices=["Post-1993", "1991-1993", "Pre-1991", "Day 1"])
        tx = wx.StaticText(pa, label="Text Position:")
        pas.Add(tx, 0, wx.ALL, 2)
        pas.Add(self.textpos, 0, wx.ALL, 2)
        tpas.Add(pa, 1, wx.ALL | wx.EXPAND, 2)
        
        pth = ""
        if conf_exist:
            pth = existing_conf.get("musicdir", "")
        
        pa = wx.Panel(tpa)
        pas = wx.BoxSizer(wx.VERTICAL)
        pa.SetSizer(pas)
        pas.Add(wx.StaticText(pa, label="Music Directory"), 0, wx.ALL | wx.EXPAND, 2)
        musicdir = wx.DirPickerCtrl(pa, path=pth)
        pas.Add(musicdir, 0, wx.ALL | wx.EXPAND, 2)
        tpas.Add(pa, 1, wx.ALL | wx.EXPAND, 2)
        
        p1s.Add(tpa, 0, wx.ALL | wx.EXPAND, 2)
        
        
        pa2 = wx.Panel(page1)
        pa2s = wx.BoxSizer(wx.HORIZONTAL)
        pa2.SetSizer(pa2s)
        
        if not conf_exist:
            self.textpos.SetSelection(0)
        else:
            self.textpos.SetSelection(existing_conf.get("textpos", 0))
        self.flags = wx.CheckListBox(pa2, choices=["More Uppercase Text", "Time Draw Delay", "LDL Draw Delay", "Show Pressure Trend", "Unlimited Ceiling Colon", "Extra CC Space", "Old Titles", "Alert Crawl Palette Bug"])
        
        pa2s.Add(self.flags, 1, wx.ALL | wx.EXPAND)
        
        if conf_exist:
            set_flags = []
            if existing_conf.get("veryuppercase", False):
                set_flags.append(0)
            if existing_conf.get("timedrawing", False):
                set_flags.append(1)
            if existing_conf.get("ldldrawing", False):
                set_flags.append(2)
            if existing_conf.get("pressuretrend", False):
                set_flags.append(3)
            flg = existing_conf.get("old", [])
            if "ceiling_colon" in flg:
                set_flags.append(4)
            if "ccspace" in flg:
                set_flags.append(5)
            if "oldtitles" in flg:
                set_flags.append(6)
            if "warnpalbug" in flg:
                set_flags.append(7)
            self.flags.SetCheckedItems(set_flags)
        
        top = wx.Panel(panel)
        info_bitmap = wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE, wx.ART_MENU, wx.Size(32, 32))
        info2_bitmap = wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE_AS, wx.ART_MENU, wx.Size(32, 32))
        menu1 = wx.BitmapButton(top, bitmap=info_bitmap, pos=(5, 5))
        menu1b = wx.BitmapButton(top, bitmap=info2_bitmap, pos=(menu1.GetClientSize()[0] + 10, 5))
        menu2 = wx.BitmapButton(top, bitmap=icon1x, pos=(menu1.GetClientSize()[0]*2 + 15, 5))
        menu1.SetToolTip(wx.ToolTip("Save Configuration"))
        menu1b.SetToolTip(wx.ToolTip("Save Configuration As..."))
        menu2.SetToolTip(wx.ToolTip("Start Simulator"))
        
        page2 = wx.Panel(self.nb)
        pg2s = wx.BoxSizer(wx.VERTICAL)
        page2.SetSizer(pg2s)
        
        oo = 150
        mx = wx.StaticText(page2, label="Main Location:", pos=(oo+20, 20))
        pg2s.Add(mx, 0, wx.ALL, 2)
        mainloc = wx.TextCtrl(page2, pos=(oo+20,  40))
        pg2s.Add(mainloc, 0, wx.ALL | wx.EXPAND, 2)
        pg2s.Add(wx.StaticText(page2, label="Display Name:"), 0, wx.ALL, 2)
        mainloc2 = wx.TextCtrl(page2)
        pg2s.Add(mainloc2, 0, wx.ALL | wx.EXPAND, 2)

        pa = wx.Panel(page2)
        pas = wx.BoxSizer(wx.HORIZONTAL)
        pa.SetSizer(pas)

        paa = wx.Panel(pa)
        paas = wx.BoxSizer(wx.VERTICAL)
        paa.SetSizer(paas)
        paas.Add(wx.StaticText(paa, label="Mesonet Product ID (e.g. CLIJFK):"), 0, wx.ALL, 2)
        mesoid = wx.TextCtrl(paa)
        paas.Add(mesoid, 0, wx.ALL | wx.EXPAND, 2)
        pas.Add(paa, 1, wx.ALL | wx.EXPAND, 2)

        paa = wx.Panel(pa)
        paas = wx.BoxSizer(wx.VERTICAL)
        paa.SetSizer(paas)
        paas.Add(wx.StaticText(paa, label="Extended Forecast Region Name:"), 0, wx.ALL, 2)
        efname = wx.TextCtrl(paa)
        paas.Add(efname, 0, wx.ALL | wx.EXPAND, 2)
        pas.Add(paa, 1, wx.ALL | wx.EXPAND, 2)

        pg2s.Add(pa, 0, wx.ALL | wx.EXPAND, 2)
        
        ###
        pa = wx.Panel(page2)
        pas = wx.BoxSizer(wx.HORIZONTAL)
        pa.SetSizer(pas)

        paa = wx.Panel(pa)
        paas = wx.BoxSizer(wx.VERTICAL)
        paa.SetSizer(paas)
        paas.Add(wx.StaticText(paa, label="Main Logo:"), 0, wx.ALL, 2)
        mainlogo = wx.FilePickerCtrl(paa)
        paas.Add(mainlogo, 0, wx.ALL | wx.EXPAND, 2)
        pas.Add(paa, 1, wx.ALL | wx.EXPAND, 2)

        paa = wx.Panel(pa)
        paas = wx.BoxSizer(wx.VERTICAL)
        paa.SetSizer(paas)
        paas.Add(wx.StaticText(paa, label="Radar Logo:"), 0, wx.ALL, 2)
        radarlogo = wx.FilePickerCtrl(paa)
        paas.Add(radarlogo, 0, wx.ALL | wx.EXPAND, 2)
        pas.Add(paa, 1, wx.ALL | wx.EXPAND, 2)

        pg2s.Add(pa, 0, wx.ALL | wx.EXPAND, 2)
        ###
        
        pa = wx.Panel(pa2)
        bs = wx.BoxSizer(wx.VERTICAL)
        pa.SetSizer(bs)
        #pa.setSizer(pa)
        sldl = wx.CheckBox(pa, label="Start in LDL Mode")
        sldl.SetToolTip(wx.ToolTip("Determines whether or not the simulator will launch into LDL mode or a local forecast. Enable if \"Repeat LF Forever\" is set."))
        frvr = wx.CheckBox(pa, label="Repeat LF Forever")
        frvr.SetToolTip(wx.ToolTip("Enabling will cause local forecast slides to loop forever. Do not use if you have a schedule set up."))
        frvr2 = wx.CheckBox(pa, label="Repeat LDL Forever")
        frvr2.SetToolTip(wx.ToolTip("In LDL-only mode, setting this option will repeat the LDL loop forever. Otherwise, it will have to be cued by an external program."))
        aspect = wx.CheckBox(pa, label="8:5 Feed Size Adjust")
        aspect.SetToolTip(wx.ToolTip("When enabled, video input will be stretched slightly. Enable if you are outputting in 4:3, otherwise disable. Has no effect if using \"Stretch to Fill\" feed sizing."))
        nat = wx.CheckBox(pa, label="Local Forecast LDL Product")
        nat.SetToolTip(wx.ToolTip("If enabled, the LDL will show the little-known Local Forecast over National product."))
        socket = wx.CheckBox(pa, label="Socket Communication")
        socket.SetToolTip(wx.ToolTip("Allows other programs to communicate with FreeStar to do things such as cue Local Forecasts. Enabling this is the only way to cue the feed LDL if Repeat LDL Forever is disabled."))

        paa = wx.Panel(pa)
        paas = wx.BoxSizer(wx.HORIZONTAL)
        paa.SetSizer(paas)
        radarinttx = wx.StaticText(paa, label="Radar Frame Interval:")
        radarint = wx.SpinCtrlDouble(paa)
        paas.Add(radarinttx, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        paas.Add(radarint, 0, wx.ALL, 2)

        paa2 = wx.Panel(pa)
        paas = wx.BoxSizer(wx.HORIZONTAL)
        paa2.SetSizer(paas)
        radarholdtx = wx.StaticText(paa2, label="Radar Final Frame Time:")
        radarhold = wx.SpinCtrlDouble(paa2)
        paas.Add(radarholdtx, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        paas.Add(radarhold, 0, wx.ALL, 2)
        
        bs.Add(sldl, 0, wx.ALL | wx.EXPAND, 2)
        bs.Add(frvr, 0, wx.ALL | wx.EXPAND, 2)
        bs.Add(frvr2, 0, wx.ALL | wx.EXPAND, 2)
        bs.Add(aspect, 0, wx.ALL | wx.EXPAND, 2)
        bs.Add(nat, 0, wx.ALL | wx.EXPAND, 2)
        bs.Add(socket, 0, wx.ALL | wx.EXPAND, 2)
        bs.AddStretchSpacer()
        bs.Add(paa, 0, wx.ALL | wx.EXPAND, 2)
        bs.Add(paa2, 0, wx.ALL | wx.EXPAND, 2)
        
        pa2s.Add(pa, 1, wx.ALL | wx.EXPAND, 2)
        p1s.Add(pa2, 1, wx.ALL | wx.EXPAND, 2)

        p2 = wx.Panel(page1)
        p2s = wx.BoxSizer(wx.HORIZONTAL)
        p2.SetSizer(p2s)
        
        pa = wx.Panel(p2)
        pas = wx.BoxSizer(wx.VERTICAL)
        pa.SetSizer(pas)
        pas.Add(wx.StaticText(pa, label="Extra LDL Message (blank to remove):"), 0, wx.ALL | wx.ALIGN_LEFT, 2)
        extra = wx.TextCtrl(pa)
        pas.Add(extra, 1, wx.ALL | wx.EXPAND, 2)
        p2s.Add(pa, 1, wx.ALL | wx.EXPAND, 2)

        pa = wx.Panel(p2)
        pas = wx.BoxSizer(wx.VERTICAL)
        pa.SetSizer(pas)
        pas.Add(wx.StaticText(pa, label="Schedule Minutes (comma separated):"), 0, wx.ALL | wx.ALIGN_LEFT, 2)
        
        schedmins = wx.TextCtrl(pa)
        
        pas.Add(schedmins, 1, wx.ALL | wx.EXPAND, 2)
        p2s.Add(pa, 1, wx.ALL | wx.EXPAND, 2)
        
        p1s.Add(p2, 0, wx.ALL | wx.EXPAND, 2)
        
        
        radarint.SetIncrement(0.01)
        radarhold.SetIncrement(0.01)
        radarint.SetValue(0.25)
        radarhold.SetValue(2.50)

        if conf_exist:
            mainloc.SetValue(existing_conf.get("mainloc", ""))
            #altloc.SetValue(existing_conf.get("altloc", ""))
            mainloc2.SetValue(existing_conf.get("mainloc2", ""))
            #altloc2.SetValue(existing_conf.get("altloc2", ""))
            mesoid.SetValue(existing_conf.get("mesoid", ""))
            efname.SetValue(existing_conf.get("efname", ""))
            extra.SetValue(existing_conf.get("extra", ""))
            if "schedule" in existing_conf:
                schedmins.SetValue(",".join([str(e) for e in existing_conf["schedule"]]))
            sldl.SetValue(existing_conf.get("ldlmode", True))
            frvr.SetValue(existing_conf.get("forever", False))
            frvr2.SetValue(existing_conf.get("foreverldl", False))
            aspect.SetValue(existing_conf.get("aspect", True))
            socket.SetValue(existing_conf.get("socket", False))
            
            radarint.SetValue(existing_conf.get("radarint", 0.25))
            radarhold.SetValue(existing_conf.get("radarhold", 2.50))
            nat.SetValue(existing_conf.get("ldllf", False))
            mainlogo.SetPath(existing_conf.get("mainlogo", "logos/mwslogo.png"))
            radarlogo.SetPath(existing_conf.get("radarlogo", "logos/mwsradar.png"))
        
        obslocs = []
        if conf_exist:
            obslocs = existing_conf.get("obsloc", [])
        obsloc = []
        obsname = []
        page3 = wx.Panel(self.nb)
        p3sizer = wx.BoxSizer(wx.VERTICAL)
        page3.SetSizer(p3sizer)
        pa = wx.Panel(page3)
        pas = wx.BoxSizer(wx.HORIZONTAL)
        pa.SetSizer(pas)
        loclab = wx.StaticText(pa, label="Location Search Name")
        namelab = wx.StaticText(pa, label="Display Name (≤14 characters suggested)")
        pas.Add(loclab, 1, wx.ALL | wx.EXPAND, 2)
        pas.Add(namelab, 1, wx.ALL | wx.EXPAND, 2)
        p3sizer.Add(pa, 0, wx.ALL | wx.EXPAND, 2)
        for i in range(7):
            pa = wx.Panel(page3)
            pas = wx.BoxSizer(wx.HORIZONTAL)
            pa.SetSizer(pas)
            locent = wx.TextCtrl(pa, pos=(20, 20+25*i))
            nameent = wx.TextCtrl(pa, pos=(20, 20+25*i))
            
            if i < len(obslocs):
                locent.SetValue(obslocs[i][0])
                nameent.SetValue(obslocs[i][1])

            locent.SetMinSize(wx.Size(-1, 15))
            nameent.SetMinSize(wx.Size(-1, 15))
            
            obsloc.append(locent)
            obsname.append(nameent)
            pas.Add(locent, 1, wx.ALL | wx.EXPAND, 2)
            pas.Add(nameent, 1, wx.ALL | wx.EXPAND, 2)
            p3sizer.Add(pa, 1, wx.ALL | wx.EXPAND, 2)

        #page4 = wx.Panel(self.nb)
        
        
        page5 = wx.Panel(self.nb)
        sizer2 = wx.GridSizer(2, 0, 0)
        
        flavorcont = wx.Panel(page5)
        sizer3 = wx.BoxSizer(wx.VERTICAL)
        flavorcont.SetSizer(sizer2)
        #flavorl: list of slides added
        pagemap2 = {
            "cc": "Current Conditions",
            "oldcc": "Old Current Conditions",
            "lo": "Latest Observations",
            "lf": "36-Hour Forecast",
            "xf": "Extended Forecast",
            "lr": "Local Radar",
            "al": "Almanac",
            "ol": "Outlook"
        }
        items = ["Current Conditions - 10.0 secs.", "Latest Observations - 10.0 secs.", "36-Hour Forecast - 10.0 secs.", "Local Radar - 10.0 secs."]
        if conf_exist and "flavor" in existing_conf:
            items = []
            
            if "flavor_times" not in existing_conf:
                existing_conf["flavor_times"] = []
                for i in range(len(existing_conf["flavor"])):
                    existing_conf["flavor_times"].append(10.0)
            for i, f in enumerate(existing_conf["flavor"]):
                items.append(f'{pagemap2[f.split("_")[-1]]} - {existing_conf["flavor_times"][i]} secs.')
        self.flavorl = wx.RearrangeList(flavorcont, order=list(range(len(items))), items=items)
        if conf_exist and "flavor" in existing_conf:
            ci = []
            for i, f in enumerate(existing_conf["flavor"]):
                if not f.startswith("disabled"):
                    ci.append(i)
            self.flavorl.SetCheckedItems(ci)
        btnpanel = wx.Panel(page5)
        page5.SetSizer(sizer3)
        btnsizer = wx.BoxSizer(wx.HORIZONTAL)
        up_btn = wx.Button(btnpanel, label="Up")
        down_btn = wx.Button(btnpanel, label="Down")
        add_btn = wx.Button(btnpanel, label="Add")
        del_btn = wx.Button(btnpanel, label="Delete")
        rep_btn = wx.Button(btnpanel, label="Replace")
        
        def saveFlavor(event):
            dialog = wx.FileDialog(panel, "Save to file:", "./flavors", "flavor.txt", "Text (*.txt)|*.txt", wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
            if (dialog.ShowModal() == wx.ID_OK):
                filename = dialog.GetFilename()
                dirname = dialog.GetDirectory()
                f = open(os.path.join(dirname, filename), 'w')
                lines = [str(radarint.GetValue()), str(radarhold.GetValue())]
                lines.extend(self.flavorl.GetStrings())
                for i in range(len(self.flavorl.GetStrings())):
                    lines.append("1" if self.flavorl.IsChecked(i) else "0")
                f.write("\n".join(lines))
                f.close()
            dialog.Destroy()
        
        def loadFlavor(event):
            # try:
            dialog = wx.FileDialog(panel, "Load flavor:", "./flavors", "flavor.txt", "Text (*.txt)|*.txt", wx.FD_OPEN)
            if (dialog.ShowModal() == wx.ID_OK):
                filename = dialog.GetFilename()
                dirname = dialog.GetDirectory()
                f = open(os.path.join(dirname, filename), 'r')
                fc2 = f.read().split("\n")
                fc = []
                for l in fc2:
                    if l.strip() != "":
                        fc.append(l)
                radarint.SetValue(float(fc.pop(0)))
                radarhold.SetValue(float(fc.pop(0)))
                
                fl1 = []
                fl2 = []
                i = 0
                for l in fc:
                    if l in ["1", "0"]:
                        if bool(int(l)):
                            fl2.append(i)
                        i += 1
                    else:
                        fl1.append(l)
                
                self.flavorl.Set(fl1)
                self.flavorl.SetCheckedItems(fl2)
                f.close()
            dialog.Destroy()
            # except:
            #     pass
        
        save_btn = wx.Button(btnpanel, label="Save")
        load_btn = wx.Button(btnpanel, label="Load")
        
        save_btn.Bind(wx.EVT_BUTTON, saveFlavor)
        load_btn.Bind(wx.EVT_BUTTON, loadFlavor)
        
        btnsizer.Add(up_btn, 0, wx.ALL, 5)
        btnsizer.Add(down_btn, 0, wx.ALL, 5)
        btnsizer.Add(add_btn, 0, wx.ALL, 5)
        btnsizer.Add(del_btn, 0, wx.ALL, 5)
        btnsizer.Add(rep_btn, 0, wx.ALL, 5)
        
        btnsizer.Add(save_btn, 0, wx.ALL, 5)
        btnsizer.Add(load_btn, 0, wx.ALL, 5)
        
        btnpanel.SetSizer(btnsizer)
        sizer3.Add(flavorcont, 1, wx.EXPAND | wx.ALL, 5)
        sizer3.Add(btnpanel, 0, wx.ALIGN_CENTER)
        self.flavori = wx.Choicebook(flavorcont) #flavori: list of slides that can be added
        
        def moveUp(event):
            self.flavorl.MoveCurrentUp()
        def moveDown(event):
            self.flavorl.MoveCurrentDown()
        def addSlide(event):
            idx = self.flavori.GetSelection()
            if idx != wx.NOT_FOUND:
                slide_name = self.flavori.GetPageText(idx)
                self.flavorl.Append(f"{slide_name} - {spincts[slide_name].GetValue()} secs.")
                self.flavorl.Check(len(self.flavorl.GetItems())-1)
        def delSlide(event):
            idx = self.flavorl.GetSelection()
            if idx != wx.NOT_FOUND:
                self.flavorl.Delete(idx)
        def repSlide(event):
            idx = self.flavorl.GetSelection()
            if idx != wx.NOT_FOUND:
                idx2 = self.flavori.GetSelection()
                if idx2 != wx.NOT_FOUND:
                    chi = self.flavorl.GetCheckedItems()
                    slide_name = self.flavori.GetPageText(idx2)
                    items = self.flavorl.GetItems()
                    items[idx] = (f"{slide_name} - {spincts[slide_name].GetValue()} secs.")
                    self.flavorl.SetItems(items)
                    self.flavorl.SetSelection(idx)
                    self.flavorl.SetCheckedItems(chi)
        btnpanel.Bind(wx.EVT_BUTTON, moveUp, up_btn)
        btnpanel.Bind(wx.EVT_BUTTON, moveDown, down_btn)
        btnpanel.Bind(wx.EVT_BUTTON, addSlide, add_btn)
        btnpanel.Bind(wx.EVT_BUTTON, delSlide, del_btn)
        btnpanel.Bind(wx.EVT_BUTTON, repSlide, rep_btn)

        spincts = {}

        def addPageSelector(name, sid, desc="", length=0):
            newpage = wx.Panel(self.flavori)
            sizer = wx.BoxSizer(wx.VERTICAL)
            newpage.SetSizer(sizer)
            st = wx.StaticText(newpage, label=desc)
            sizer.Add(st, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 2)
            #print(os.listdir("launcher"))
            if (sid+".png") in os.listdir("launcher"):
                bmp = wx.Bitmap(os.path.join("launcher", sid + ".png"), wx.BITMAP_TYPE_PNG).ConvertToImage()
                bmp.Rescale(256, 192, wx.IMAGE_QUALITY_BICUBIC)
                img = wx.StaticBitmap(newpage, bitmap=bmp.ConvertToBitmap(), size=(256, 192))
                sizer.Add(img, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 2)
            pan = wx.Panel(newpage)
            ps = wx.BoxSizer(wx.HORIZONTAL)
            pan.SetSizer(ps)
            txx = wx.StaticText(pan, label="Slide Time:")
            tm = wx.SpinCtrlDouble(pan)
            tm.SetIncrement(0.1)
            tm.SetMax(60)
            tm.SetValue(10)
            spincts[name] = tm
            ps.Add(txx, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
            ps.Add(tm, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
            sizer.Add(pan, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 2)

            self.flavori.AddPage(newpage, name)

        def resettime(event):
            for tm in spincts.values():
                tm.SetValue(10)

        self.flavori.Bind(wx.EVT_CHOICEBOOK_PAGE_CHANGED, resettime)
        
        #Hey! Stop snooping! You'll get more slides when we get there!
        
        addPageSelector("Current Conditions", "cc", "Shows the current weather conditions.")
        addPageSelector("Old Current Conditions", "oldcc", "Text-based CC page from before April 17, 1991.")
        addPageSelector("Latest Observations", "lo", "Displays conditions from multiple nearby stations.")
        addPageSelector("36-Hour Forecast", "lf", "Displays three 12-hour forecasts.\nSlide length applies per page.")
        addPageSelector("Extended Forecast", "xf", "Shows conditions for three upcoming days..")
        addPageSelector("Almanac", "al", "Shows moon, sun, and temperature information.")
        addPageSelector("Outlook", "ol", "Predicts trends for the next 30 days.")
        addPageSelector("Local Radar", "lr", "Shows an animated radar view.")

        page6 = wx.Panel(self.nb)
        p6sizer = wx.BoxSizer(wx.VERTICAL)
        
        crawls = []
        crawlentry = []
        crawlenable = []
        if conf_exist:
            crawls = existing_conf.get("crawls", [])
        for i in range(10):
            pa = wx.Panel(page6)
            pas = wx.BoxSizer(wx.HORIZONTAL)
            pa.SetSizer(pas)
            chk = wx.CheckBox(pa)
            chk.SetValue(True)
            crawlent = wx.TextCtrl(pa, pos=(20, 20+25*i))
            if i < len(crawls):
                crawlent.SetValue(crawls[i][0])
                chk.SetValue(crawls[i][1])
            pa.SetMinSize(wx.Size(-1, 10))
            crawlent.SetMinSize(wx.Size(-1, 10))
            crawlentry.append(crawlent)
            crawlenable.append(chk)
            pas.Add(chk, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
            pas.Add(crawlent, 1, wx.ALL | wx.EXPAND, 2)
            p6sizer.Add(pa, 1, wx.ALL | wx.EXPAND, 2)
        pa = wx.Panel(page6)
        pas = wx.BoxSizer(wx.HORIZONTAL)
        pa.SetSizer(pas)
        ci1 = wx.StaticText(pa, label="Crawl Interval:")
        crawlint = wx.Choice(pa, choices=["15 mins", "30 mins", "1 hour", "2 hours", "3 hours", "4 hours", "6 hours", "8 hours", "12 hours", "24 hours"], )
        if not conf_exist:
            crawlint.SetSelection(0)
        else:
            crawlint.SetSelection(existing_conf.get("crawlint", 0))
        pas.Add(ci1, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        pas.Add(crawlint, 0, wx.ALL, 2)
        pas.AddStretchSpacer(1)
        ci2 = wx.StaticText(pa, label="Background Path:")
        pas.Add(ci2, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        bgg = wx.FilePickerCtrl(pa)
        pas.Add(bgg, 0, wx.ALL, 2)
        p6sizer.Add(pa, 0, wx.ALL | wx.EXPAND, 2)
        page6.SetSizer(p6sizer)
        
        page7 = wx.Panel(self.nb)
        p7sizer = wx.BoxSizer(wx.VERTICAL)
        p7sizer.Add(wx.StaticText(page7, label="Output URIs (prefix with # to disable)"), 0, wx.ALL | wx.EXPAND, 5)
        outs = wx.adv.EditableListBox(page7, style=wx.adv.EL_NO_REORDER|wx.adv.EL_DEFAULT_STYLE)
        p7sizer.Add(outs, 1, wx.ALL | wx.EXPAND)
        pa = wx.Panel(page7)
        pas = wx.BoxSizer(wx.HORIZONTAL)
        pa.SetSizer(pas)
        p7sizer.Add(wx.StaticText(page7, label="Input URI (for static images, check the LDL tab)"), 0, wx.ALL | wx.EXPAND, 5)
        ins = wx.TextCtrl(pa)
        pas.Add(ins, 1, wx.ALL | wx.EXPAND, 5)
        smode = wx.Choice(pa, choices=["Stretch to Fill", "Fixed Width", "Fixed Height"])
        smode.SetSelection(0)
        pas.Add(smode, 0, wx.ALL | wx.EXPAND, 5)
        p7sizer.Add(pa, 0, wx.ALL | wx.EXPAND, 0)
        page7.SetSizer(p7sizer)
        if conf_exist:
            outs.SetStrings(existing_conf.get("outputs", []))
            ins.SetValue(str(existing_conf.get("ldlfeed", "")))
            bgg.SetPath(existing_conf.get("ldlbg", ""))
            smode.SetSelection(existing_conf.get("smode", 0))
        
        #fun fact for anybody reading: this page was added on november 24th
        page8 = wx.Panel(self.nb)
        p8sizer = wx.BoxSizer(wx.VERTICAL)
        page8.SetSizer(p8sizer)
        
        pa = wx.Panel(page8)
        pas = wx.BoxSizer(wx.HORIZONTAL)
        pa.SetSizer(pas)
        pas.Add(wx.StaticText(pa, label="Audio Output Device:"), 0, wx.ALL, 2)
        pas.AddStretchSpacer()
        pas.Add(wx.StaticText(pa, label="Video Encoder:"), 0, wx.ALL, 2)
        p8sizer.Add(pa, 0, wx.ALL | wx.EXPAND, 2)
        
        pa = wx.Panel(page8)
        pas = wx.BoxSizer(wx.HORIZONTAL)
        pa.SetSizer(pas)
        audiodevsel = wx.Choice(pa, choices=devices)
        pas.Add(audiodevsel, 0, wx.ALL, 2)
        pas.AddStretchSpacer()
        vencoder = wx.TextCtrl(pa)
        pas.Add(vencoder, 0, wx.ALL, 2)
        p8sizer.Add(pa, 0, wx.ALL | wx.EXPAND, 2)
        
        extensionsel = wx.CheckListBox(page8, choices=extensions_possible)
        
        pa = wx.Panel(page8)
        pas = wx.BoxSizer(wx.HORIZONTAL)
        pa.SetSizer(pas)
        metric = wx.CheckBox(pa, label="Metric Units")
        borderless = wx.CheckBox(pa, label="Borderless Window")
        widescreen = wx.CheckBox(pa, label="Widescreen")
        noaudio = wx.CheckBox(pa, label="Mute Audio")
        pas.Add(metric, 0, wx.ALL, 2)
        pas.AddStretchSpacer()
        pas.Add(borderless, 0, wx.ALL, 2)
        pas.AddStretchSpacer()
        pas.Add(widescreen, 0, wx.ALL, 2)
        pas.AddStretchSpacer()
        pas.Add(noaudio, 0, wx.ALL, 2)
        p8sizer.Add(pa, 0, wx.ALL | wx.EXPAND, 2)
        
        p8sizer.Add(extensionsel, 1, wx.ALL | wx.EXPAND, 4)
        
        if conf_exist:
            extensionsel.SetCheckedStrings(selected_extension_names)
            audiodevsel.SetStringSelection(existing_conf.get("audiodevice", "Default"))
            metric.SetValue(existing_conf.get("metric", False))
            borderless.SetValue(existing_conf.get("borderless", False))
            vencoder.SetValue(existing_conf.get("vencoder", "libx264"))
            widescreen.SetValue(existing_conf.get("widescreen", False))
            noaudio.SetValue(existing_conf.get("mute", False))
        
        def getconfig():
            items = []
            items.append(("textpos", self.textpos.GetSelection()))
            flg = self.flags.GetCheckedItems()
            items.append(("timedrawing", 1 in flg))
            items.append(("ldldrawing", 2 in flg))
            items.append(("veryuppercase", 0 in flg))
            items.append(("pressuretrend", 3 in flg))
            
            misc = set()
            if 4 in flg: misc.add("ceiling_colon")
            if 5 in flg: misc.add("ccspace")
            if 6 in flg: misc.add("oldtitles")
            if 6 in flg: misc.add("warnpalbug")

            items.append(("mainloc", str(mainloc.GetValue())))
            items.append(("mainloc2", str(mainloc2.GetValue())))
            items.append(("musicdir", musicdir.GetPath()))
            items.append(("mesoid", mesoid.GetValue()))
            items.append(("extra", extra.GetValue()))
            items.append(("crawlint", crawlint.GetSelection()))
            items.append(("ldlbg", bgg.GetPath()))
            items.append(("old", misc))
            #items.append(("altloc", str(altloc.GetValue())))
            #items.append(("altloc2", str(altloc2.GetValue())))

            items.append(("crawls", [(crawlentry[i].GetValue(), crawlenable[i].GetValue()) for i in range(10)]))
            items.append(("obsloc", [[obsloc[i].GetValue(), obsname[i].GetValue()] for i in range(7)]))
            items.append(("outputs", outs.GetStrings()))
            if schedmins.GetValue().strip():
                items.append(("schedule", [int(e.strip()) for e in schedmins.GetValue().split(",")]))
            else:
                items.append(("schedule", ""))
            items.append(("ldlmode", sldl.GetValue()))
            items.append(("forever", frvr.GetValue()))
            items.append(("foreverldl", frvr2.GetValue()))
            items.append(("aspect", aspect.GetValue()))
            items.append(("socket", socket.GetValue()))
            items.append(("smode", smode.GetSelection()))
            items.append(("radarint", radarint.GetValue()))
            items.append(("radarhold", radarhold.GetValue()))
            items.append(("ldllf", nat.GetValue()))
            items.append(("efname", efname.GetValue()))
            items.append(("mainlogo", mainlogo.GetPath()))
            items.append(("radarlogo", radarlogo.GetPath()))
            items.append(("extensions", extensionsel.GetCheckedStrings()))
            items.append(("audiodevice", audiodevsel.GetStringSelection()))
            items.append(("metric", metric.GetValue()))
            items.append(("borderless", borderless.GetValue()))
            items.append(("vencoder", vencoder.GetValue()))
            items.append(("widescreen", widescreen.GetValue()))
            items.append(("mute", noaudio.GetValue()))
            iv = ins.GetValue()
            try:
                iv = int(iv)
            except:
                pass
            items.append(("ldlfeed", iv))
            
            pagemap = {
                "Current Conditions": "cc",
                "Old Current Conditions": "oldcc",
                "Latest Observations": "lo",
                "36-Hour Forecast": "lf",
                "Extended Forecast": "xf",
                "Local Radar": "lr",
                "Almanac": "al",
                "Outlook": "ol"
            }
            pages = []
            times = []
            e2 = self.flavorl.GetCheckedItems()
            for i, page in enumerate(self.flavorl.GetItems()):
                pg = page.split(" - ")
                fname = pg[0]
                pgt = float(pg[1].split(" ")[0])
                pages.append(("" if i in e2 else "disabled_") + pagemap[fname])
                times.append(pgt)
            
            items.append(("flavor", pages))
            items.append(("flavor_times", times))
            
            final = ""
            for item in items:
                if isinstance(item[1], str):
                    im = item[1].replace('\\', '\\\\')
                    final += f"{item[0]}=\"{im}\"\n"
                else:
                    final += f"{item[0]}={item[1]}\n"
            
            return final
        
        def save(event):
            with open("conf.py", "w") as f:
                f.write(getconfig())
        
        def save_as(event):
            dialog = wx.FileDialog(panel, "Save to file:", "./configs", "config.txt", "Text (*.txt)|*.txt", wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
            if (dialog.ShowModal() == wx.ID_OK):
                filename = dialog.GetFilename()
                dirname = dialog.GetDirectory()
                f = open(os.path.join(dirname, filename), 'w')
                f.write(getconfig())
                f.close()
            dialog.Destroy()
        
        def launch(event):
            global sub
            if sub is not None:
                if sub.poll() is not None:
                    sub = sp.Popen([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")])
            else:
                sub = sp.Popen([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")])
        panel.Bind(wx.EVT_BUTTON, save, menu1)
        panel.Bind(wx.EVT_BUTTON, save_as, menu1b)
        panel.Bind(wx.EVT_BUTTON, launch, menu2)
        
        sizer2.Add(self.flavorl, 0, wx.EXPAND, 0)
        sizer2.Add(self.flavori, 0, wx.EXPAND, 0)
        flavorcont.SetSizer(sizer2)
        
        about = wx.Panel(self.nb)
        aboutsizer = wx.BoxSizer(wx.VERTICAL)
        abouttext = wx.StaticText(about, label="FreeStar 4k Launcher\nVersion 1.0", style=wx.ALIGN_CENTER)
        logo = wx.StaticBitmap(about, bitmap=wx.Bitmap("launcher/icon_128x128.png", wx.BITMAP_TYPE_PNG))
        abouttext2 = wx.StaticText(about, label="Developed by 9D Crew\nA special thanks to COLSTER for helping with gathering STAR fonts!\nThanks to Malek Masoud for creating the Extended Forecast background!\nIf you are Bill Goodwill, creator of the WS4000 Simulator, please do not use FreeStar simulators.\nThanks to This program is licensed under the GNU General Public License v3.0 or later.\nFor questions, visit https://freestar.lewolfyt.cc/", style=wx.ALIGN_CENTER)
        aboutsizer.Add(abouttext, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        aboutsizer.Add(logo, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        aboutsizer.Add(abouttext2, 1, wx.ALL | wx.ALIGN_CENTER, 10)
        about.SetSizer(aboutsizer)
        
        self.nb.AddPage(page1, "Presentation") #graphics settings
        self.nb.AddPage(page2, "Main Locations") #main+alternate locations
        self.nb.AddPage(page3, "Local Locations") #local/close locations
        #self.nb.AddPage(page4, "Audio") #music/sound settings
        self.nb.AddPage(page5, "Flavor") #which slides to show and in what order
        self.nb.AddPage(page6, "LDL") #ldl timing and text
        self.nb.AddPage(page7, "Stream I/O") #main+alternate locations
        self.nb.AddPage(page8, "Misc")
        self.nb.AddPage(about, "About") #about page
        
        sizer.Add(top, 0, wx.EXPAND, 0)
        sizer.Add(self.nb, 1, wx.ALL | wx.EXPAND, 5)
        
        panel.SetSizer(sizer)
        
        self.Show()
        self.SetIcons(ib)
        tbi = wx.adv.TaskBarIcon(wx.adv.TBI_DOCK)
        tbi.SetIcon(icon2x)

if __name__ == '__main__':
    app = wx.App()
    frame = Launcher()
    frame.Show(True)
    app.SetTopWindow(frame)
    app.MainLoop()
