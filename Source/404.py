#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
404.
A simple multithreaded dead link checker.
"""


import os
import queue
import sys
import time
import urllib

from queue import Queue
from threading import Thread

from argparse import ArgumentParser, RawDescriptionHelpFormatter


# Information and error messages:

def outln(line):
    """ Write 'line' to stdout, using the platform encoding and newline format. """
    print(line, flush = True)


def errln(line):
    """ Write 'line' to stderr, using the platform encoding and newline format. """
    print('404.py: error:', line, file = sys.stderr, flush = True)


# Non-builtin imports:

try:
    import requests

    from bs4 import BeautifulSoup
    from requests import RequestException, Timeout

except ImportError:
    errln('404 requires the following modules:')
    errln('beautifulsoup4 4.3.2+ - <https://pypi.python.org/pypi/beautifulsoup4>')
    errln('requests 2.7.0+ - <https://pypi.python.org/pypi/requests>')
    sys.exit(1)


# Threads, tasks and a thread pool:

class Worker(Thread):
    """
    Thread that pops tasks from a '.todo' Queue, executes them, and puts
    the completed tasks in a '.done' Queue.

    A task is any object that has a run() method.
    Tasks themselves are responsible to hold their own results.
    """

    def __init__(self, todo, done):
        super().__init__()
        self.todo = todo
        self.done = done
        self.daemon = True
        self.start()

    def run(self):
        while True:
            task = self.todo.get()
            task.run()
            self.done.put(task)
            self.todo.task_done()


class Link404Task(object):
    """
    A task that makes a HEAD request to a given link
    and stores the resulting status code.
    """
    def __init__(self, link, timeout):
        self.link = link
        self.timeout = timeout

        # will hold the status code after executing run()
        # or 'timeout' if the request couldn't complete in time:
        self.status = None

        # since we run in a thread with its own context
        # exception information is captured here:
        self.exception = None

    def run(self):
        try:
            self.status = requests.head(self.link, timeout = self.timeout).status_code

        except:
            self.exception = sys.exc_info()


class ThreadPool(object):
    """
    Mantains a list of 'todo' and 'done' tasks and a number of threads
    consuming the tasks. Child threads are expected to put the tasks
    in the 'done' queue when those are completed.
    """

    def __init__(self, threads):
        self.threads = threads

        self.tasks = []
        self.results = set()

        self.todo = Queue()
        self.done = Queue()

    def start(self, tasks):
        """ Start computing tasks. """
        self.tasks = tasks

        for task in self.tasks:
            self.todo.put(task)

        for x in range(self.threads):
            Worker(self.todo, self.done)

    def wait_for_task(self):
        """ Wait for one task to complete. """
        while True:
            try:
                task = self.done.get(block = False)
                self.results.add(task)
                break

            # give tasks processor time:
            except queue.Empty:
                time.sleep(0.1)

    def poll_completed_tasks(self):
        """
        Yield the computed tasks, in the order specified when 'start(tasks)'
        was called, as soon as they are finished.
        """
        for task in self.tasks:
            while True:
                if task in self.results:
                    yield task
                    break
                else:
                    self.wait_for_task()

        # at this point, all the tasks are completed:
        self.todo.join()


# IO:

# For portability, all output is done in bytes
# to avoid Python default encoding and automatic newline conversion:

def utf8_bytes(string):
    """ Convert 'string' to bytes using UTF-8. """
    return bytes(string, 'UTF-8')


BYTES_NEWLINES = {
    'dos'    : b'\r\n',
    'mac'    : b'\r',
    'unix'   : b'\n',
    'system' : utf8_bytes(os.linesep),
}


def binary_stdout_writeline(line, newline):
    """
    Write 'line' (as bytes) to stdout without buffering
    using the specified 'newline' format (as bytes).
    """
    sys.stdout.buffer.write(line)
    sys.stdout.buffer.write(newline)
    sys.stdout.flush()


# Crawling links:

def absolute_links(urlstring, skip_internal = False, skip_external = False):
    """
    Download HTML from urlstring (using a GET request), parse it
    and return all the http/s links.

    Relative links are converted to absolute links.
    Duplicates are removed.
    """
    response = requests.get(urlstring)
    soup = BeautifulSoup(response.content, from_encoding = response.encoding)
    netloc = urllib.parse.urlparse(urlstring).netloc

    result = set()
    for a in soup.find_all('a', href = True):
        absolute_link = urllib.parse.urljoin(urlstring, a['href'])
        parsed = urllib.parse.urlparse(absolute_link)
        is_internal = (netloc == parsed.netloc)

        # accept http/s protocols:
        if parsed.scheme not in ('http', 'https'):
            continue

        # skip:
        if (is_internal and skip_internal) or (not is_internal and skip_external):
            continue

        # no duplicates:
        if absolute_link not in result:
            result.add(absolute_link)

    return list(result)


# Parser:

def make_parser():
    parser = ArgumentParser(
        description = __doc__,
        formatter_class = RawDescriptionHelpFormatter,
        epilog = 'example: 404.py http://beluki.github.io --skip-external --threads 3',
        usage  = '404.py url [option [options ...]]',
    )

    # positional:
    parser.add_argument('url',
        help = 'url to crawl looking for links')

    # optional:
    parser.add_argument('--newline',
        help = 'use a specific newline mode (default: system)',
        choices = ['dos', 'mac', 'unix', 'system'],
        default = 'system')

    parser.add_argument('--print-all',
        help = 'print all status codes and urls instead of only 404s',
        action = 'store_true')

    parser.add_argument('--skip-internal',
        help = 'skip internal links (same domain)',
        default = False,
        action = 'store_true')

    parser.add_argument('--skip-external',
        help = 'skip external links (different domain)',
        default = False,
        action = 'store_true')

    parser.add_argument('--threads',
        help = 'number of threads (default: 1)',
        default = 1,
        type = int)

    parser.add_argument('--timeout',
        help = 'seconds to wait for request responses (default: 10)',
        default = 10,
        type = int)

    return parser


# Main program:

def run(url, newline, print_all, skip_internal, skip_external, threads, timeout):
    """
    Print all the links in url that return 404 to stdout.
    """
    status = 0
    pool = ThreadPool(threads)
    tasks = []

    # crawl:
    try:
        links = absolute_links(url, skip_internal, skip_external)
        tasks = [Link404Task(link, timeout) for link in links]

    except RequestException as e:
        errln('unable to connect to: {}'.format(url))
        errln('exception message: {}'.format(e))
        sys.exit(1)

    # start checking links:
    pool.start(tasks)
    for task in pool.poll_completed_tasks():

        # error in request:
        if task.exception:
            status = 1
            exc_type, exc_obj, exc_trace = task.exception

            # provide a concise error message for timeouts (common)
            # otherwise, use the exception information:
            if isinstance(exc_obj, Timeout):
                errln('{} - timeout.'.format(task.link))
            else:
                errln('{} - {}.'.format(task.link, exc_obj))

        else:
            if print_all or (task.status == 404):
                output = utf8_bytes('{}: {}'.format(task.status, task.link))
                binary_stdout_writeline(output, newline)

    sys.exit(status)


def main():
    parser = make_parser()
    options = parser.parse_args()

    url = options.url
    newline = BYTES_NEWLINES[options.newline]
    print_all = options.print_all
    skip_internal = options.skip_internal
    skip_external = options.skip_external
    threads = options.threads

    # 0 means no timeout:
    if options.timeout > 0:
        timeout = options.timeout
    else:
        timeout = None

    run(url, newline, print_all, skip_internal, skip_external, threads, timeout)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass

