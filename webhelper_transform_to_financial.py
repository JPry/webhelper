import sys
import os

from webhelper import parse_rules
from webhelper_csv import CSVSpreadsheet


def standardize_date(d):
    if len(d) <= 0:
        return ""
    parts = d.split('/')
    try:
        parts = map(int, parts)
    except ValueError:
        return ""

    if parts[2] < 2000:
        parts[2] += 2000
    return '%0.2d/%0.2d/%d' % (parts[0], parts[1], parts[2])


def standardize_amount(am):
    return am.replace(",", "").replace(" ", "").replace("$", "")


def main():
    verbose = False
    spreadsheet_name = "Webhelper"
    webhelper_rulefile = os.path.dirname(os.path.realpath(__file__)) + os.sep + "webhelper_rules.txt"

    if '-v' in sys.argv:
        sys.argv.remove('-v')
        verbose = True

    if '-n' in sys.argv:
        spreadsheet_name = sys.argv[sys.argv.index('-n') + 1]
        sys.argv.remove('-n')
        sys.argv.remove(spreadsheet_name)

    if '-r' in sys.argv:
        webhelper_rulefile = sys.argv[sys.argv.index('-r') + 1]
        sys.argv.remove('-r')
        sys.argv.remove(webhelper_rulefile)

    if '-h' in sys.argv or '--help' in sys.argv:
        print "Usage: %s [-h] [--help] [-v] [--import-google] [--export-google] [-r <webhelper rule file>] [-n <CSV file prefix or spreadsheet name>]" % (
        sys.argv[0],)
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
            print "Importing %s data from %s" % (rule, import_spreadsheet,)
        rows = import_spreadsheet.import_data(rule)
        if verbose:
            print "Finished importing %s data from %s" % (rule, import_spreadsheet,)

        financial_data_rows = []
        if len(rows) > 0:
            # Let's look for a header
            max_populated_cells = 0
            header_index = None
            for ind, row in enumerate(rows):
                # Find whether all cells in this row are alpha numeric.  If any are numeric, this is probably not a header
                all_alphanum = True
                for cell in row:
                    if cell.replace(',', '').replace('$', '').replace('.', '').replace(' ', '').isdigit():
                        all_alphanum = False
                        break
                if not all_alphanum:
                    continue
                if len(filter(lambda val: val, row)) > max_populated_cells:
                    max_populated_cells = len(filter(lambda val: val, row))
                    header_index = ind

            # If we didn't even find a header with at least 3 columns, that doesn't count as a header
            if max_populated_cells < 3:
                header_index = None

            if header_index != None and verbose:
                print "Found header at row %d" % (header_index,)

            found_date = None
            found_note = None
            found_amount = None
            found_debit = None
            found_credit = None

            # Look for key information, date of transaction, note and dollar amount
            if header_index != None:
                for ind, cell in enumerate(rows[header_index]):
                    if found_date == None and cell.lower().find("date") >= 0:
                        found_date = ind
                    elif found_note == None and cell.lower().find("description") >= 0 or cell.lower().find(
                            "note") >= 0 or cell.lower().find("memo") >= 0:
                        found_note = ind
                    elif found_amount == None and cell.lower().find("amount") >= 0:
                        found_amount = ind
                    elif found_debit == None and cell.lower().find("debit") >= 0:
                        found_debit = ind
                    elif found_credit == None and cell.lower().find("credit") >= 0:
                        found_credit = ind
            else:
                for ind, cell in enumerate(rows[0]):
                    if found_amount == None and cell.replace(',', '').replace('$', '').replace('.', '').replace(' ',
                                                                                                                '').isdigit():
                        found_amount = ind
                    elif found_date == None and cell.replace('/', '').replace(' ', '').isdigit():
                        found_date = ind
                    elif found_note == None and not cell.replace(',', '').replace('$', '').replace('.', '').replace(' ',
                                                                                                                    '').isdigit():
                        found_note = ind
                header_index = -1

            financial_data_rows.append([])
            if found_date != None:
                financial_data_rows[-1].append("Date")
            if found_amount != None or (found_debit != None and found_credit != None):
                financial_data_rows[-1].append("Amount")
            if found_note != None:
                financial_data_rows[-1].append("Note")

            if verbose:
                print "Built header: " + str(financial_data_rows[-1])

            for row in rows[header_index + 1:]:
                new_row = []
                if found_date != None:
                    if len(row) > found_date:
                        new_row.append(standardize_date(row[found_date]))
                    else:
                        new_row.append("")
                if found_amount != None or (found_debit != None and found_credit != None):
                    amount = None
                    if found_amount != None and len(row) > found_amount:
                        amount = row[found_amount]
                    elif found_debit != None and len(row) > found_debit and standardize_amount(row[found_debit]):
                        amount = "-" + row[found_debit]
                    elif found_credit != None and len(row) > found_credit and standardize_amount(row[found_credit]):
                        amount = row[found_credit]

                    if amount:
                        try:
                            new_row.append("%0.2f" % (round(float(standardize_amount(amount)), 2)))
                        except:
                            new_row.append("")
                    else:
                        new_row.append("")

                # If date and amount are blank, maybe this is another row of notes
                if found_note != None and found_date != None and not new_row[0] and (
                        found_amount != None or (found_debit != None and found_credit != None)) and not new_row[-1]:
                    if found_note != None and len(row) > found_note and row[found_note]:
                        financial_data_rows[-1][-1] += " " + row[found_note]
                    # Whether there were additional notes or not, let's skip any rows without proper information
                    continue

                if found_note != None:
                    if len(row) > found_note:
                        new_row.append(row[found_note])
                    else:
                        new_row.append("")

                # Finally, add the new row
                financial_data_rows.append(new_row)

        if verbose:
            print "Exporting %s__financial data to %s" % (rule, export_spreadsheet,)
        export_spreadsheet.export_data(financial_data_rows, "%s__financial" % (rule,))
        if verbose:
            print "Finished exporting %s__financial data to %s" % (rule, export_spreadsheet,)


if __name__ == "__main__":
    main()
