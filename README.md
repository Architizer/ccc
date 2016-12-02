Common Crawl Catalog
====================

Tool to grab pages per domain and index into solr


To build common crawl lookup index

```
bash install.sh CC-MAIN-2016-40
```

To index domain to a solr

```
SOLR_URL=http://solrhost:port bin/ccc index-domain duravit.com
```



# Credits
Some install borrowed from https://github.com/Referly/cdx-server

