#!/usr/bin/env python3
# coding: utf-8

import gettext
import importlib
import json
import os
import shutil
import time
from multiprocessing.dummy import Pool
from pathlib import Path
from zipfile import ZipFile

from .config import HOME, GetConfig, SetConfig
from .utils import Download, GetPage, Name, ReplaceDir

_ = gettext.gettext


def LoadFile(path: str):
    spec = importlib.util.spec_from_file_location('Package', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Package()


def Configurate(path: str):
    pkg = LoadFile(path)
    if pkg.isMultiple:
        i = int(
            input(_('\ninput the number of profiles for {pkgname}: ').format(pkgname=pkg.ID)))
        pkg.setconfig('i', i)
        for i in range(i):
            newpkg = LoadFile(path)
            newpkg.cfg += f'.{i}'
            newpkg.config()
    else:
        pkg.config()


def Save(source: str, ver=-1, sync=True, check_ver=True):
    latest = False  # old source is not latest
    name = ''
    if '->' in source:
        source, name = source.split('->')

    def download(url, name, verattr, filetype, sync, check_ver):
        latest = False
        filename = url.split('/')[-1] if not name else name
        abspath = HOME / filetype
        filepath = HOME / filetype / filename
        if sync:
            if not check_ver:
                Download(url, directory=abspath, filename=filename)
                return filepath, latest
            if verattr == -1:
                res = GetPage(url + '.ver', warn=False).replace(' ', '')
                ver = -1 if not res.isnumeric() else int(res)
            else:
                ver = verattr
            ver_ = GetConfig(filename, filename=filename +
                             '.ver.json', abspath=abspath)
            ver_ = -1 if not ver_ else int(ver_)
            if ver == -1 or ver > ver_:
                Download(url, directory=abspath, filename=filename)
                SetConfig(filename, ver, filename=filename +
                          '.ver.json', abspath=abspath)
            else:
                latest = True
        return filepath, latest

    if source.startswith('http'):
        if source.endswith('.py'):
            filepath, latest = download(
                source, name, ver, 'py', sync, check_ver)
        elif source.endswith('.json'):
            filepath, latest = download(
                source, name, ver, 'json', sync, check_ver)
        elif source.endswith('.zip'):
            filepath, latest = download(
                source, name, ver, 'zip', sync, check_ver)
    else:
        filepath = source
    return filepath, latest


def LoadZip(filepath, latest=False, installed=True):
    filepath = Path(filepath)
    dir = filepath.parent / filepath.name[:-4]
    pkgdir = dir / 'packages'
    if not latest:
        if pkgdir.exists():
            shutil.rmtree(pkgdir)
        with ZipFile(filepath, 'r') as myzip:
            files = [name for name in myzip.namelist() if 'packages/' in name]
            myzip.extractall(path=str(dir), members=files)
        ReplaceDir(str(dir / files[0]), str(pkgdir))
    files = [str((pkgdir/file).absolute()) for file in os.listdir(pkgdir)
             if file.endswith('.py') or file.endswith('.json')]
    return [Load(file, installed=installed) for file in files]


def Load(source: str, ver=-1, installed=True, sync=True, jobs=10):
    if GetConfig('debug') == 'yes':
        print(f'debug: loading {source}')
    if not source.endswith('.json') and not GetConfig('unsafe') == 'yes':
        return [], '.json'
    if not installed:
        sync = True
    if source.endswith('.py'):
        filepath = Save(source, ver, sync)[0]
        pkg = LoadFile(filepath)
        if pkg.needConfig and not installed:
            Configurate(filepath)
        if pkg.isMultiple:
            pkgs = []
            if not pkg.getconfig('i'):
                return [pkg], '.py'
            for i in range(pkg.getconfig('i')):
                newpkg = LoadFile(filepath)
                newpkg.cfg += f'.{i}'
                newpkg.__init__()
                pkgs.append(newpkg)
        else:
            pkgs = [pkg]
        return pkgs, '.py'
    elif source.endswith('.json'):
        filepath = Save(source, ver, sync)[0]
        with open(filepath, 'r', encoding="utf8") as f:
            return json.load(f)['packages'], '.json'
    elif source.endswith('.zip'):
        filepath, latest = Save(source, ver, sync)
        return LoadZip(filepath, latest, installed), '.zip'
    elif source.endswith('.sources'):
        if source.startswith('http'):
            sources = json.loads(GetPage(source))
        else:
            with open(source, 'r', encoding="utf8") as f:
                sources = json.load(f)
        parser = [key for key, value in sources.items() if value == 'parser']
        for url in parser:
            del sources[url]
            Load(url, installed=installed, sync=sync)
        with Pool(jobs) as p:
            score = [x for x in p.map(lambda x: Load(
                x[0], x[1], installed, sync), sources.items()) if x]
        return score, '.sources'


def HasConflict(softs, pkgs) -> list:
    ids = []
    for item in pkgs:
        if item.isMultiple and item.ID in ids:
            pass
        else:
            ids.append(item.ID)
    [ids.append(item['id']) for item in softs]
    return [id for id in ids if ids.count(id) > 1]


def Sorted(items):
    softs, pkgs, sources = [], [], []
    a, b, c, d = [], [], [], []
    for x, ext in items:
        if ext == '.json':
            a.append(x)
        elif ext == '.py':
            b.append(x)
        elif ext == '.sources':
            c.append(x)
        elif ext == '.zip':
            d.append(x)
    # a=[[soft1, soft2]]
    # b=[[pkg1, pkg2]]
    # c=[[(x1,ext),(x2,ext)]], x1=a/b/d[0]
    # d=[[(x1,ext),(x2,ext)]], x1=a/b[0]
    for L in c:
        sources += L
    for x, ext in sources:
        if ext == '.json':
            a.append(x)
        elif ext == '.py':
            b.append(x)
        elif ext == '.zip':
            d.append(x)
    for x in d:
        for y, ext in x:
            if ext == '.json':
                a.append(y)
            elif ext == '.py':
                b.append(y)
    for softlist in a:
        softs += softlist
    for pkglist in b:
        pkgs += pkglist
    pkgs = [pkg for pkg in pkgs if pkg.ID]
    return softs, pkgs


def ConfigSoft(soft):
    with Pool(10) as p:
        items = [x for x in p.map(Load, GetConfig('sources')) if x]
    pkgs = Sorted(items)[1]
    pkg = [pkg for pkg in pkgs if pkg.name == soft['name']]
    if pkg:
        pkg[0].config()


def Prepare(pkg):
    try:
        pkg.prepare()
        if not hasattr(pkg, 'data') or 'packages' not in pkg.data:
            print(f'warning({pkg.ID}): no data')
            return pkg
    except Exception as err:
        print(f'error({pkg.ID}): {err}')
        return pkg


def GetSofts(jobs=10, sync=True, use_cache=True) -> list:
    softs_ = GetConfig('softs', filename='softs.json')
    if softs_ and use_cache:
        return softs_

    with Pool(jobs) as p:
        items = [x for x in p.map(lambda x:Load(
            x, sync=sync, jobs=jobs), GetConfig('sources')) if x]
    softs, pkgs = Sorted(items)

    score = HasConflict(softs, pkgs)
    if score:
        print(f'warning(id conflict): {set(score)}')

    with Pool(jobs) as p:
        err = [result for result in p.map(Prepare, pkgs) if result]
    for soft in [pkg.data['packages'] for pkg in pkgs if pkg not in err]:
        softs += soft

    Name(softs)
    if not softs == softs_:
        SetConfig('softs', softs, filename='softs.json')

    return softs


def GetOutdated():
    installed = GetConfig(filename='installed.json')
    latest = {}
    for soft in GetSofts():
        latest[soft['name']] = [soft['ver'], soft.get('date')]
    outdated = {}
    for name, value in installed.items():
        if not name in latest:
            print('warning: cannot find '+name)
            continue
        date = latest[name][1]
        if date:
            date = time.strftime(
                '%y%m%d', time.strptime(date, '%Y-%m-%d'))
        else:
            date = ''
        if value[0] != latest[name][0]:
            outdated[name] = [date, value[0], latest[name][0]]
        elif latest[name][1] and value[1] != latest[name][1]:
            outdated[name] = [date, value[0], latest[name][0]]
    return outdated


def Names2Softs(names: list, softs=False):
    names = [name.lower() for name in names]
    if not softs:
        softs_all = GetSofts()
    return [soft for soft in softs_all if soft['name'].lower() in names]
