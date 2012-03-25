# -*- coding: utf-8 -*-
import sys
import os
import getopt
import locale
import urllib2
from xml.dom import minidom
from tagger import *

class Mp3File:
    "User-friendly wrapper class for pytagger"
    __imageCache = {}
    def __init__(self, filename):
        self.__lastfmApiKey = "ea5915792f192735a6e242c3d4054bf7"
        self.__fileName = filename
        self.__artistName = None
        self.__albumName = None
        self.__albumCoverImage = None        
        self.__id3 = ID3v2(self.__fileName)
        self.__apicfid = "PIC" if self.__id3.version == 2.2 else "APIC"
        if not self.__id3.tag_exists():
            id3Old = ID3v1(self.__fileName)
            self.__artistName = id3Old.artist.decode(currentEncoding).encode('utf8') 
            self.__albumName  = id3Old.album.decode(currentEncoding).encode('utf8')
            self.__albumCoverImage = None
        else:
            for elem in self.__id3.frames:
                if elem.fid == "TPE1":
                    self.__artistName = elem.strings[0].decode(currentEncoding).encode('utf8')
                if elem.fid == "TALB":
                    self.__albumName = elem.strings[0].decode(currentEncoding).encode('utf8')
            apicframe = [frame for frame in self.__id3.frames if frame.fid == self.__apicfid]
            if apicframe:
                self.__albumCoverImage = apicframe[0]

    def hasImage(self):
        return True if self.__albumCoverImage else None
        
    def __getAlbumCoverUrl(self):
        imageUrl = None
        if self.__artistName and self.__albumName:            
            url = "http://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key=%s&artist=%s&album=%s" % (self.__lastfmApiKey, self.__artistName, self.__albumName)    
            url = url.replace(' ', '%20')
            try:       
                sock = urllib2.urlopen(url)
                xmlSource = sock.read()    
                sock.close()
            except:
                pass
            else:
                #print xmlSource                                    # <-- uncomment me to debug
                dom = minidom.parseString(xmlSource)
                imagesList = dom.getElementsByTagName('image')
                imageUrl = max(imagesList).firstChild.nodeValue if imagesList else None
        return imageUrl
        
    def __loadImageFromLastFm(self):
        imageUrl = self.__getAlbumCoverUrl()
        if ".jpeg" in imageUrl or ".jpg" in imageUrl:
            self.__mimetype = "image/jpg"
        else:
            self.__mimetype = "image/png"        
        imageSource = None
        if imageUrl:
            try:                    
                imgSock = urllib2.urlopen(imageUrl)
                imageSource = imgSock.read()    
                imgSock.close()
            except:
                print "%s Can't find album cover!" % f                    
        return imageSource
        
    def __saveChanges(self):
        try:
            self.__id3.frames = [frame for frame in self.__id3.frames if frame.fid != self.__apicfid]
            if self.__albumCoverImage:
                apic = self.__id3.new_frame(self.__apicfid)
                apic.encoding = 'latin_1'
                apic.mimetype = self.__mimetype
                apic.picttype = 0
                apic.desc = ''        
                apic.pict = self.__albumCoverImage                
                self.__id3.frames.append(apic)
                status, resultMessage = (1, "[OK] image has been successfully saved!")
            else:
                status, resultMessage = (1, "[OK] image has been successfully deleted!")
            self.__id3.commit()            
        except:
            status, resultMessage = (0, "[ERR] can't save image to file!")        
        return (status, resultMessage)

    def deleteCoverImage(self):
        if self.hasImage():
            self.__albumCoverImage = None
            status, resultMessage = self.__saveChanges()
        else:
            status, resultMessage = (1, "[OK] mp3 already haven't album cover!")
        return (status, resultMessage)
        
    def setCoverImage(self, overwrite = None):
        if not self.hasImage() or overwrite:
            if self.__artistName and self.__albumName:
                if (self.__artistName, self.__albumName) in self.__imageCache:
                    self.__albumCoverImage, self.__mimetype = self.__imageCache[(self.__artistName, self.__albumName)]
                else:
                    self.__albumCoverImage = self.__loadImageFromLastFm()
                    self.__class__.__imageCache[(self.__artistName, self.__albumName)] = (self.__albumCoverImage, self.__mimetype)
                status, resultMessage = self.__saveChanges()
            else:
                status, resultMessage = (0, "[ERR] Not enough data in id3-tag to load album cover!")
        else:
            status, resultMessage = (1, "[OK] mp3 already contains album cover image! Use --overwrite to update it.")
        return (status, resultMessage)        
        
    #debug: check for attributes
    def printAttr(self):
        print self.__artistName
        print self.__albumName
        if self.__albumCoverImage:
            print "Image exists!"
            


if __name__ == "__main__":    
    print "Imagizer: script adding album cover to your mp3s"
    helpString = """
    USAGE: python imagizer.py [-h] [-s] [-d] [-o] [file1 file2 ... fileN]
     -h\t --help\t this help
     -s\t --set\t set album cover image to mp3
     -d\t --delete\t remove album cover image from mp3
     -o\t --overwrite\t overwrite album cover image if it's already exists
     file1 file2 ... fileN\t files to process. If is absent - process all mp3 from this dir recursively 
    """

    # Recognizing execution mode in command-line arguments
    mode, overwrite = (None, None)    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hdso", ["help", "delete", "set", "overwrite"])
    except getopt.GetoptError as err:
        print(err) # will print something like "option -a not recognized"
        sys.exit(2)
    for o, a in opts:
        if o in ("-h", "--help"):
            mode = "help"
        elif o in ("-d", "--delete"):
            mode = "delete"
            break
        elif o in ("-s", "--set"):
            mode = "set"
        elif o in ("-o", "--overwrite"):
            mode = "set"
            overwrite = 1
    # And if script has no args, we strongly recommended to read help. In fact you have no choice :)
    if not mode or mode == "help":
        print helpString
        sys.exit(1)
        
    
    # Get the list of files to process (from command-line args or from current folder recursively)
    filesToProcess = []
    if args:
        print "...will proceed list of files"
        for fileName in args:
            if os.access(fileName, os.F_OK):
                newItem = fileName
                filesToProcess.append(newItem)
            else:
                print fileName + " couldn't find!"
    else:
        print "...will proceed current directory"
        sourceDir = os.path.realpath(os.path.dirname(sys.argv[0]))
        for root, dirs, files in os.walk(sourceDir):
            for file in files:
                if file.endswith('.mp3'):
                    newItem = os.path.join(root, file)
                    filesToProcess.append(newItem)
    
    # Main part of script - processing every file in your list
    currentEncoding = locale.getlocale()[1] if locale.getlocale()[1] else "1251"
    passed, failed = ([], [])
    for fileName in filesToProcess:
        print fileName + " ",
        mp3 = Mp3File(fileName)
        stat, msg = mp3.deleteCoverImage() if mode == "delete" else mp3.setCoverImage(overwrite)
        if stat:
            passed.append(fileName)
        else:
            failed.append(fileName)
        print msg
    print "\n\nTotal: %d files successfully proceed, %d proceed with error" % (len(passed), len(failed))