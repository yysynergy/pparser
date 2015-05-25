import operator
from PySide.QtCore import *
from PySide.QtGui import *

class MyTableModel(QAbstractTableModel):
    def __init__(self, parent, mylist, header, *args):
        """please note that column heading names must be
        exactly the same as data dictionary key names !!!"""
        QAbstractTableModel.__init__(self, parent, *args)
        self.mylist = mylist
        self.header = header
        # columngetter is a dictionary to be used in data function
        # the aim is to pass number if data is [[list or tuple], [list or tuple], ...]
        # or pass key name if data is [{dict}, {dict}, ...]
        self.columngetter = {}
        if isinstance(self.mylist[0], dict):
            # columngetter is {int:string, int:string, ...}
            i = 0
            for h in self.header:
                self.columngetter[i] = h
                i += 1
        else:
            # columngetter is {int:int, int:int, ...}
            for h in range(len(self.header)):
                self.columngetter[h] = h
    def rowCount(self, parent):
        return len(self.mylist)
    def columnCount(self, parent):
        return len(self.header)
    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
        return self.mylist[index.row()][self.columngetter[index.column()]]
    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header[col]
        return None
    def sort(self, col, order):
        """sort table by given column number col"""
        self.emit(SIGNAL("layoutAboutToBeChanged()"))
        selector = self.columngetter[col]
        self.mylist.sort(key=operator.itemgetter(selector))
        if order == Qt.DescendingOrder:
            self.mylist.reverse()
        self.emit(SIGNAL("layoutChanged()"))

class myTableProxy(QSortFilterProxyModel):
    def __init__(self, parent):
        QSortFilterProxyModel.__init__(self, parent)
        # this is a filter criteria parameter
        # must be 1-element dictionary {key:[value, value, ...]}
        # or empty dictionary if no filter
        #self.criteria = {'Skills':['PHP']}
        self.criteria = {}
    def filterAcceptsRow(self, row, parentIndex):
        if not self.criteria:
            return True
        elif self.criteriaIntersect(self.criteria, row):
            return True
        else:
            return False
    
    def criteriaIntersect(self, criteria, row):
        critList = criteria.values()[0]
        toCheckList = self.sourceModel().mylist[row][criteria.keys()[0]]
        resList = [val for val in critList if val in toCheckList]
        if len(resList) > 0:
            return True
        else:
            return False
    