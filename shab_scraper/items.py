# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html


from scrapy.item import Item, Field


class PersonProfileItem(Item):
    company_name = Field()
    UID = Field()
    legal_form = Field()
    also_view = Field()
    education = Field()
    locality = Field()
    industry = Field()
    summary = Field()
    specilities = Field()
    skills = Field()
    interests = Field()
    group = Field()
    honors = Field()
    education = Field()
    experience = Field()
    overview_html = Field()
    homepage = Field()
