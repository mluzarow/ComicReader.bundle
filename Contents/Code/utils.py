import os
import re
import archives
from db import DATABASE

IMAGE_FORMATS = ['.jpg', '.png', '.png', '.gif', '.tiff', '.bmp']
SUPPORT_PATH = os.path.join(Core.bundle_path.split('Plug-ins')[0], 'Plug-in Support', 'Data', Plugin.Identifier)
PAGE_NUM_REGEX = re.compile(r'([0-9]+)([a-zA-Z])?\.')


def mime_type(filename):
    ext = os.path.splitext(filename)[-1]
    return {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.tiff': 'image/tiff',
        '.bmp': 'image/bmp'
    }.get(ext, '*/*')


class State(object):
    READ = 0
    UNREAD = 1
    IN_PROGRESS = 2


def get_image(archive, filename, user):
    """Return the contents of `filename` from within `archive`. also do some other stuff."""
    a = archives.get_archive(archive)

    x, total_pages = DATABASE.get_state(user, archive)

    m = PAGE_NUM_REGEX.search(filename)
    cur_page = int(m.group(1)) if m else 0
    Log.Info('{}: <{}> ({}/{})'.format(user, os.path.basename(archive), cur_page, total_pages))

    if cur_page > 0:
        DATABASE.set_state(user, archive, cur_page)

    return DataObject(a.read(filename), mime_type(filename))


def get_thumb(archive, filename):
    """Return the contents of `filename` from within `archive`."""
    a = archives.get_archive(archive)
    return DataObject(a.read(filename), mime_type(filename))


def get_cover(archive):
    """Return the contents of the first file in `archive`."""
    a = archives.get_archive(archive)
    x = sorted([x for x in a.namelist() if os.path.splitext(x)[-1] in IMAGE_FORMATS])
    if x:
        return DataObject(a.read(x[0]), mime_type(x[0]))


def thumb_transcode(url, w=150, h=150):
    """use the PMS photo transcoder for thumbnails"""
    return '/photo/:/transcode?url={}&height={}&width={}&maxSize=1'.format(String.Quote(url), w, h)


def decorate_title(archive, user, state, title):
    if state == State.UNREAD:
        indicator = Prefs['unread_symbol']
    elif state == State.IN_PROGRESS:
        cur, total = DATABASE.get_state(user, archive)
        if cur <= 0 or total <= 0:
            indicator = Prefs['in_progress_symbol']
        else:
            indicator = '{} [{}/{}]'.format(Prefs['in_progress_symbol'], cur, total)
    elif state == State.READ:
        indicator = Prefs['read_symbol']
    return '{} {}'.format('' if indicator is None else indicator.strip(), title)


def decorate_directory(directory, user, title):
    if not is_series(directory):
        return title
    state = DATABASE.series_state(user, directory)
    if state == State.UNREAD:
        indicator = Prefs['unread_symbol']
    elif state == State.IN_PROGRESS:
        indicator = Prefs['in_progress_symbol']
    elif state == State.READ:
        indicator = Prefs['read_symbol']
    return '{} {}'.format('' if indicator is None else indicator.strip(), title)


def filtered_listdir(directory):
    """Return a list of only directories and compatible format files in `directory`"""
    dirs, comics = [], []
    for x in sorted_nicely(os.listdir(directory)):
        if os.path.isdir(os.path.join(directory, x)):
            l = dirs if bool(Prefs['dirs_first']) else comics
            l.append((x, True))
        elif os.path.splitext(x)[-1] in archives.FORMATS:
            comics.append((x, False))
    return dirs + comics


def sorted_nicely(l):
    """sort file names as you would expect them to be sorted"""
    def alphanum_key(key):
        return [int(c) if c.isdigit() else c for c in re.split('([0-9]+)', key.lower())]
    return sorted(l, key=alphanum_key)


def is_series(directory):
    """determine if a directory can be considered a series"""
    try:
        for x in os.listdir(directory):
            if os.path.splitext(x)[-1] in archives.FORMATS:
                return True
    except Exception as e:
        return False
    return False