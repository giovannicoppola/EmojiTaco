# -*- coding: utf-8 -*-

from workflow import Workflow3
from workflow.notify import notify
from bs4 import BeautifulSoup
import sys

import base64
import urllib2

import os
import shutil


last_pct = 0




class DataFilerBuilder():
    def my_super_copy(self, what, where):
        try:
            shutil.copy(what, where)
        except IOError:
            os.chmod(where, 777)  # ?? still can raise exception
            shutil.copy(what, where)

    def build_headers(self, cols):
        """Extacts a mapping of column number to name -- hopefully to help future proof this script"""

        headers = {}

        for i in range(0, len(cols)):
            headers[cols[i].text] = i
            # print("Header : " + cols[i].text)
        return headers

    def buildData(self, wf, test_mode=False):

        def convert_to_unicode(str):
            """Takes a string in the form of U+XXX and turns it into a \UXXXXXXXX """
            ret = ""
            for uni in str.replace("U+", "").split(" "):
                ret += "\U00000000"[:-len(uni)] + uni

            # Apply Emoji Selector to the end
            ret += "\U0000FE0F"
            return ret

        # Print / write the output as needed
        def print_result(print_name):
            output = ','.join(
                [str(number) + ".png", print_name, code.decode('unicode_escape'), code, raw_code_string, keywords])
            csv.write(output.encode('utf-8') + "\n")

        def chunk_report(bytes_so_far, chunk_size, total_size):
            percent = float(bytes_so_far) / total_size
            percent = int(round(percent * 100, 2))

            if int(last_pct) < int(percent):
                #print("Downloaded {} of {} bytes {:0.2f}%".format(bytes_so_far, total_size, percent))
                last_pct = int(percent)
                sys.stdout.write("Downloaded %d of %d bytes (%0.2f%%)\r" % (bytes_so_far, total_size, percent))

            #if bytes_so_far >= total_size:
                #sys.stdout.write('\n')

        def chunk_read(response, chunk_size=8192, report_hook=None):
            total_size = response.info().getheader('Content-Length').strip()
            total_size = int(total_size)
            bytes_so_far = 0

            while 1:
                chunk = response.read(chunk_size)
                bytes_so_far += len(chunk)

                if not chunk:
                    break

                if report_hook:
                    report_hook(bytes_so_far, chunk_size, total_size)

            return bytes_so_far

        ###################################
        # END INTERNAL FUNCTION definition
        ###################################

        url1 = 'http://unicode.org/emoji/charts-beta/full-emoji-list.html'
        url2 = 'http://unicode.org/emoji/charts/full-emoji-list.html'

        if not test_mode:
            notify(title=u'Emoji Taco', text=u'Initializing emoji data', sound=None)

        try:
            try:
                if test_mode:
                    print "Querying: ", url1
                html = urllib2.urlopen(url1, timeout=10000)
                chunk_read(html, report_hook=chunk_report)


            except Exception as e:
                if test_mode:
                    print "Fall back query: ", url2
                html = urllib2.urlopen(url2, timeout=10000)
                chunk_read(html, report_hook=chunk_report)
                print(e)
        except urllib2.HTTPError as e:
            if not test_mode:
                notify(title='ERROR', text=str(e))
            exit()
        except Exception as e:
            if not test_mode:
                notify(title='Error', text=str(e))
            else:
                print str(e)
            exit()

        if not test_mode:
            notify(title=u'Emoji Taco', text=u'Converting emoji data', sound=None)
            soup = BeautifulSoup(html, "lxml")
        else:
            soup = BeautifulSoup(html)

        tables = soup.findAll('table')

        # Used to handle alias situations
        alias_dict = {}

        # Open the output file
        csv = open('emoji.csv', 'w')

        if not test_mode:
            notify(title=u'Emoji Taco', text=u'Parsing emoji data', sound=None)

        headers = None

        emoji_count = 0

        for table in tables:

            rows = table.findAll('tr')

            for tr in rows:
                cols = tr.findAll(['th', 'td'])

                if not headers:
                    headers = self.build_headers(cols)

                if len(headers) < 3:
                    # " Bad header detected ... lets abort for now"
                    headers = None
                    continue

                # March 15 - Ignore the sub-header lines like "Face neutral" and stuff
                # March 15 - Ignore the strange lines that have some emoji - probably are the ones that arent decided on yet (like star-struck)
                if len(cols) < 7:
                    continue

                # Extract the raw unicode string - basically turn it into something python can print
                # raw_code_string = str(cols[1].text)
                raw_code_string = str(cols[headers[u'Code']].text)

                if raw_code_string == u'Code':
                    # Skip header lines
                    continue

                # Unicode code
                code = convert_to_unicode(raw_code_string)
                # The apple column - if we have no data here we prob dont care about the emoji because it isnt in osx
                apple = cols[headers[u'Appl']].text

                # March 15th - File format changed so sometimes we get funky text like this in a case where there is no apple emoji - skip these items
                if apple == u'…     …':
                    continue

                try:
                    names = cols[headers[u'CLDR Short Name']].text.replace(u'amp;', u'').split(u'≊ ')
                except:
                    # March 29th - added a table to the bottom of the page listing out totals of emoji type - it breaks here so we must skip over it
                    continue

                # The number
                number = int(cols[headers[u'№']].text)

                # Zero out alias and name
                alias = None
                name = None

                keywords = cols[headers[u'CLDR Short Name']].text.replace("|", '').replace('  ', ' ').replace('  ', ' ')

                image_filename = "img/" + str(number) + '.png'

                # Ignore non apple unicodes
                if apple != u'':
                    self.my_super_copy('na.png', image_filename)
                    # continue
                else:
                    # With default Beautiful soup parser use this line
                    # img_data = base64.b64decode(cols[4].contents[0].attrs[2][1].split(',')[1])
                    # With lxml parser use this
                    img_data = base64.b64decode(cols[headers[u'Appl']].contents[0].attrs['src'].split(',')[1])
                    with open(image_filename, 'wb') as f:
                        f.write(img_data)

                emoji_count += 1

                if len(names) > 1:  # We have an alias definition
                    name = names[0]
                    alias = names[1]
                    alias_dict[alias] = name
                elif names[0].islower():

                    # Split on comma
                    names = names[0].split(', ')
                    name = alias_dict.get(names[0], names[0])
                    if len(names) > 1:
                        name += " "
                        name += names[1]
                else:
                    name = names[0]

                if alias:
                    print_result(alias.upper())

                print_result(name)

        if not test_mode:
            notify(title=u'Emoji Taco', text=u'Is ready for use. {} emoji processed'.format(emoji_count), sound=None)


def main(wf):
    dfb = DataFilerBuilder()
    dfb.buildData(wf)


if __name__ == '__main__':
    wf = Workflow3()
    sys.exit(wf.run(main))
