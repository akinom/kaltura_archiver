from KalturaClient import *
from KalturaClient.Plugins.Core import *

from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
import logging

__client__ = None

def getClient():
    global __client__;
    return __client__;

def startsession(partner_id, user_id, secret):
    """ Use configuration to generate KS
    """
    global __client__
    config = KalturaConfiguration(partner_id)
    config.serviceUrl = "https://www.kaltura.com/"
    client = KalturaClient(config)
    ktype = KalturaSessionType.ADMIN
    expiry = 432000 # 432000 = 5 days
    privileges = "disableentitlement"

    ks = client.session.start(secret, user_id, ktype, partner_id, expiry, privileges)
    client.setKs(ks)
    logging.info("Kaltura/Api: connected to %s with %s partnerId:%s" % (config.serviceUrl, user_id, partner_id))
    __client__ = client
    return None

from KalturaClient import *
from KalturaClient.Plugins.Core import *

class Filter:
    def __init__(self, mediaType=KalturaMediaType.VIDEO):
        self.filter = KalturaMediaEntryFilter()
        self.filter.mediaTypeEqual = mediaType
        self.filter.orderBy = "+createdAt"  # Oldest first

    def tag(self, tag):
        if (tag != None):
            self.filter.tagLike = "!" + tag
            logging.debug("Filter.tag=%s" % self.filter.tagLike )
        else:
            logging.debug("Filter.tag: NOOP ")
        return self

    def category(self, categoryId):
        if (categoryId != None):
            self.filter.categoryAncestorIdIn = categoryId
            logging.debug("Filter.tag=%s" % self.filter.categoryAncestorIdIn.to_s )
        else:
            logging.debug("Filter.category: NOOP")
        return self

    def undefined_LAST_PLAYED_AT(self):
        if (self.filter.advancedSearch != NotImplemented):
            raise RuntimeError("undefined_LAST_PLAYED_AT: filter.advancedSearch already defined")
            logging.debug("Filter.undefined_LAST_PLAYED_AT" )
            return self.years_since_played(20)

    def years_since_played(self, years):
        if years is not None:
            if (self.filter.advancedSearch != NotImplemented):
                raise RuntimeError("years_since_played: filter.advancedSearch already defined")
            self.filter.advancedSearch = KalturaMediaEntryCompareAttributeCondition()
            self.filter.advancedSearch.attribute = KalturaMediaEntryCompareAttribute.LAST_PLAYED_AT
            self.filter.advancedSearch.comparison = KalturaSearchConditionComparison.LESS_THAN
            d = datetime.now() - relativedelta(years=years)
            timestamp = calendar.timegm(d.utctimetuple())
            self.filter.advancedSearch.value = timestamp
            logging.debug("Filter.LAST_PLAYED_AT LESS_THAN {:%d, %b %Y}".format(d) )
        else:
            logging.debug("Filter.yearsSincePlayed: NOOP")
        return self

    def __iter__(self):
        return FilterIter(self)

    def __str__(self):
        s = "Filter("
        if hasattr(self.filter, 'tagLike'):
            s = s + "tag=%s" % self.filter.tagLike
        if hasattr(self.filter, 'categoryAncestorIdIn') and self.filter.categoryAncestorIdIn != NotImplemented:
            s = s + "category=%s" % self.filter.categoryAncestorIdIn
        if hasattr(self.filter, 'advancedSearch') and  self.filter.advancedSearch != NotImplemented:
            s = s + "search: %s %s %s" % \
                ( self.filter.advancedSearch.attribute, self.filter.advancedSearch.comparison, str(self.filter.advancedSearch.value) )
        return s + ')'

class FilterIter:
    PAGER_CHUNK = 10

    def __init__(self, filter):
        self.filter = filter
        self.pager = KalturaFilterPager()
        self.pager.pageSize = FilterIter.PAGER_CHUNK
        self.pager.pageIndex = 0
        self.objects = iter([])

    def next(self):
        try:
            n = next(self.objects)
            return n;
        except StopIteration as stp:
            self.pager.setPageIndex(self.pager.getPageIndex() + 1)
            self.objects = iter(getClient().media.list(self.filter.filter, self.pager).objects)
            logging.debug("%s: iter page %d" % (self, self.pager.getPageIndex()))
            return next(self.objects)

class MediaEntry:

    @staticmethod
    def props(i, keys=['id', 'views', 'lastPlayedAt','tags', 'categoriesIds', 'categories']):
        hsh = vars(i)
        return {  k : hsh[k] for k in keys }
