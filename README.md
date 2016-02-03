
## About

This shouldn't have happened.

The thing is... I was testing a new programming language by writing
a simple web crawler as an exercise. Being frustrated by multiple concurrency
bugs in the stdlib I thought: "Okay, enough. I can probably write this in
Python in an evening".

Famous last words.

A week later, the program snowballed from a toy example and it currently
has the following features:

* Supports SSL, redirections and custom timeouts, thanks
  to the excellent [requests][] library.

* Lenient HTML parsing, so dubious markup should be fine, using
  the also excellent [beautifulsoup4][] library.

* Validates both usual `<a href="...">` hyperlinks and `<img src="...">`
  image links.

* Can check, ignore or recursively follow both internal (same domain)
  and external links.

* Tries to be efficient: multithreaded, ignores [fragments][], does not build
  a parse tree for non-link markup.

* Fits in 404 lines. :)

[beautifulsoup4]: http://www.crummy.com/software/BeautifulSoup/
[fragments]: http://en.wikipedia.org/wiki/Fragment_identifier
[requests]: http://docs.python-requests.org/en/latest/

Here is an example, checking my entire blog:

```bash
$ 404.py http://beluki.github.io --threads 20 --internal follow
404: http://cdimage.debian.org/debian-cd/7.8.0/i386/iso-cd/
Checked 144 total links in 6.54 seconds.
46 internal, 98 external.
0 network/parsing errors, 1 link errors.
```

(please, be polite and don't spawn many concurrent connections to the
same server, this is just a demonstration)

## Installation

First, make sure you are using Python 3.3+ and have the [beautifulsoup4][]
and [requests][] libraries installed. Both are available in pip.

Other than that, 404 is a single Python script that you can put in your PATH.

## Command-line options

404 has some options that can be used to change the behavior:

*  `--external [check, ignore, follow]` toggles behavior for external (different
   domain) links. The default is to check them. Be careful! 'follow' may try
   to recursively crawl the entire internet and should only be used on an
   intranet.

* ` --internal [check, ignore, follow]` like above, but for internal links.
  The default is also 'check'.

* `--newline [dos, mac, unix, system]` changes the newline format.
  I tend to use Unix newlines everywhere, even on Windows. The default is
  `system`, which uses the current platform newline format.

* `--no-redirects` avoids following redirections. Links with redirections
   will be considered ok, according to their 3xx status code.

* `--print-all` prints all the status codes/links, regardles of whether
  it indicates an error. This is useful to grep specific non-error codes
  such as 204 (no content).

* ` --quiet` avoids printing the statistics to stderr at the end.
  Useful for scripts.

* `--threads n` uses n concurrent threads to process requests.
  The default is to use a single thread.

* `--timeout n` waits n seconds for request responses. 10 seconds by
  default. Use `--timeout 0` to wait forever for the response.

Some examples:

```bash
# check all the reachable internal links, ignoring external links
# (e.g. check that all the links a static blog generator creates are ok)
404.py url --internal follow --external ignore

# check all the external links in a single page:
404.py url --internal ignore --external check

# wait forever for an url to be available:
404.py url --internal ignore --external ignore --timeout 0

# get all the links in a site and dump them to a txt (without status code)
# (errors and statistics on stderr)
404.py url --internal follow --print-all | awk '{ print $2 }' > links.txt
```

## Portability

Status codes/links are written to stdout, using UTF-8 and the newline
format specified by `--newline`.

Network or HTML parsing errors and statistics and written to stderr using
the current platform newline format.

The exit status is 0 on success and 1 on errors. After an error,
404 skips the current url and proceeds with the next one instead of aborting.
It can be interrupted with control + c.

Note that a link returning a 404 status code (or any 4xx or 5xx status) is
NOT an error. Only being unable to get a status code at all due to network
problems or invalid input is considered an error.

404 is tested on Windows 7 and 8 and on Debian (both x86 and x86-64)
using Python 3.4+, beautifulsoup4 4.3.2+ and requests 2.6.2+. Older versions
are not supported.

## Status

This program is finished!

404 is feature-complete and has no known bugs. Unless issues are reported
I plan no further development on it other than maintenance.

## License

Like all my hobby projects, this is Free Software. See the [Documentation][]
folder for more information. No warranty though.

[Documentation]: Documentation

