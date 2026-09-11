"""Export the agent catalogue for the board's Agent catalogue tab: one document, out/catalogue/index.json,
listing every agent and skill in the agent-catalog marketplace.

    python exporters/export_catalogue.py [out_dir]

Reads, and never writes, two places named by the "catalogue" block of board.config.json:
- marketplacePath, the marketplace clone: plugins/<plugin>/agents/<name>.md and
  plugins/<plugin>/skills/<name>/SKILL.md (frontmatter name and description), and each plugin's
  .claude-plugin/plugin.json (its description gives the plugin's one-line purpose);
- installedPath, the installed-plugins file, whose "<plugin>@agent-catalog" keys say which plugins are
  installed.

Each entry carries its kind, plugin, name, description and installed flag. Usage is not stored here: the
page derives it from the runs and sessions documents, so this document changes only when the catalogue does.

Only a catalogue config value of the wrong type exits non-zero (exit 2). Every other problem is a warning on
stderr: an unreadable or malformed agent or skill file is left out, as are the entries of an agents or skills
folder that cannot be listed; a malformed manifest makes the plugin's name its purpose; an unusable
installed-plugins file marks every entry not installed. A missing marketplace, a missing or unlistable plugins/
folder, or no agents and no skills at all keeps the previous out/catalogue/index.json untouched, so a moved
clone cannot blank the tab.

Frontmatter and purpose parsing live in derive.py; this module reads the files and writes the document.
"""
import fnmatch, io, json, os, re, sys
from datetime import datetime, timezone

import board_config
import derive
from derive import PURPOSE_MAX, purpose  # noqa: F401  (part of this module's interface)
from export_sessions import write_json

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(HERE, 'board.config.json')
MARKETPLACE = 'agent-catalog'  # installed-plugins keys are "<plugin>@<marketplace>"
# Entry ids are matched against transcript ids and rendered on the page, so they are kept to a safe set.
ID = re.compile(r'^[A-Za-z0-9_.:-]{1,100}$')


def warn(msg):
    print('export_catalogue: ' + msg, file=sys.stderr)


def frontmatter(path):
    """The single-line "key: value" pairs between the first two lines that are "---". Raises OSError or
    ValueError (UnicodeDecodeError included) for a file that cannot be read or has no frontmatter."""
    # Text mode reads CRLF as LF; utf-8-sig drops a byte-order mark.
    with io.open(path, encoding='utf-8-sig') as f:
        text = f.read()
    return derive.frontmatter(text, path, warn)


def manifest_description(plugin_dir, plugin):
    """The description in a plugin's .claude-plugin/plugin.json, or None without a readable manifest."""
    path = os.path.join(plugin_dir, '.claude-plugin', 'plugin.json')
    if not os.path.isfile(path):
        return None
    try:
        with io.open(path, encoding='utf-8-sig') as f:
            data = json.load(f)
    except (OSError, ValueError, RecursionError) as e:  # deeply nested JSON is valid but exhausts the decoder's stack
        warn('plugin %s: manifest could not be read (%s: %s); its purpose is its name' % (plugin, type(e).__name__, e))
        return None
    if not isinstance(data, dict):
        warn('plugin %s: manifest is not a JSON object; its purpose is its name' % plugin)
        return None
    return data.get('description')


def installed_plugins(path):
    """The agent-catalog plugins the installed-plugins file lists; none, with a warning, when the file is
    missing, unreadable or not in its expected shape."""
    try:
        with io.open(path, encoding='utf-8-sig') as f:
            data = json.load(f)
    except (OSError, ValueError, RecursionError) as e:  # deeply nested JSON is valid but exhausts the decoder's stack
        warn('installed-plugins file %s could not be read (%s); every entry is marked not installed' % (path, type(e).__name__))
        return set()
    plugins = data.get('plugins') if isinstance(data, dict) else None
    if not isinstance(plugins, dict):
        warn('installed-plugins file %s has no "plugins" object; every entry is marked not installed' % path)
        return set()
    suffix = '@' + MARKETPLACE
    return {k[:-len(suffix)] for k in plugins if isinstance(k, str) and k.endswith(suffix)}


def listing(folder):
    """The names in a folder, sorted, leaving out names that start with "."; none when it does not exist, and
    none with a warning when it cannot be listed. glob is not used, because it skips an unlistable folder
    without a word."""
    if not os.path.isdir(folder):
        return []
    try:
        return sorted(n for n in os.listdir(folder) if not n.startswith('.'))
    except OSError as e:
        warn('%s could not be listed (%s: %s); its entries are left out' % (folder, type(e).__name__, e))
        return []


def read_entry(path, plugin, kind, fallback):
    """One catalogue entry from an agent or skill file, or None (with a warning) when it cannot be used.
    fallback is the name to use when the frontmatter has none: the file name for agents, the folder for skills."""
    try:
        fm = frontmatter(path)
    except (OSError, ValueError) as e:
        warn('%s skipped (%s: %s)' % (path, type(e).__name__, e))
        return None
    name = fm.get('name') or fallback
    eid = '%s:%s' % (plugin, name)
    if not ID.match(eid):
        warn('%s skipped: id %r is not letters, digits, "_", ".", ":" and "-"' % (path, eid[:120]))
        return None
    return {'id': eid, 'kind': kind, 'plugin': plugin, 'name': name, 'description': fm.get('description', '')}


def main(config=None, out_dir=None, now=None):
    """Export the catalogue into out_dir (default out/); returns the process exit code."""
    if config is None:
        with io.open(CONFIG, encoding='utf-8') as f:
            config = json.load(f)
    try:
        paths = board_config.catalogue(config)
    except ValueError as e:
        print('export_catalogue: %s; nothing exported' % e, file=sys.stderr)
        return 2
    out = out_dir or os.path.join(HERE, 'out')
    target = os.path.join(out, 'catalogue', 'index.json')
    market, root = paths['marketplacePath'], os.path.join(paths['marketplacePath'], 'plugins')

    if not os.path.isdir(market):
        warn('marketplace %s does not exist; keeping the last catalogue export' % market)
        return 0
    if not os.path.isdir(root):
        warn('marketplace %s has no plugins folder; keeping the last catalogue export' % market)
        return 0
    installed = installed_plugins(paths['installedPath'])
    try:
        names = sorted(os.listdir(root))
    except OSError as e:
        warn('plugins folder %s could not be listed (%s: %s); keeping the last catalogue export' % (root, type(e).__name__, e))
        return 0
    entries, plugins = [], []
    for plugin in names:
        pdir = os.path.join(root, plugin)
        if not os.path.isdir(pdir):
            continue
        found = []
        adir, sdir = os.path.join(pdir, 'agents'), os.path.join(pdir, 'skills')
        for name in listing(adir):
            if fnmatch.fnmatch(name, '*.md'):  # case-insensitive on Windows, as the file system is
                found.append(read_entry(os.path.join(adir, name), plugin, 'agent', name[:-len('.md')]))
        for name in listing(sdir):
            path = os.path.join(sdir, name, 'SKILL.md')
            if os.path.lexists(path):
                found.append(read_entry(path, plugin, 'skill', name))
        found = sorted((e for e in found if e), key=lambda e: (e['kind'] != 'agent', e['name']))
        if not found:
            continue
        on = plugin in installed
        for e in found:
            e['installed'] = on
        desc = manifest_description(pdir, plugin)
        plugins.append({'plugin': plugin, 'purpose': purpose(desc, plugin),
                        'purposeFull': desc.strip() if isinstance(desc, str) else '', 'installed': on,
                        'agents': sum(e['kind'] == 'agent' for e in found), 'skills': sum(e['kind'] == 'skill' for e in found)})
        entries += found
    if not entries:
        warn('found no agents or skills under %s; keeping the last catalogue export' % root)
        return 0

    os.makedirs(os.path.dirname(target), exist_ok=True)
    write_json(target, {'generatedAt': now or datetime.now(timezone.utc).isoformat(timespec='seconds'),
                        'source': {'marketplacePath': market, 'installedPath': paths['installedPath']},
                        'plugins': plugins, 'entries': entries})
    print('wrote the agent catalogue: %d agents and %d skills in %d plugins' % (
        sum(e['kind'] == 'agent' for e in entries), sum(e['kind'] == 'skill' for e in entries), len(plugins)))
    return 0


if __name__ == '__main__':
    sys.exit(main(out_dir=sys.argv[1] if len(sys.argv) > 1 else None))
