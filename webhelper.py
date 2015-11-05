import selenium.webdriver.support.select
from selenium.webdriver.common.keys import Keys
import time
import getpass


#import logging
#logging.basicConfig(level=logging.DEBUG)

def parse_rules(st):
    lines = st.split('\n')
    rulename = None
    ruleset = []
    for line in lines:
        if line.startswith('rule '):
            rulename = line[5:]
            ruleset.append({'name':rulename, 'steps':[]})
        elif not line:
            rulename = None
        elif line.strip().startswith('#'):
            continue
        elif rulename:
            if line.find(' ') > 0:
                ruleset[-1]['steps'].append({'command': line[:line.find(' ')], 'param': line[line.find(' ')+1:]})
            else:
                ruleset[-1]['steps'].append({'command': line})
        else:
            raise Exception("No rule defined")
    return ruleset

def run_rule(driver, rule, verbose = False):
    return_val = False
    current_element = None
    url_history = []
    for s in rule['steps']:
        if verbose:
            print s
        url_history.append(driver.current_url)
        if s['command'].find('match_') == 0:
            # If last match was a "multiple" command, the actions are now over so it's time to revert back to normal mode
            if type(current_element) == type([]):
                current_element = current_element[0]

            found_command = False
            for etype in ['link_text', 'xpath', 'id', 'name', 'css_selector', 'partial_link_text', 'tag_name', 'class_name']:
                if s['command'] == 'match_' + etype:
                    current_element = getattr(driver, 'find_element_by_' + etype)(s['param'])
                    if not current_element:
                        return return_val

                    found_command = True
                    break

                elif s['command'] == 'match_within_' + etype:
                    current_element = getattr(current_element, 'find_element_by_' + etype)(s['param'])
                    if not current_element:
                        return return_val

                    found_command = True
                    break

                elif s['command'] == 'match_multiple_' + etype:
                    current_element = getattr(driver, 'find_elements_by_' + etype)(s['param'])
                    if not current_element:
                        return return_val

                    found_command = True
                    break

                elif s['command'] == 'match_multiple_within_' + etype:
                    current_element = getattr(current_element, 'find_elements_by_' + etype)(s['param'])
                    if not current_element:
                        return return_val

                    found_command = True
                    break

            if s['command'] == 'match_within_text':
                if current_element.text != s['param']:
                    return return_val
                found_command = True
            elif s['command'] == 'match_within_partial_text':
                if current_element.text.find(s['param']) < 0:
                    return return_val
                found_command = True
            elif s['command'] == 'match_url':
                if driver.current_url != s['param']:
                    return return_val
                found_command = True
            elif s['command'] == 'match_partial_url':
                if driver.current_url.find(s['param']) < 0:
                    return return_val
                found_command = True

            if not found_command:
                raise Exception("Command not found: "+s['command'])
        else:
            # We must now signal at least that we have successfully passed the beginning match commands and proceeded onto non-match commands
            if return_val == False:
                return_val = True
            if s['command'] == 'get':
                driver.get(s['param'])
            elif s['command'] == 'switch_to_frame':
                if s['param'].isdigit():
                    driver.switch_to_frame(int(s['param']))
                else:
                    driver.switch_to_frame(s['param'])
            elif s['command'] == 'back':
                driver.back()
            elif s['command'] == 'forward':
                driver.forward()
            elif s['command'] == 'wait':
                time.sleep(float(s['param']))
            elif s['command'] == 'wait_url_change':
                hist = []
                # If possible, find the URL before the previous command was run
                if len(url_history) >= 3:
                    compare = url_history[-3]
                # Otherwise, find the URL before this command was run
                else:
                    compare = url_history[-1]
                TIMEOUT = 8
                CHECK_INTERVAL = 0.2
                return_val = False
                for ind in range(int(TIMEOUT/CHECK_INTERVAL)):
                    # Make sure the past 3 samples have been the same, all different than the comparison url
                    if len(hist) >= 3 and driver.current_url != compare and hist[-1] != compare and hist[-2] != compare and hist[-3] != compare:
                        return_val = True
                        break
                    hist.append(driver.current_url)
                    time.sleep(CHECK_INTERVAL)
                if not return_val:
                    if len(url_history) < 3:
                        print "WARNING: Running wait_url_change as the first command in a rule limits the scope of knowing the most recent stable URL.  Returning failure for this rule."
                    return return_val
                mark_url = driver.current_url
            else:
                # All of the remaining commands can be multiplied by a preceeding "match_multiple"
                element_operation = current_element
                if type(current_element) != type([]):
                    element_operation = [current_element]

                for elem in element_operation:
                    if s['command'] == 'wait_until_gone':
                        TIMEOUT = 20
                        CHECK_INTERVAL = 0.2
                        return_val = False
                        for ind in range(int(TIMEOUT/CHECK_INTERVAL)):
                            try:
                                elem.get_attribute("id")
                            except selenium.common.exceptions.StaleElementReferenceException:
                                return_val = True
                                break
                            time.sleep(CHECK_INTERVAL)
                        if not return_val:
                            return return_val
                    elif s['command'] == 'click':
                        elem.click()
                    elif s['command'] == 'submit':
                        elem.submit()
                    elif s['command'] == 'send_keys':
                        elem.send_keys(s['param'])
                    elif s['command'] == 'send_keys_prompt':
                        elem.send_keys(raw_input(s['param']+': '))
                    elif s['command'] == 'send_keys_prompt_password':
                        elem.send_keys(getpass.getpass(s['param']+': '))
                    elif s['command'] == 'send_special_key':
                        elem.send_keys(getattr(Keys, s['param']))
                    elif s['command'] == 'select_by_value':
                        selenium.webdriver.support.select.Select(elem).select_by_value(s['param'])
                    elif s['command'] == 'export_text':
                        text_chunks = []
                        elements = elem.find_elements_by_xpath("*")
                        for element in elements:
                            thistext = element.text
                            if thistext:
                                text_chunks.append(thistext)
                        if len(text_chunks) > 0:
                            if type(return_val) != type([]):
                                return_val = [text_chunks]
                            else:
                                return_val.append(text_chunks)
                    elif s['command'] == 'export_attribute':
                        if type(return_val) != type([]):
                            return_val = [elem.get_attribute(s['param'])]
                        else:
                            return_val.append(elem.get_attribute(s['param']))
                    else:
                        raise Exception("Command not found: "+s['command'])

        # Track the past URLs
        url_history.append(driver.current_url)
        if len(url_history) >= 6:
            url_history = url_history[2:]
                
    return return_val
