"""Build the student package: the project with no development tooling inside.

Takes the last commit (DanceWorkshop.toe and the test media), then in a copy:
- removes the Embody COMP, its externalizations table and annotation, and the
  in-TouchDesigner tests (tests, test_t01 and their annotation);
- strips what Embody leaves on the operators that stay: tags, storage entries,
  the About page (Build Number, Build Date, Touch Build) and the links from
  DATs to their .py/.glsl/.tsv files (the text stays inside the .toe);
- points transport's Audio File and MIDI File at the test media;
- rewords the two code comments that mention the tooling;
then checks nothing is left (expanding the result again) and zips it with a
README made from the main one.

The .toe is edited in TouchDesigner's text form (toeexpand / toecollapse), so
the master project is never opened or changed. Nothing in the repository is
modified; the zip goes to dist/ (git ignores it).

Run from the repository root:
  python tools/make_student_package.py              (about 1 MB)
  python tools/make_student_package.py --mediapipe  (adds TouchDesigner/toxes/*.tox
                                                     from this computer, about 500 MB)
Output: dist/DanceWorkshop-student-<commit>.zip
"""
import glob, io, os, pickle, pickletools, re, shlex, shutil, subprocess, sys, tarfile, tempfile, zipfile

TD_BIN = r'C:\Program Files\Derivative\TouchDesigner\bin'
NAME = 'DanceWorkshop'
PATHS = ['TouchDesigner/DanceWorkshop.toe', 'media/test']
REMOVE_OPS = ['project1/Embody', 'project1/externalizations', 'project1/annotate3',   # Embody
              'project1/tests', 'project1/test_t01', 'project1/annotate2']            # tests
DEV_TAG = re.compile(r'^(tdxn(_exclude(:.*)?)?|py|glsl|tsv|TDExternalized|embody_internal)$')
DEV_KEYS = {'_tdn_rel_path'}
ABOUT_PARS = {'Build', 'Date', 'Touchbuild'}
PARM_VALUES = {   # operator .parm file -> {parameter: new value}
    'project1/transport.parm': {'Audiofile': '"../media/test/sync_test.wav"',
                                'Midifile': '"../media/test/sync_test.mid"'},
}
TEXT_EDITS = {    # DAT text -> [(old, new)]
    'project1/control/ControlExt.text': [("# Embody's build info, kept last", '# build info page, kept last')],
    'project1/inputs/pose_chop_callbacks.text': [('which TDXN would save', 'which the .toe would save')],
}
TRACE = re.compile(rb'claude|anthropic|envoy|embody|embot|tdxn|_tdn_|mwadd|dropbox', re.I)

repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git(*args):
    return subprocess.run(['git', '-C', repo, *args], check=True, capture_output=True).stdout


def read(p):
    return open(p, encoding='utf-8', errors='surrogateescape').read()


def write(p, s):
    open(p, 'w', encoding='utf-8', errors='surrogateescape', newline='\n').write(s)


def dict_keys(hexdata):
    out = io.StringIO()
    pickletools.dis(bytes.fromhex(hexdata), out)
    return [l.split("'")[1] for l in out.getvalue().splitlines() if 'UNICODE' in l and "'" in l]


def clean_dict(hexdata):
    """The storage pickle without the development keys; None when nothing is left."""
    if not set(dict_keys(hexdata)) & DEV_KEYS:
        return hexdata
    data = pickle.loads(bytes.fromhex(hexdata))   # only plain dicts of strings carry these keys
    for k in DEV_KEYS:
        data.pop(k, None)
    return pickle.dumps(data, protocol=4).hex().upper() if data else None


def remove_ops(root, toc):
    for rel in REMOVE_OPS:
        base = os.path.join(root, *rel.split('/'))
        if os.path.isdir(base):
            shutil.rmtree(base)
        for f in glob.glob(glob.escape(base) + '.*'):
            os.remove(f)
    return [l for l in toc if not any(l.startswith(r + '.') or l.startswith(r + '/') for r in REMOVE_OPS)]


def clean_n(path):
    """Tags and storage. Returns True when the operator was tracked by Embody."""
    lines, keep, tracked = read(path).split('\n'), [], False
    for line in lines:
        parts = line.split(' ')
        if parts[0] == 'tags':
            tags = parts[3:]
            tracked |= any(DEV_TAG.match(t) for t in tags)
            tags = [t for t in tags if not DEV_TAG.match(t)]
            if not tags:
                continue
            line = ' '.join(['tags', parts[1], str(len(tags))] + tags)
        elif parts[0] == 'dict':
            parts[1] = clean_dict(parts[1])
            if parts[1] is None:
                continue
            line = ' '.join(parts)
        keep.append(line)
    if keep != lines:
        write(path, '\n'.join(keep))
    return tracked


def remove_about_page(base, root, toc):
    """Embody's About page (Build Number, Build Date, Touch Build)."""
    cparm, parm = base + '.cparm', base + '.parm'
    if not os.path.exists(cparm):
        return
    lines, keep, removed = read(cparm).split('\n'), [], set()
    for line in lines:
        if line.startswith('pages '):
            pages = shlex.split(line)[2:]
            if 'About' in pages:
                pages.remove('About')
                line = ' '.join(['pages', str(len(pages))] + [shlex.quote(p) if ' ' in p else p for p in pages])
        else:
            f = line.split(' ')
            if len(f) > 2 and f[1] in ABOUT_PARS and ' About ' in line:
                removed.add(f[1])
                continue
        keep.append(line)
    if all(l in ('?', '', 'pages 0') for l in keep):
        os.remove(cparm)
        toc.remove(os.path.relpath(cparm, root).replace(os.sep, '/'))
    elif keep != lines:
        write(cparm, '\n'.join(keep))
    if removed and os.path.exists(parm):
        write(parm, '\n'.join(l for l in read(parm).split('\n') if l.split(' ')[0] not in removed))


def clean_parm(path, rel):
    """DAT links to external files, and the fixed values in PARM_VALUES."""
    lines, keep = read(path).split('\n'), []
    synced = any(re.match(r'file (0|256) project1/', l) for l in lines)
    for line in lines:
        name = line.split(' ')[0]
        if synced and (re.match(r'file (0|256) project1/', line) or line == 'syncfile 0 on'):
            continue
        if name in PARM_VALUES.get(rel, {}):
            line = '%s %s %s' % (name, line.split(' ')[1], PARM_VALUES[rel][name])
        keep.append(line)
    if keep != lines:
        write(path, '\n'.join(keep))


def edit_text(path, edits):
    """A DAT's .text file: 27-byte header ending in the text length (big-endian), then the text."""
    data = open(path, 'rb').read()
    head, text = data[:27], data[27:]
    if int.from_bytes(head[23:27], 'big') != len(text):
        sys.exit('Unexpected DAT text format: ' + path)
    for old, new in edits:
        if text.count(old.encode()) != 1:
            sys.exit('Text to replace not found in %s: %s' % (path, old))
        text = text.replace(old.encode(), new.encode())
    open(path, 'wb').write(head[:23] + len(text).to_bytes(4, 'big') + text)


def clean_tree(root, toc_path):
    toc = remove_ops(root, read(toc_path).splitlines())
    for d, _, files in os.walk(root):
        for f in files:
            p = os.path.join(d, f)
            if f.endswith('.n') and clean_n(p):
                remove_about_page(p[:-2], root, toc)
    for d, _, files in os.walk(root):
        for f in files:
            if f.endswith('.parm'):
                p = os.path.join(d, f)
                clean_parm(p, os.path.relpath(p, root).replace(os.sep, '/'))
    for rel, edits in TEXT_EDITS.items():
        edit_text(os.path.join(root, *rel.split('/')), edits)
    write(toc_path, '\n'.join(toc) + '\n')


def find_traces(root):
    hits = []
    for d, _, files in os.walk(root):
        for f in files:
            p = os.path.join(d, f)
            for m in TRACE.finditer(open(p, 'rb').read()):
                hits.append('%s: %s' % (os.path.relpath(p, root), m.group().decode()))
                break
    return hits


def run_td(exe, cwd, name):
    # toeexpand / toecollapse return 1 even when they succeed, so check the result instead
    r = subprocess.run([os.path.join(TD_BIN, exe), name], cwd=cwd, capture_output=True, text=True)
    made = os.path.join(cwd, name + '.dir') if exe == 'toeexpand.exe' else os.path.join(cwd, name[:-len('.toc')])
    if not os.path.exists(made):
        sys.exit('%s %s failed: %s %s' % (exe, name, r.stdout, r.stderr))


def clean_file(path):
    folder, name = os.path.split(path)
    run_td('toeexpand.exe', folder, name)
    clean_tree(path + '.dir', path + '.toc')
    os.remove(path)
    run_td('toecollapse.exe', folder, name + '.toc')
    shutil.rmtree(path + '.dir')
    os.remove(path + '.toc')
    # check: expand the result again and look for anything left
    run_td('toeexpand.exe', folder, name)
    hits = find_traces(path + '.dir')
    left = [r for r in REMOVE_OPS if os.path.exists(os.path.join(path + '.dir', *r.split('/')) + '.n')]
    shutil.rmtree(path + '.dir')
    os.remove(path + '.toc')
    if hits or left:
        sys.exit('Left in %s: %s %s' % (name, hits[:20], left))
    for extra in os.listdir(folder):            # toecollapse may leave a backup copy
        if extra != name and extra.startswith(os.path.splitext(name)[0]) and extra.endswith('.toe'):
            os.remove(os.path.join(folder, extra))


def student_readme():
    s = git('show', 'HEAD:README.md').decode('utf-8').replace('\r\n', '\n')
    s = s[:s.index('\n## Testing')] + '\n'
    s = re.sub(r'\n\*\*Status:\*\*[^\n]*\n', '', s)
    for old, new in [
            ('Clone or download this repository.', 'Unzip this folder.'),
            ("is too large for GitHub, so it is not in this repository.", 'is not included in this folder.'),
            ('in this repository (create the folder). Git ignores it.', 'in this folder (create it).'),
            (' (see `Firmware/`; up to three', ' (up to three'),
            (' (see `Firmware/README.md`)', ''),
            ('on MINI-PC ', ''), ('measured on MINI-PC with', 'measured with')]:
        s = s.replace(old, new)
    return s


def main():
    with_mediapipe = '--mediapipe' in sys.argv[1:]
    commit = git('rev-parse', '--short', 'HEAD').decode().strip()
    work = tempfile.mkdtemp(prefix='dance_student_')
    pkg = os.path.join(work, NAME)
    tar = git('archive', '--format=tar', '--prefix=%s/' % NAME, 'HEAD', '--', *PATHS)
    tarfile.open(fileobj=io.BytesIO(tar)).extractall(work, filter='data')
    clean_file(os.path.join(pkg, 'TouchDesigner', 'DanceWorkshop.toe'))
    readme = student_readme()
    if with_mediapipe:
        toxes = glob.glob(os.path.join(repo, 'TouchDesigner', 'toxes', '*.tox'))
        if not toxes:
            sys.exit('No TouchDesigner/toxes/*.tox on this computer (see README, Body tracking)')
        os.makedirs(os.path.join(pkg, 'TouchDesigner', 'toxes'))
        for t in toxes:
            shutil.copy2(t, os.path.join(pkg, 'TouchDesigner', 'toxes'))
        old = "**Setup, once per computer:** the plugin's `MediaPipe.tox` (187 MB) is not included in this folder."
        if old not in readme:
            sys.exit('README body tracking setup text changed; update make_student_package.py')
        readme = readme.replace(old, "**Setup:** already done: the plugin's `.tox` files are in "
                                "`TouchDesigner/toxes/`. To set it up again on another copy:")
    write(os.path.join(pkg, 'README.md'), readme)
    hits = [h for h in find_traces(pkg) if not h.split(':')[0].endswith(('.toe', '.tox'))]   # .toe checked expanded
    if hits:
        sys.exit('Traces left: %s' % hits)
    dist = os.path.join(repo, 'dist')
    os.makedirs(dist, exist_ok=True)
    zpath = os.path.join(dist, '%s-student-%s%s.zip' % (NAME, commit, '-mediapipe' if with_mediapipe else ''))
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for d, _, files in os.walk(pkg):
            for f in files:
                p = os.path.join(d, f)
                z.write(p, os.path.relpath(p, work))
    shutil.rmtree(work)
    print(zpath)


if __name__ == '__main__':
    main()
