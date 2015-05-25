# -*- coding: UTF-8 -*-
import re
import math
import json
from requests import Session
from urlparse import urlparse
from bs4 import BeautifulSoup
from PySide.QtCore import QObject, Signal

class Miner:
    def __init__(self, initialLink, pagingLink):
        # hard-coded & non-conditional
        self.browserType = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:36.0) Gecko/20100101 Firefox/36.0'
        self.acceptLanguage = 'en-US;q=0.5,en;q=0.3'
        self.acceptEncoding = 'gzip, deflate'
        self.accept = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        self.contentType = 'text/plain; charset=UTF-8'
        self.session = Session()
        # user-defined
        self.initialLink = initialLink
        self.pagingLink = pagingLink
        self.host = urlparse(self.initialLink).hostname
        
         # evaluated
        self.bytes = 0
        #self.startHTML, self.kuka = self.placeGetRequest(self.initialLink)
        #print 'Class Miner instance initilized'
        
    def placeGetRequest(self, link):
        headers = {'user-agent': self.browserType,
                   'Connection': 'keep-alive',
                   'Host' : self.host,
                   'Accept-Language' : self.acceptLanguage,
                   'Accept-Encoding' : self.acceptEncoding,
                   'Accept' : self.accept
                  }
        resp = self.session.get(link, headers = headers)
        self.bytes += len(resp.content)
        #print 'First GET completed.', self.bytes, 'Bytes'
        return (resp.text, resp.cookies)

class CountInformer(QObject):
    processedEntriesChanged = Signal(list)
    # list format: list[0] = processed entries
    #              list[1] = total entries
    #              list[2] = percentage (from 0 to 100) for progressBar

class OreTreatment:
    def __init__(self, hitsPerPage):
        self.hitsPerPage = hitsPerPage
        self.totalEntries = 0
        self.processedEntries = 0
        self.countInformer = CountInformer()
        self.quantRatio = 0.1 # for progress bar
        self.quant = 0
        self.nextProgressThreshold = 0
        self.nextPercentage = 0
    
    def totalPagesToIterate(self, soup):
        countt = soup.find('span', class_ = 'resultsDisplay').text.replace(',','')
        self.totalEntries = int(re.search('\d{2,}', countt).group(0))
        self.quant = self.totalEntries*self.quantRatio
        self.nextProgressThreshold += self.quant
        tPages = self.calcIntegerPagesToIterate(self.totalEntries, self.hitsPerPage)
        return tPages
    
    def calcIntegerPagesToIterate(self, totalEntries, hitsPerPage):
        pagesTuple = math.modf(1.0*totalEntries/hitsPerPage)
        if pagesTuple[0] > 0:
            tPages = pagesTuple[1] + 1
        else:
            tPages = pagesTuple[1]
        return int(tPages)

    def getJobBlock(self, soup):
        jobDB = []
        blocks = soup.findAll('div', class_ = 'jobCard')
        for block in blocks:
            id = block['data-jobid']
            tit = block.find('a', class_ = 'title')
            jobTitle = tit.text.strip()
            jobURL = tit['href']
            jobDescription = block.find('div', id = id + 'Desc').text.strip()
            stat = block.find('div', class_ = 'stats').text.split('|')
            jobDate, jobDuration, proposalsSoFar = self.extractStatistics(stat)
            props = block.findAll('div', class_ = 'prof')
            jobCategory, jobSkills, jobLocation = self.extractProperties(props)
            struct = {'Id' : id,
                      'Title': jobTitle,
                      'URL' : jobURL,
                      'Description' : jobDescription,
                      'Date' : jobDate,
                      'Duration' : jobDuration,
                      'Proposals' : proposalsSoFar,
                      'Category' : jobCategory,
                      'Skills' : jobSkills,
                      'Location' : jobLocation
                     }
            jobDB.append(struct)
            self.processedEntries += 1
            if self.processedEntries >= self.nextProgressThreshold:
                self.nextPercentage += 10
                self.countInformer.processedEntriesChanged.emit([self.processedEntries,
                                                                 self.totalEntries,
                                                                 self.nextPercentage])
                self.nextProgressThreshold += self.quant
            #print 'job number', self.processedEntries
        return jobDB    

    def extractStatistics(self, statText):
        #extracting constants
        cPosted = 'Posted: '
        cEnds = 'Ends: '
        cProposals = 'Proposal'
        for t in statText:
            elem = t.strip()
            dt = elem.find(cPosted)
            end = elem.find(cEnds)
            prop = elem.find(cProposals)
            if dt > -1:
                date = elem[dt + len(cPosted):]
                dt = -1
            if end > -1:
                duration = elem[end + len(cEnds):]
                end = -1
            if prop > -1:
                proposals = re.search('\d+', elem).group(0)
                prop = -1
        return (date, duration, proposals)
    
    def extractProperties(self, props):
        #extracting constants
        cCategory = 'Category:'
        cSkills = 'Skills:'
        txt = props[0].text
        cat = txt.find(cCategory)
        ski = txt.find(cSkills)
        jobCategory = txt[cat+len(cCategory):ski].strip()
        jobSkills = txt[ski+len(cSkills):].strip()
        jobLocation = props[1].text.split('|')[-1].strip()
        return (jobCategory, jobSkills, jobLocation)
    

#initialLink = 'https://www.elance.com/r/jobs/cat-it-programming/sct-other-it-programming-12350-data-analysis-14174-web-programming-10224-data-science-14176'
#pagingLink = 'https://www.elance.com/r/jobs/cat-it-programming/sct-other-it-programming-12350-data-analysis-14174-web-programming-10224-data-science-14176/p-'
#hitsPerPage = 25
class Downloader:
    def __init__(self, initialLink, pagingLink, hitsPerPage, pages = 0):
        #print 'Started...'
        self.db_file = 'elance.json'
        self.wm = Miner(initialLink, pagingLink)
        self.ot = OreTreatment(hitsPerPage)
        self.cPage = 1
        self.tPages = 10
        self.pagesRequested = pages
        self.messenger = Messenger()
        self.ot.countInformer.processedEntriesChanged.connect(self.emitProgressChanged)

    def download(self):
        jobDB = []
        while self.cPage <= self.tPages:
            # requests block
            if self.cPage == 1:
                link = self.wm.initialLink
            else:
                link = self.wm.pagingLink + str(self.cPage)
            txt = self.wm.placeGetRequest(link)[0]
            soup = BeautifulSoup(txt)
            # set total pages to iterate
            if self.cPage == 1:
                if self.pagesRequested == 0:
                    self.tPages = self.ot.totalPagesToIterate(soup)
                else:
                    self.tPages = self.pagesRequested
                    self.ot.totalEntries = self.pagesRequested*self.ot.hitsPerPage
                    self.ot.quant = self.ot.totalEntries*self.ot.quantRatio
                    self.ot.nextProgressThreshold += self.ot.quant
            # get job block in jobDB format
            jobBlock = self.ot.getJobBlock(soup)
            jobDB += jobBlock
            # output file opened, rewrited & closed every time as jobDB increases
            f = open(self.db_file, 'w')
            f.write(json.dumps(jobDB).encode('utf8'))
            f.close()
            # update counters and outputs
            #print 'Processed page', self.cPage, 'of total', self.tPages, '; ', self.ot.processedEntries, 'jobs, of total', self.ot.totalEntries, 'Bytes:', self.wm.bytes
            self.cPage += 1
        #print 'Work complete!'
        self.messenger.downloadComplete.emit()

    def emitProgressChanged(self, stata):
        self.messenger.downloadProgressChanged.emit(stata + [self.cPage, self.tPages, self.wm.bytes])

class Messenger(QObject):
    downloadComplete = Signal()
    downloadProgressChanged = Signal(list)
    # list format: list[0] = processed entries
    #              list[1] = total entries
    #              list[2] = percentage (from 0 to 100) for progressBar
    #              list[3] = current page processed
    #              list[4] = total pages to process
    #              list[5] = how many bytes downloaded so far

# test stub
# downloader = Downloader('https://www.elance.com/r/jobs/cat-it-programming/sct-other-it-programming-12350-data-analysis-14174-web-programming-10224-data-science-14176',
#     'https://www.elance.com/r/jobs/cat-it-programming/sct-other-it-programming-12350-data-analysis-14174-web-programming-10224-data-science-14176/p-',
#     25)
# downloader.download()