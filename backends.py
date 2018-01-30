import os, os.path
from queue import Queue
from threading import Thread

import rss
import yt
from utils import *
from database import DataBase

def getData(url, printInfos=print, new=False):
    if 'youtube' in url:
        data = yt.getData(url, printInfos, new)
    else:
        data = rss.getData(url, printInfos)
    return data

class DownloadManager():
    def __init__(self, itemList, printInfos=print):
        self.nthreads = 2
        self.itemList = itemList
        self.printInfos = printInfos
        self.queue = Queue()

        # Set up some threads to fetch the items to download
        for i in range(self.nthreads):
            worker = Thread(target=self.handleQueue, args=(self.queue,))
            worker.setDaemon(True)
            worker.start()

        for video in self.itemList.videos:
            if 'downloading' == video['status']:
                channel = self.itemList.db.getChannel(video['url'])
                self.add(video, channel, update=False)

    def handleQueue(self, q):
        """This is the worker thread function. It processes items in the queue one
        after another.  These daemon threads go into an infinite loop, and only
        exit when the main thread ends."""
        while True:
            video, channel = q.get()
            self.download(video, channel)
            q.task_done()

    def add(self, video, channel, update=True):
        if update:
            self.printInfos('Add to download: %s' % video['title'])
            video['status'] = 'downloading'
            self.itemList.db.updateVideo(video)
            self.itemList.updateVideoAreas()
        self.queue.put((video, channel))

    def download(self, video, channel):
        link = video['link']

        # Set filename # TODO handle collision add into db even before downloading
        path = strToFilename(channel['title'])
        if not os.path.exists(path):
            os.makedirs(path)

        # Download file
        if 'rss' == channel['type']:
            ext = link.split('.')[-1]
            filename = "%s/%s_%s.%s" % (path, tsToDate(video['date']),
                    strToFilename(video['title']), ext)
            rss.download(link, filename, self.printInfos)

        elif 'youtube' == channel['type']:
            filename = "%s/%s_%s.%s" % (path, tsToDate(video['date']),
                    strToFilename(video['title']), 'mp4')
            yt.download(link, filename, self.printInfos)

        # Change status and filename
        video['filename'] = filename
        video['status'] = 'downloaded'
        db = DataBase(self.itemList.dbName, self.printInfos)
        db.updateVideo(video)
        self.itemList.updateVideoAreas()
