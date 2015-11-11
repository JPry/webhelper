import sys
import os

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from webhelper import parse_rules, run_rule
from webhelper_csv import CSVSpreadsheet

dcap = dict(DesiredCapabilities.PHANTOMJS)
dcap["phantomjs.page.settings.userAgent"] = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/53 "
    "(KHTML, like Gecko) Chrome/15.0.87"
)


def main():
    verbose = False
    screenshot = None
    spreadsheet_name = "Webhelper"
    webhelper_rulefile = os.path.dirname(os.path.realpath(__file__)) + os.sep + "webhelper_rules.txt"

    if '-v' in sys.argv:
        sys.argv.remove('-v')
        verbose = True

    if '-s' in sys.argv:
        screenshot = sys.argv[sys.argv.index('-s') + 1]
        sys.argv.remove('-s')
        sys.argv.remove(screenshot)

    if '-n' in sys.argv:
        spreadsheet_name = sys.argv[sys.argv.index('-n') + 1]
        sys.argv.remove('-n')
        sys.argv.remove(spreadsheet_name)

    if '-r' in sys.argv:
        webhelper_rulefile = sys.argv[sys.argv.index('-r') + 1]
        sys.argv.remove('-r')
        sys.argv.remove(webhelper_rulefile)

    if '-h' in sys.argv or '--help' in sys.argv:
        print "Usage: %s [-h] [--help] [-v] [--export-google] [-s <filename to save .png screenshot to>] [-r <webhelper rule file>] [-n <CSV file prefix or spreadsheet name>]" % (
        sys.argv[0],)
        sys.exit(1)

    driver = webdriver.PhantomJS(desired_capabilities=dcap)
    # driver = webdriver.Remote(command_executor='http://127.0.0.1:4444/wd/hub', desired_capabilities=dcap)

    driver.set_window_size(1200, 600)
    driver.implicitly_wait(10)

    spreadsheet = None
    if '--export-google' in sys.argv:
        sys.argv.remove('--export-google')
        from webhelper_google import GoogleSpreadsheet
        spreadsheet = GoogleSpreadsheet(spreadsheet_name)
    else:
        spreadsheet = CSVSpreadsheet(spreadsheet_name)

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

    for rule_to_run in rules:
        if verbose:
            print "Starting to run rule " + rule_to_run['name']
        value = run_rule(driver, rule_to_run, verbose)
        if verbose:
            print "Ran rule " + rule_to_run['name']
        values[rule_to_run['name']] = value
        if verbose:
            print `value`
        if rule_to_run['name'] in exportrules:
            if type(value) != type([]):
                value = []
            if len(value) > 0 and type(value[0]) != type([]):
                value = [value]
            if verbose:
                print "Exporting %s data to %s" % (rule_to_run['name'], spreadsheet,)
            spreadsheet.export_data(value, rule_to_run['name'])
            if verbose:
                print "Finished exporting %s data to %s" % (rule_to_run['name'], spreadsheet,)

        if screenshot:
            driver.save_screenshot(screenshot)
    if verbose:
        print "Done running rules"


if __name__ == "__main__":
    main()
