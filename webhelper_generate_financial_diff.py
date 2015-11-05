import time
import datetime
import csv
import sys
import os

from webhelper import parse_rules
from webhelper_csv import CSVSpreadsheet

DATE_THRESHOLD = 3*24*60*60

def date_to_sec(date):
    split = date.split('/')
    if len(split) == 3:
        try:
            return (datetime.datetime(int(split[2]),int(split[0]),int(split[1])) - datetime.datetime(1970,1,1)).total_seconds()
        except ValueError:
            return 0
    else:
        return 0

def main():
    verbose = False
    spreadsheet_name = "Webhelper"
    webhelper_rulefile = os.path.dirname(os.path.realpath(__file__)) + os.sep + "webhelper_rules.txt"

    if '-v' in sys.argv:
        sys.argv.remove('-v')
        verbose = True

    if '-n' in sys.argv:
        spreadsheet_name = sys.argv[sys.argv.index('-n')+1]
        sys.argv.remove('-n')
        sys.argv.remove(spreadsheet_name)

    if '-r' in sys.argv:
        webhelper_rulefile = sys.argv[sys.argv.index('-r')+1]
        sys.argv.remove('-r')
        sys.argv.remove(webhelper_rulefile)

    if '-h' in sys.argv or '--help' in sys.argv:
        print "Usage: %s [-h] [--help] [-v] [--import-google] [--export-google] [-r <webhelper rule file>] [-n <CSV file prefix or spreadsheet name>]" % (sys.argv[0],)
        sys.exit(1)

    import_spreadsheet = None
    if '--import-google' in sys.argv:
        sys.argv.remove('--import-google')
        from webhelper_google import GoogleSpreadsheet
        import_spreadsheet = GoogleSpreadsheet(spreadsheet_name)
    else:
        import_spreadsheet = CSVSpreadsheet(spreadsheet_name)

    export_spreadsheet = None
    if '--export-google' in sys.argv:
        sys.argv.remove('--export-google')
        from webhelper_google import GoogleSpreadsheet
        # If we have already opened this google spreadsheet, just use the same handle
        if import_spreadsheet.__class__ == GoogleSpreadsheet:
            export_spreadsheet = import_spreadsheet
        else:
            export_spreadsheet = GoogleSpreadsheet(spreadsheet_name)
    else:
        export_spreadsheet = CSVSpreadsheet(spreadsheet_name)

    f = open(webhelper_rulefile)
    rule = f.read()
    f.close()
    rules = parse_rules(rule)

    values = {}

    exportrules = []
    for rule in rules:
        for step in rule['steps']:
            if step['command'].find("export") >= 0 and rule['name'] not in exportrules:
                exportrules.append(rule['name'])

    for rule in exportrules:
        if verbose:
            print "Importing %s__financial data from %s" % (rule, import_spreadsheet,)
        rows = import_spreadsheet.import_data("%s__financial" % (rule,))
        if verbose:
            print "Finished importing %s__financial data from %s" %(rule, import_spreadsheet,)

        if verbose:
            print "Importing %s__financial_recent data from %s" % (rule, import_spreadsheet,)
        recentrows = import_spreadsheet.import_data("%s__financial_recent" % (rule,))
        if verbose:
            print "Finished importing %s__financial_recent data from %s" %(rule, import_spreadsheet,)

        if verbose:
            print "Reading previous %s__financial_diff data from %s" % (rule, export_spreadsheet,)
        data_rows_diff = export_spreadsheet.import_data("%s__financial_diff" % (rule,))
        if verbose:
            print "Finished reading previous %s__financial_diff data from %s" %(rule, export_spreadsheet,)

        lresolved = {}
        rresolved = {}
        if len(rows) > 1 and len(recentrows) > 1 and rows[0] != recentrows[0]:
            print "ERROR: The headers on the data from %s__financial_recent do not match the headers from %s__financial" % (rule, rule)
            continue
        # Check for equals
        for ind, row in enumerate(recentrows[1:]):
            for ind2, row2 in enumerate(rows[1:]):
                if row == row2:
                    lresolved[ind] = ind2
                    rresolved[ind2] = ind

        if len(lresolved.keys()) < len(recentrows) and len(rows) > 1 and len(recentrows) > 1 and "Note" in rows[0] and "Date" in rows[0] and "Amount" in rows[0]:
            # Make header for special Date/Amount/Note case
            lnote = recentrows[0].index("Note")
            rnote = rows[0].index("Note")
            ldate = recentrows[0].index("Date")
            rdate = rows[0].index("Date")
            lamount = recentrows[0].index("Amount")
            ramount = rows[0].index("Amount")
            header = ["Change Type", "Date", "Amount", "Note", "New Date", "New Note"]
            if len(data_rows_diff) > 0:
                if data_rows_diff[0] != header:
                    print "ERROR: The nature of the data seems to have changed such that we now have Date/Amount/Note but we formerly didn't.  Skipping %s__financial." % (rule,)
                    continue
            else:
                data_rows_diff.append(header)

            # Check for note-only changes
            for ind, row in enumerate(recentrows[1:]):
                if lresolved.has_key(ind):
                    continue
                for ind2, row2 in enumerate(rows[1:]):
                    if rresolved.has_key(ind2):
                        continue
                    if row[ldate] == row2[rdate] and row[lamount] == row2[ramount]:
                        data_rows_diff.append(["Modify", row[ldate], row[lamount], row[lnote], "", row2[rnote]])
                        lresolved[ind] = ind2
                        rresolved[ind2] = ind

            if len(lresolved.keys()) < len(recentrows):
                # Check for date-only changes by a certain threshold
                for ind, row in enumerate(recentrows[1:]):
                    if lresolved.has_key(ind):
                        continue
                    for ind2, row2 in enumerate(rows[1:]):
                        if rresolved.has_key(ind2):
                            continue
                        if abs(date_to_sec(row[ldate]) - date_to_sec(row2[rdate])) < DATE_THRESHOLD and row[lamount] == row2[ramount] and row[lnote] == row2[rnote]:
                            data_rows_diff.append(["Modify", row[ldate], row[lamount], row[lnote], row2[rdate], ""])
                            lresolved[ind] = ind2
                            rresolved[ind2] = ind

            if len(lresolved.keys()) < len(recentrows):
                # Check for note and date changes by a certain threshold
                for ind, row in enumerate(recentrows[1:]):
                    if lresolved.has_key(ind):
                        continue
                    for ind2, row2 in enumerate(rows[1:]):
                        if rresolved.has_key(ind2):
                            continue
                        if abs(date_to_sec(row[ldate]) - date_to_sec(row2[rdate])) < DATE_THRESHOLD and row[lamount] == row2[ramount]:
                            data_rows_diff.append(["Modify", row[ldate], row[lamount], row[lnote], row2[rdate], row2[rnote]])
                            lresolved[ind] = ind2
                            rresolved[ind2] = ind

        elif len(lresolved.keys()) < len(recentrows) or len(rresolved.keys()) < len(rows):
            # Make diff header for normal case
            header = []
            if len(rows) > 1:
                header = ["Change Type"]+rows[0]
            elif len(recentrows) > 1:
                header = ["Change Type"]+recentrows[0]
            if "Date" in header and "Amount" in header and "Note" in header:
                header.extend(["New Date", "New Note"])

            if len(data_rows_diff) > 0:
                if data_rows_diff[0] != header:
                    print "ERROR: The nature of the data seems to have changed such that we now have different columns than we used to.  Skipping %s__financial." % (rule,)
                    continue
            else:
                data_rows_diff.append(header)

        # Check for deleted rows
        for ind, row in enumerate(recentrows[1:]):
            if not lresolved.has_key(ind):
                data_rows_diff.append(["Delete"] + row)
                # Add blank spots to end of row if we are in the special Date/Amount/Note case
                if len(data_rows_diff[-1]) < len(data_rows_diff[0]):
                    data_rows_diff[-1].extend([""] * (len(data_rows_diff[0])-len(data_rows_diff[-1])))

        # Check for new rows
        for ind, row in enumerate(rows[1:]):
            if not lresolved.has_key(ind):
                data_rows_diff.append(["Add"] + row)
                # Add blank spots to end of row if we are in the special Date/Amount/Note case
                if len(data_rows_diff[-1]) < len(data_rows_diff[0]):
                    data_rows_diff[-1].extend([""] * (len(data_rows_diff[0])-len(data_rows_diff[-1])))

        if verbose:
            print "Exporting %s__financial_diff data to %s" % (rule, export_spreadsheet,)
        export_spreadsheet.export_data(data_rows_diff, "%s__financial_diff" % (rule,))
        if verbose:
            print "Finished exporting %s__financial_diff data to %s" %(rule, export_spreadsheet,)

        if verbose:
            print "Saving %s__financial_recent data to %s" % (rule, import_spreadsheet,)
        import_spreadsheet.export_data(rows, "%s__financial_recent" % (rule,))
        if verbose:
            print "Finished saving %s__financial_recent data to %s" %(rule, import_spreadsheet,)

if __name__ == "__main__":
    main()


