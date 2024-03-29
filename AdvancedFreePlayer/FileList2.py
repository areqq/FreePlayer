from __init__ import *
from re import compile as re_compile
from os import path as os_path, listdir
from Components.config import config
from Components.MenuList import MenuList
from Components.Harddisk import harddiskmanager

from Tools.Directories import SCOPE_CURRENT_SKIN, resolveFilename, fileExists

from enigma import RT_HALIGN_LEFT, eListboxPythonMultiContent, \
    eServiceReference, eServiceCenter, gFont
from Tools.LoadPixmap import LoadPixmap

EXTENSIONS = {
        "m4a": "music",
        "mp2": "music",
        "mp3": "music",
        "wav": "music",
        "ogg": "music",
        "flac": "music",
        "jpg": "picture",
        "jpeg": "picture",
        "png": "picture",
        "bmp": "picture",
        "ts": "movie",
        "avi": "movie",
        "divx": "movie",
        "m4v": "movie",
        "mpg": "movie",
        "mpeg": "movie",
        "mkv": "movie",
        "mp4": "movie",
        "mov": "movie",
        "txt": "text",
        "srt": "text"
    }

def FileEntryComponent(name, absolute = None, isDir = False):
    res = [ (absolute, isDir) ]
    res.append((eListboxPythonMultiContent.TYPE_TEXT, 45, 1, 1020, 35, 0, RT_HALIGN_LEFT, name))
    if isDir:
        png = LoadPixmap(cached=True, path="%spic/folder.png" % PluginPath)
    else:
        extension = name.split('.')
        extension = extension[-1].lower()
        if EXTENSIONS.has_key(extension):
            if os_path.exists(resolveFilename(SCOPE_CURRENT_SKIN, "extensions/" + EXTENSIONS[extension] + ".png")):
                png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "extensions/" + EXTENSIONS[extension] + ".png"))
            else:
                print "%spic/%s.png" % (PluginPath,EXTENSIONS[extension])
                png = LoadPixmap("%spic/%s.png" % (PluginPath,EXTENSIONS[extension]))
        else:
            png = None
    if png is not None:
        res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 5, 4, 25, 25, png))
    return res

class FileList(MenuList):
    def __init__(self, directory, showDirectories = True, showFiles = True, showMountpoints = True, matchingPattern = None, useServiceRef = False, inhibitDirs = False, inhibitMounts = False, isTop = False, enableWrapAround = False, additionalExtensions = None, sortDate=False):
        MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
        self.additional_extensions = additionalExtensions
        self.mountpoints = []
        self.current_directory = None
        self.current_mountpoint = None
        self.useServiceRef = useServiceRef
        self.showDirectories = showDirectories
        self.showMountpoints = showMountpoints
        self.showFiles = showFiles
        self.isTop = isTop
        # example: matching .nfi and .ts files: "^.*\.(nfi|ts)"
        self.matchingPattern = matchingPattern
        self.inhibitDirs = inhibitDirs or []
        self.inhibitMounts = inhibitMounts or []
        self.sortDate = sortDate

        self.refreshMountpoints()
        self.changeDir(directory)
        self.l.setFont(0, gFont("Regular", int(config.plugins.AdvancedFreePlayer.FileListFontSize.value)))
        self.l.setItemHeight(35)
        self.serviceHandler = eServiceCenter.getInstance()

    def refreshMountpoints(self):
        self.mountpoints = [os_path.join(p.mountpoint, "") for p in harddiskmanager.getMountedPartitions()]
        self.mountpoints.sort(reverse = True)

    def getMountpoint(self, file):
        file = os_path.join(os_path.realpath(file), "")
        for m in self.mountpoints:
            if file.startswith(m):
                return m
        return False

    def getMountpointLink(self, file):
        if os_path.realpath(file) == file:
            return self.getMountpoint(file)
        else:
            if file[-1] == "/":
                file = file[:-1]
            mp = self.getMountpoint(file)
            last = file
            file = os_path.dirname(file)
            while last != "/" and mp == self.getMountpoint(file):
                last = file
                file = os_path.dirname(file)
            return os_path.join(last, "")

    def getSelection(self):
        if self.l.getCurrentSelection() is None:
            return None
        return self.l.getCurrentSelection()[0]

    def getCurrentEvent(self):
        l = self.l.getCurrentSelection()
        if not l or l[0][1] == True:
            return None
        else:
            return self.serviceHandler.info(l[0][0]).getEvent(l[0][0])

    def getFileList(self):
        return self.list

    def inParentDirs(self, dir, parents):
        dir = os_path.realpath(dir)
        for p in parents:
            if dir.startswith(p):
                return True
        return False

    def changeDir(self, directory, select = None):
        self.list = []

        # if we are just entering from the list of mount points:
        if self.current_directory is None:
            if directory and self.showMountpoints:
                self.current_mountpoint = self.getMountpointLink(directory)
            else:
                self.current_mountpoint = None
        self.current_directory = directory
        directories = []
        files = []

        if directory is None and self.showMountpoints: # present available mountpoints
            for p in harddiskmanager.getMountedPartitions():
                path = os_path.join(p.mountpoint, "")
                if path not in self.inhibitMounts and not self.inParentDirs(path, self.inhibitDirs):
                    self.list.append(FileEntryComponent(name = p.description, absolute = path, isDir = True))
            files = [ ]
            directories = [ ]
        elif directory is None:
            files = [ ]
            directories = [ ]
        elif self.useServiceRef:
            root = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + directory)
            if self.additional_extensions:
                root.setName(self.additional_extensions)
            serviceHandler = eServiceCenter.getInstance()
            list = serviceHandler.list(root)

            while 1:
                s = list.getNext()
                if not s.valid():
                    del list
                    break
                if s.flags & s.mustDescent:
                    directories.append(s.getPath())
                else:
                    files.append(s)
            directories.sort()
            files.sort()
        else:
            if fileExists(directory):
                try:
                    files = listdir(directory)
                    
                except:
                    files = []
                if self.sortDate:
                    files.sort(key=lambda s: os_path.getmtime(os_path.join(directory, s)))
                    files.reverse()
                else:
                    files.sort()
                tmpfiles = files[:]
                for x in tmpfiles:
                    if os_path.isdir(directory + x):
                        directories.append(directory + x + "/")
                        files.remove(x)

        if directory is not None and self.showDirectories and not self.isTop:
            if directory == self.current_mountpoint and self.showMountpoints:
                self.list.append(FileEntryComponent(name = "<" +_("List of Storage Devices") + ">", absolute = None, isDir = True))
            elif (directory != "/") and not (self.inhibitMounts and self.getMountpoint(directory) in self.inhibitMounts):
                self.list.append(FileEntryComponent(name = "<" +_("Parent Directory") + ">", absolute = '/'.join(directory.split('/')[:-2]) + '/', isDir = True))

        if self.showDirectories:
            for x in directories:
                if not (self.inhibitMounts and self.getMountpoint(x) in self.inhibitMounts) and not self.inParentDirs(x, self.inhibitDirs):
                    name = x.split('/')[-2]
                    self.list.append(FileEntryComponent(name = name, absolute = x, isDir = True))

        if self.showFiles:
            for x in files:
                if self.useServiceRef:
                    path = x.getPath()
                    name = path.split('/')[-1]
                else:
                    path = directory + x
                    name = x

                if (self.matchingPattern is None) or re_compile(self.matchingPattern).search(path):
                    self.list.append(FileEntryComponent(name = name, absolute = x , isDir = False))

        if self.showMountpoints and len(self.list) == 0:
            self.list.append(FileEntryComponent(name = _("nothing connected"), absolute = None, isDir = False))

        self.l.setList(self.list)

        if select is not None:
            i = 0
            self.moveToIndex(0)
            for x in self.list:
                p = x[0][0]
                
                if isinstance(p, eServiceReference):
                    p = p.getPath()
                
                if p == select:
                    self.moveToIndex(i)
                i += 1

    def sortDateEnable(self):
        #print "sortDateEnable"
        self.sortDate=True

    def sortDateDisable(self):
        #print "sortDateDisable"
        self.sortDate=False

    def getCurrentDirectory(self):
        return self.current_directory

    def canDescent(self):
        if self.getSelection() is None:
            return False
        return self.getSelection()[1]

    def descent(self):
        if self.getSelection() is None:
            return
        self.changeDir(self.getSelection()[0], select = self.current_directory)

    def getFilename(self):
        if self.getSelection() is None:
            return None
        x = self.getSelection()[0]
        if isinstance(x, eServiceReference):
            x = x.getPath()
        return x

    def getServiceRef(self):
        if self.getSelection() is None:
            return None
        x = self.getSelection()[0]
        if isinstance(x, eServiceReference):
            return x
        return None

    def execBegin(self):
        harddiskmanager.on_partition_list_change.append(self.partitionListChanged)

    def execEnd(self):
        harddiskmanager.on_partition_list_change.remove(self.partitionListChanged)

    def refresh(self):
        self.changeDir(self.current_directory, self.getFilename())

    def partitionListChanged(self, action, device):
        self.refreshMountpoints()
        if self.current_directory is None:
            self.refresh()
