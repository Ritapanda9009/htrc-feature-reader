from __future__ import unicode_literals
from htrc_features.page import Page, Section
from htrc_features.term_index import TermIndex
from six import iteritems
import logging
try:
    import pysolr
except ImportError:
    logging.info("Pysolr not installed.")

class Volume(object):
    SUPPORTED_SCHEMA = '1.0'
    _metadata = None

    def __init__(self, obj):
        # Verify schema version
        if obj['features']['schemaVersion'] != self.SUPPORTED_SCHEMA:
            logging.warn('Schema version of imported (%s) file does not match '
            'the supported version (%s)' % (obj['features']['schemaVersion'],
                                            self.SUPPORTED_SCHEMA) )
        self.id = obj['id']
        self._pages = obj['features']['pages']
        self.pageCount = obj['features']['pageCount']

        # Expand metadata to attributes
        for (key, value) in obj['metadata'].items():
            setattr(self, key, value)
        
        if hasattr(self, 'genre'):
            self.genre = self.genre.split(", ") 

        self.pageindex = 0
    
    def __iter__(self):
        return self
    
    def next(self):
        return self.__next__()

    def __next__(self):
        return next(self.pages())
    
    @property
    def year(self):
        ''' A friendlier name wrapping Volume.pubDate '''
        return self.pubDate

    @property
    def metadata(self):
        if not pysolr:
            logging.error("Cannot retrieve metadata. Pysolr not installed.")
        if not self._metadata:
            logging.debug("Looking up full metadata for {0}".format(self.id))
            solr = pysolr.Solr('http://sandbox.htrc.illinois.edu/solr/meta', timeout=10)
            results = solr.search('id:"{0}"'.format(self.id))
            if len(results) != 1:
                logging.error("Unexpected: there were {0} results for {1} instead of 1.".format(len(results), self.id))
            result = list(results)[0]
            self._metadata = result
        return self._metadata


    def _parseFeatures(self, featobj):
        rawpages = featobj['pages']

    def pages(self, **kwargs):
        for page in self._pages:
            yield Page(page, self, **kwargs)

    def tokens_per_page(self, **kwargs):
        l = [0] * self.pageCount
        for (index, page) in enumerate(self.pages(**kwargs)):
            try:
                l[index] = page.total_tokens()
            except:
                logging.error("Seq and pageCount don't match in %s" % self.id)
        return l

    def term_page_freqs(self, page_freq=True, case=True):
        return self._frequencies(page_freq, case)

    def term_volume_freqs(self, page_freq=True, case=True):
        tp = self._frequencies(page_freq, case)
        for (token, l) in iteritems(tp):
            tp[token] = sum(l)
        return tp

    def end_line_chars(self, **args):
        return self._line_chars('endLineChars')

    def begin_line_chars(self, **args):
        return self._line_chars('beginLineChars')

    def _line_chars(self, attr, sec='body'):
        '''attr=[endLineChars|startLineChars]'''
        cp = TermIndex(self.pageCount)
        for (index, page) in enumerate(self.pages()):
            section =getattr(page, sec)
            for (char, count) in iteritems(getattr(section, attr)):
                cp[char][index] = count
        return cp

    def _frequencies(self, page_freq=True, case=False):
        ''' Build term-page frequency list.

        page_freq[bool] : Whether to count page frequency(if the term occurs in the page or not)
                          or a full frequency.
        '''
        ti = TermIndex(self.pageCount)
        for (index, page) in enumerate(self.pages()):
            for (token, count) in iteritems(page.tokenlist.token_counts(case=case, pos=False)):
                if page_freq:
                    ti[token][index] = 1
                else:
                    ti[token][index] = count
        return ti
    

    def __str__(self):
        return "<HTRC Volume: %s>" % self.id
