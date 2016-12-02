Common Crawl Catalog
====================

Tool to grab pages per domain and index into solr


To install local index for common crawl lookup index

```
bin/ccc install CC-MAIN-2016-40
```

To index domain to a solr

```
SOLR_URL=http://solrhost:port bin/ccc index-domain architizer.com
```



# Credits
Some install borrowed from https://github.com/Referly/cdx-server

