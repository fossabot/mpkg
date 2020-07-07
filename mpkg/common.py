#!/usr/bin/env python3
# coding: utf-8

import gettext
import json
from typing import List, Tuple

from .config import GetConfig, SetConfig
from .utils import Download, Selected

DefaultList = [-1, -1, -1]
DefaultLog = ''

_ = gettext.gettext


class Soft(object):
    id = 'Soft'
    allowExtract = False
    isPrepared = False
    needConfig = False
    DefaultList = [-1, -1, -1]
    DefaultLog = ''

    def __init__(self, name='', rem=''):
        name_ = self.getconfig('name')
        rem_ = self.getconfig('rem')
        if name:
            self.name = name
        elif name_:
            self.name = name_
        else:
            self.name = self.id
        if rem:
            self.rem = rem
        else:
            self.rem = rem_

    def _parse(self) -> Tuple[List[int], List[int], List[str], str]:
        return self.DefaultList, self.DefaultList, ['url'], self.DefaultLog

    def config(self):
        print(_('\n configuring {0} (press enter to pass)').format(self.id))
        self.setconfig('name')
        self.setconfig('rem')

    def setconfig(self, key, value=False):
        if value == False:
            value = input(_('input {key}: '.format(key=key)))
        SetConfig(key, value, path=self.id)

    def getconfig(self, key):
        return GetConfig(key, path=self.id)

    def json(self) -> bytes:
        if not self.isPrepared:
            self.prepare()
        return json.dumps(self.data).encode('utf-8')

    def download(self):
        # -v print(_('使用缺省下载方案'))
        if len(self.links) != 1:
            link = Selected(self.links, msg=_('select a url:'))[0]
        else:
            link = self.links[0]
        Download(link)

    def prepare(self):
        self.isPrepared = True
        self.ver, self.date, self.links, self.log = self._parse()
        data = {}
        data['id'] = self.id
        data['ver'] = self.ver
        data['links'] = self.links
        if self.date != self.DefaultList:
            data['date'] = self.date
        if self.rem:
            data['rem'] = self.rem
        if self.log:
            data['changelog'] = self.log
        self.data = data


class Driver(Soft):
    needConfig = True

    def __init__(self, url: str, name='', rem=''):
        super().__init__(name, rem=rem)
        self.url = url
