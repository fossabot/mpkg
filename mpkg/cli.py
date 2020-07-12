#!/usr/bin/env python3
# coding: utf-8

import gettext
import os
import shutil
from platform import architecture
from pprint import pformat, pprint

import click

from .common import Soft
from .config import HOME, GetConfig, SetConfig
from .load import ConfigSoft, GetSofts, Load, Names2Softs
from .utils import Download, GetOutdated, PreInstall, Selected, ToLink

_ = gettext.gettext
arch = architecture()[0]


@click.group(context_settings=dict(help_option_names=['-h', '--help']))
def cli():
    pass


@cli.command()
@click.option('-j', '--jobs', default=10, help=_('threads'))
@click.option('--sync/--no-sync', default=True, help=_('sync source files'))
def sync(jobs, sync):
    softs = GetSofts(jobs, sync, use_cache=False)
    names = [soft['name'] for soft in softs]
    outdated = sorted(list(GetOutdated().items()),
                      key=lambda x: x[1][0], reverse=True)
    if len(outdated) == 0:
        print(_('Already up to date.'))
    else:
        for name, value in outdated:
            soft = softs[names.index(name)]
            print()
            if value[0]:
                print(f'{name}|{value[0]}\t{value[1]}->{value[2]}')
            else:
                print(f'{name}\t{value[1]}->{value[2]}')
            if soft.get('rem'):
                print(f' rem: {soft["rem"]}')
            if soft.get('changelog'):
                print(f' changelog: {soft["changelog"]}')


@cli.command()
@click.argument('packages', nargs=-1)
@click.option('-f', '--force', is_flag=True)
@click.option('--load/--no-load', default=True)
@click.option('--delete-all', is_flag=True)
@click.option('--re-redirect', is_flag=True)
def config(packages, force, load, delete_all, re_redirect):
    if packages:
        for soft in Names2Softs(packages):
            ConfigSoft(soft)
        return
    if re_redirect:
        rules = []
        while True:
            r = input(_('\n input pattern(press enter to pass): '))
            if r:
                rules.append({r: input(_(' redirect to: '))})
            else:
                SetConfig('redirect', rules)
                return
    if not force and GetConfig('sources'):
        print(_('pass'))
    elif delete_all:
        shutil.rmtree(HOME)
    else:
        PreInstall()
        sources = []
        while True:
            s = input(_('\n input sources(press enter to pass): '))
            if s:
                sources.append(s)
                if load:
                    Load(s, installed=False)
            else:
                break
        SetConfig('sources', sources)


@cli.command('set')
@click.argument('key')
@click.argument('values', nargs=-1)
@click.option('islist', '--list', is_flag=True)
@click.option('--prepare', is_flag=True)
@click.option('--add', is_flag=True)
@click.option('--delete', is_flag=True)
@click.option('--test', is_flag=True)
def set_(key, values, islist, prepare, add, test, delete):
    if prepare:
        PreInstall()
    if add:
        islist = True
        values = GetConfig(key)+list(values)
    if len(values) > 1 or islist:
        value = list(values)
    elif len(values) == 1:
        value = values[0]
    else:
        value = ''
    print('set {key}={value}'.format(key=key, value=value))
    if not test:
        SetConfig(key, value, delete=delete)


@cli.command()
@click.argument('packages', nargs=-1, required=True)
def download(packages):
    softs = Names2Softs(packages)
    for soft in softs:
        if not soft.get('link'):
            soft['link'] = ToLink(soft['links'])
        elif not arch in soft['link']:
            print('warning: no link available')
    for soft in softs:
        Download(soft['link'][arch])


@cli.command()
@click.argument('packages', nargs=-1)
@click.option('-d', '--download', is_flag=True)
@click.option('-o', '--outdated', is_flag=True)
@click.option('--dry-run', is_flag=True)
def install(packages, download, outdated, dry_run):
    if packages:
        softs = Names2Softs(packages)
    elif outdated:
        softs = Names2Softs(list(GetOutdated().keys()))
    else:
        print(install.get_help(click.core.Context(install)))
        return
    for soft in softs:
        if not soft.get('link') and not dry_run:
            soft['link'] = ToLink(soft['links'])
        elif not arch in soft['link']:
            print('warning: no link available')
        if not soft.get('date'):
            soft['date'] = Soft.DefaultList
        if not soft.get('args'):
            soft['args'] = Soft.SilentArgs
    for soft in softs:
        SetConfig(soft['name'], [soft['ver'], soft['date']],
                  filename='installed.json')
        if dry_run:
            return
        file = Download(soft['link'][arch])
        command = str(file)+' '+soft['args']
        if download:
            if os.name == 'nt':
                script = file.parent / 'install.bat'
                os.system(f'echo {command} >> {script}')
        else:
            os.system(command)


@cli.command()
@click.argument('packages', nargs=-1)
def remove(packages):
    packages = [pkg.lower() for pkg in packages]
    if packages:
        pkgs = GetConfig(filename='installed.json')
        names = [x for x in list(pkgs.keys()) if x.lower() in packages]
        for name in names:
            SetConfig(name, filename='installed.json', delete=True)
    else:
        print(remove.get_help(click.core.Context(remove)))
        return


@cli.command('list')
@click.argument('packages', nargs=-1)
@click.option('-o', '--outdated', is_flag=True)
@click.option('-i', '--installed', is_flag=True)
def list_(packages, outdated, installed):
    if installed:
        pkgs = GetConfig(filename='installed.json')
        pprint(list(pkgs.keys()))
    elif outdated:
        pprint(list(GetOutdated().keys()))
    elif packages:
        pprint(Names2Softs(packages))
    else:
        pprint([x['name'] for x in GetSofts()])


if __name__ == "__main__":
    cli()
