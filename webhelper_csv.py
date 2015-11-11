import csv
import os

CSV_PATH = os.path.dirname(os.path.realpath(__file__)) + os.sep + "csv_files"


class CSVSpreadsheet:
    def __repr__(self):
        return "CSV file with prefix %s" % (self.name,)

    def __init__(self, name):
        self.name = name

    def export_data(self, rows, sheet_name):
        if not os.path.exists(CSV_PATH):
            os.mkdir(CSV_PATH)
        f = open(CSV_PATH + os.sep + "%s__%s.csv" % (self.name, sheet_name), "wb")
        w = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        for row in rows:
            w.writerow(row)
        f.close()

    def import_data(self, sheet_name):
        rows = []
        if os.path.exists(CSV_PATH + os.sep + "%s__%s.csv" % (self.name, sheet_name)):
            f = open(CSV_PATH + os.sep + "%s__%s.csv" % (self.name, sheet_name), "rb")
            r = csv.reader(f, delimiter=',', quotechar='"')
            for row in r:
                rows.append(row)
            f.close()
        return rows
