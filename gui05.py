#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from operator import itemgetter
from collections import Counter
import nltk
import json
import sys
import time
from PySide.QtCore import Qt, QSettings
from PySide.QtGui import QMainWindow, QIcon, QDesktopWidget, QStatusBar,\
                         QFrame, QLabel, QVBoxLayout, QPushButton,\
                         QTableView, QItemSelectionModel, QSplitter, QInputDialog
from MyTableModel import *
from downloader import Downloader

class MainWindow(QMainWindow):
    def __init__(self, datta):
        QMainWindow.__init__(self)
        self.setWindowTitle('Project Parser')
        appIcon = QIcon('search.png')
        self.setWindowIcon(appIcon)
        self.viewPortBL = QDesktopWidget().availableGeometry().topLeft()
        self.viewPortTR = QDesktopWidget().availableGeometry().bottomRight()
        self.margin = int(QDesktopWidget().availableGeometry().width()*0.1/2)
        self.shirina = QDesktopWidget().availableGeometry().width() - self.margin*2
        self.visota = QDesktopWidget().availableGeometry().height() - self.margin*2
        self.setGeometry(self.viewPortBL.x() + self.margin, self.viewPortBL.y() + self.margin,
                         self.shirina, self.visota)
        # statusbar
        self.myStatusBar = QStatusBar()
        self.setStatusBar(self.myStatusBar)
        
        #lower long layout
        self.lowerLong = QFrame()
        self.detailsLabel = QLabel()
        self.skillsLabel = QLabel()
        self.urlLabel = QLabel()
        self.locationLabel = QLabel()
        self.skillsLabel.setText('Huj huj huj')
        self.detailsLabel.setWordWrap(True)
        self.la = QVBoxLayout()
        self.la.addWidget(self.detailsLabel)
        self.la.addWidget(self.skillsLabel)
        self.la.addWidget(self.urlLabel)
        self.la.addWidget(self.locationLabel)
        self.lowerLong.setLayout(self.la)

        # table
        self.source_model = MyTableModel(self, datta, ['Id', 'Date', 'Title'])
        self.proxy_model = myTableProxy(self)
        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setDynamicSortFilter(True)
        self.table_view = QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.resizeColumnsToContents()
        self.table_view.resizeRowsToContents()
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSortingEnabled(True)
        self.table_view.sortByColumn(2, Qt.AscendingOrder)

        # events
        self.selection = self.table_view.selectionModel()
        self.selection.selectionChanged.connect(self.handleSelectionChanged)
        #DO NOT use CreateIndex() method, use index()
        index = self.proxy_model.index(0,0)
        self.selection.select(index, QItemSelectionModel.Select)
        
        self.upperLong = self.table_view  

        # right side widgets
        self.right = QFrame()
        self.la1 = QVBoxLayout()
        self.btnDownload = QPushButton('Download data')
        self.btnDownload.clicked.connect(self.download)
        self.myButton = QPushButton('Show Skillls')
        self.myButton.clicked.connect(self.showAllSkills)
        self.btnSearchByWord = QPushButton('Search by word(s)')
        self.btnSearchByWord.clicked.connect(self.onSearchByWord)
        self.btnResetFilter= QPushButton('Discard Filter')
        self.btnResetFilter.clicked.connect(self.discardFilter)
        self.btnCopyURL = QPushButton('URL to Clipboard')
        self.btnCopyURL.clicked.connect(self.copyToClipboard)
        self.btnExit = QPushButton('Exit')
        self.btnExit.clicked.connect(lambda: sys.exit())
        self.dateTimeStamp = QLabel()
        self.la1.addWidget(self.btnDownload)
        self.la1.addSpacing(10)
        self.la1.addWidget(self.myButton)
        self.la1.addSpacing(10)
        self.la1.addWidget(self.btnSearchByWord)
        self.la1.addSpacing(10)
        self.la1.addWidget(self.btnResetFilter)
        self.la1.addSpacing(10)
        self.la1.addWidget(self.btnCopyURL)
        self.la1.addSpacing(70)
        self.la1.addWidget(self.btnExit)
        self.la1.addStretch(stretch=0)
        self.la1.addWidget(self.dateTimeStamp)
        self.right.setLayout(self.la1)
        self.right.setFrameShape(QFrame.StyledPanel)

        # splitters
        self.horiSplit = QSplitter(Qt.Vertical)
        self.horiSplit.addWidget(self.upperLong)
        self.horiSplit.addWidget(self.lowerLong)
        self.horiSplit.setSizes([self.visota/2, self.visota/2])
        self.vertiSplit = QSplitter(Qt.Horizontal)
        self.vertiSplit.addWidget(self.horiSplit)
        self.vertiSplit.addWidget(self.right)
        self.vertiSplit.setSizes([self.shirina*3/4, self.shirina*1/4])
        self.setCentralWidget(self.vertiSplit)
        
        self.settings = QSettings('elance.ini', QSettings.IniFormat)
        self.settings.beginGroup('DATE_STAMP')
        self.dateTimeStamp.setText('Data actuality: %s' % self.settings.value('date/time'))
        self.settings.endGroup()
        self.statusText = ''

    def handleSelectionChanged(self, selected, deselected):
        for index in selected.first().indexes():
            #print('Row %d is selected' % index.row())
            ind = index.model().mapToSource(index)
            desc = ind.model().mylist[ind.row()]['Description']
            self.detailsLabel.setText(desc)
            skills = ', '.join(ind.model().mylist[ind.row()]['Skills']).strip()
            self.skillsLabel.setText(skills)
            url = ind.model().mylist[ind.row()]['URL']
            self.urlLabel.setText(url)
            location = ind.model().mylist[ind.row()]['Location']
            self.locationLabel.setText(location)
    
    def showAllSkills(self):
        listSkills = []
        for elem in self.source_model.mylist:
            listSkills += elem['Skills']
        allSkills = Counter(listSkills)
        tbl = MyTableModel(self, allSkills.items(), ['Skill', 'Freq'])
        win = skillsWindow(tbl, self.table_view)
        win.exec_()
    
    def discardFilter(self):
        self.table_view.model().emit(SIGNAL("modelAboutToBeReset()"))
        self.table_view.model().criteria = {}
        self.table_view.model().emit(SIGNAL("modelReset()"))
        self.table_view.resizeRowsToContents()
        
    def download(self):
        self.btnDownload.setDisabled(True)
        self.statusLabel = QLabel('Connecting')
        self.progressBar = QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.myStatusBar.addWidget(self.statusLabel, 2)
        self.myStatusBar.addWidget(self.progressBar, 1)
        self.progressBar.setValue(1)
        self.settings.beginGroup('URLS')
        initialLink = self.settings.value('CategoriesDetailed/VahaSelected/InitialLink')
        pagingLink = self.settings.value('CategoriesDetailed/VahaSelected/PagingLink')
        self.settings.endGroup()
        downloader = Downloader(initialLink, pagingLink, 25, 5)
        downloader.messenger.downloadProgressChanged.connect(self.onDownloadProgressChanged)
        downloader.messenger.downloadComplete.connect(self.onDownloadComplete)
        downloader.download()
    
    def onDownloadComplete(self):
        #QMessageBox.information(self, 'Download complete', 'Download complete!', QMessageBox.Ok)
        self.table_view.model().emit(SIGNAL("modelAboutToBeReset()"))
        self.settings.beginGroup('DATE_STAMP')
        self.settings.setValue('date/time', time.strftime('%d-%b-%Y, %H:%M:%S'))
        self.dateTimeStamp.setText('Data actuality: %s' % self.settings.value('date/time'))
        self.settings.endGroup()
        with open("elance.json") as json_file:
            jobDB = json.load(json_file)
        for elem in jobDB:
            words = nltk.tokenize.regexp_tokenize(elem['Title'].lower(), r'\w+')
            elem['Tokens'] = words
            elem['Skills'] = [t.strip() for t in elem['Skills'].split(',')]
        self.source_model.mylist = jobDB
        self.table_view.model().emit(SIGNAL("modelReset()"))
        self.btnDownload.setEnabled(True)
        self.myStatusBar.removeWidget(self.statusLabel)
        self.myStatusBar.removeWidget(self.progressBar)
        self.myStatusBar.showMessage(self.statusText, timeout = 5000)
                
    
    def onDownloadProgressChanged(self, stata):
        self.progressBar.setValue(stata[2])
        #text = 'Processed records{:5d} of{:5d}'.format(percentage[0], percentage[1])
        bajtikov = '{:,}'.format(stata[5])
        self.statusText = 'Processed page{:4d} of{:4d}. \
               Job entries{:5d} of{:5d}. \
               Downloaded{:>12s} Bytes'.format(stata[3], stata[4],
                                              stata[0], stata[1],
                                              bajtikov)
        self.statusLabel.setText(self.statusText)
        
    def copyToClipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.urlLabel.text())
        self.myStatusBar.showMessage(self.urlLabel.text(), timeout = 3000)
    
    def onSearchByWord(self):
        text, ok = QInputDialog.getText(self, 'Search the base by word(s)', 'Enter your keyword/phrase to search for:')
        if ok:
            words = [t.strip() for t in nltk.tokenize.regexp_tokenize(text.lower(), r'\w+')]
            self.table_view.model().emit(SIGNAL("modelAboutToBeReset()"))
            self.table_view.model().criteria = {'Description' : words}
            self.table_view.model().emit(SIGNAL("modelReset()"))
    

class skillsWindow(QDialog):
    def __init__(self, dataModel, oberTablo):
        QDialog.__init__(self)
        self.setWindowTitle('All Skills')
        self.setWindowIcon(QIcon('elance.ico'))
        self.oberTablo = oberTablo
        #create & configure tablewiew
        self.table_view = QTableView()
        self.table_view.setModel(dataModel)
        self.table_view.setSortingEnabled(True)
        self.table_view.sortByColumn(1, Qt.DescendingOrder)
        self.table_view.resizeColumnsToContents()
        self.table_view.resizeRowsToContents()
        #http://stackoverflow.com/questions/7189305/set-optimal-size-of-a-dialog-window-containing-a-tablewidget
        #http://stackoverflow.com/questions/8766633/how-to-determine-the-correct-size-of-a-qtablewidget
        w = 0
        w += self.table_view.contentsMargins().left() +\
             self.table_view.contentsMargins().right() +\
             self.table_view.verticalHeader().width()
        w += qApp.style().pixelMetric(QStyle.PM_ScrollBarExtent)
        for i in range(len(self.table_view.model().header)):
            w += self.table_view.columnWidth(i)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setMinimumWidth(w)
        
        # create two buttons
        self.findEntries = QPushButton('Find entries')
        self.findEntries.clicked.connect(self.ApplyFilterToMainList)
        self.cancel = QPushButton('Cancel')
        self.cancel.clicked.connect(self.winClose)
        
        self.mainLayout = QGridLayout()
        self.mainLayout.addWidget(self.table_view, 0,0,1,3)
        self.mainLayout.addWidget(self.findEntries, 1,0)
        self.mainLayout.addWidget(self.cancel, 1,2)
        self.setLayout(self.mainLayout)
        self.show()
    
    def ApplyFilterToMainList(self):
        selection = self.table_view.selectionModel().selection()
        skills = []
        for selRange in selection:
            for index in selRange.indexes():
                skill = index.model().data(index, Qt.DisplayRole)
                skills.append(skill)
        self.oberTablo.model().emit(SIGNAL("modelAboutToBeReset()"))
        self.oberTablo.model().criteria = {'Skills':skills}
        self.oberTablo.model().emit(SIGNAL("modelReset()"))
        self.close()
    
    def winClose(self):
        self.close()
    
    


        
if __name__ == '__main__':
    
    with open("elance.json") as json_file:
        jobDB = json.load(json_file)
    for elem in jobDB:
        words = nltk.tokenize.regexp_tokenize(elem['Title'].lower(), r'\w+')
        elem['Tokens'] = words
        elem['Skills'] = [t.strip() for t in elem['Skills'].split(',')]
    
    myApp = QApplication(sys.argv)
    mainWindow = MainWindow(jobDB)
    mainWindow.show()
    myApp.exec_()
    sys.exit(0)