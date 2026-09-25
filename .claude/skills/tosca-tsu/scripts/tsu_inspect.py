#!/usr/bin/env python3
"""tsu_inspect.py - read-only inspector for Tosca .tsu subset files (Commander or Cloud).

A .tsu is gzip(JSON) = {"Entities":[{ObjectClass, Surrogate, Attributes{str:str}, Assocs{str:[surrogate]}}]}.
Usage:
  tsu_inspect.py FILE summary            # origin guess, class counts, folders, test cases
  tsu_inspect.py FILE tree [NAME]        # step tree of every (or matching) TestCase / RTB
  tsu_inspect.py FILE modules            # XModules -> attributes -> locator XParams
  tsu_inspect.py FILE entity SURROGATE   # raw entity (+ decoded H4sI blobs)
  tsu_inspect.py FILE dump OUT.json      # pretty JSON without FileContent.Data
Flags: --expand (inline reusable blocks in tree), --no-ids (omit surrogates, for diffing Commander vs Cloud)
Read-only; never writes .tsu files. Stdlib only.
Adapted from the approach in https://github.com/bermudas/ToscaTSU (MIT).
"""
import sys, gzip, json, base64, re, collections, signal

if hasattr(signal, 'SIGPIPE'):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # allow piping into head/less

# ActionMode bitflags, inferred from samples (verify against TCAPI before relying on 1/515/517)
MODES = {'37': 'Input', '69': 'Verify', '101': 'WaitOn', '165': 'Buffer', '517': 'Select', '515': 'Insert', '1': 'Select(nav)'}

def load(p):
    with open(p, 'rb') as f:
        raw = f.read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return json.loads(raw.decode('utf-8-sig'))['Entities']

def blob(v):  # nested base64(gzip(XML)) attrs: TestConfigurationParameters, TCProperties
    try:
        b = gzip.decompress(base64.b64decode(v))
        return b.decode('utf-16') if b[:2] in (b'\xff\xfe', b'\xfe\xff') else b.decode('utf-8-sig')
    except Exception:
        return v

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args or args[0] in ('-h', 'help'):
        print(__doc__); sys.exit(0 if args else 2)
    noids = '--no-ids' in sys.argv
    path, cmd, rest = args[0], (args[1] if len(args) > 1 else 'summary'), args[2:]
    E = load(path); ents = {e['Surrogate']: e for e in E}
    A = lambda e, k: e['Attributes'].get(k, '')
    R = lambda e, k: [ents[s] for s in e['Assocs'].get(k, []) if s in ents]
    name = lambda e: A(e, 'Name')

    def fpath(e):
        parts = []
        while True:
            p = R(e, 'ParentFolder')
            if not p: break
            e = p[0]; parts.append(name(e))
        return '/'.join(reversed(parts))

    def sv_line(sv, ind):
        ma = (R(sv, 'ModuleAttribute') or [None])[0]
        prop = A(sv, 'ActionProperty')
        s = f"{ind}- {name(ma) if ma else '?'}{'.'+prop if prop else ''} = {A(sv,'Value')!r} [{MODES.get(A(sv,'ActionMode'), A(sv,'ActionMode'))}]"
        if A(sv, 'ExplicitName'): s += f" name={A(sv,'ExplicitName')!r}"
        print(s)
        for c in R(sv, 'SubValues'): sv_line(c, ind + '  ')

    def walk(e, ind='', seen=()):
        c = e['ObjectClass']
        if c == 'XTestStep':
            m = (R(e, 'Module') or [None])[0]
            dis = ' (disabled)' if A(e, 'DisabledDescription') else ''
            print(f"{ind}STEP {name(e)!r} -> module {name(m) if m else '?'!r}{dis}")
            for sv in R(e, 'TestStepValues'): sv_line(sv, ind + '    ')
        elif c == 'TestStepFolderReference':
            for b in R(e, 'ReusedItem'):
                params = {}
                for plr in R(e, 'ParameterLayerReference'):
                    for pr in R(plr, 'AllParameterReferences'):
                        p = (R(pr, 'Parameter') or [None])[0]
                        params[name(p) if p else '?'] = A(pr, 'Value')
                print(f"{ind}CALL RTB {name(b)!r} params={params}")
                if b['Surrogate'] not in seen and '--expand' in sys.argv:
                    for i in R(b, 'Items'): walk(i, ind + '    ', seen + (b['Surrogate'],))
        elif c == 'TestCaseControlFlowItem':
            print(f"{ind}IF/LOOP {name(e)!r} StatementType={A(e,'StatementType')}")
            for f in R(e, 'ControlFlowFolders'):
                print(f"{ind}  [{name(f)}]")
                for i in R(f, 'Items'): walk(i, ind + '    ', seen)
        else:  # TestStepFolder, ReuseableTestStepBlock, TestCase ...
            cond = f" cond={A(e,'Condition')!r}" if A(e, 'Condition') else ''
            print(f"{ind}{c} {name(e)!r}{cond}")
            for i in R(e, 'Items'): walk(i, ind + '    ', seen)

    if cmd == 'summary':
        s = next(iter(ents), '')
        origin = 'Tosca Cloud (ULID surrogates)' if re.fullmatch(r'[0-9A-HJKMNP-TV-Z]{26}', s) else \
                 'Tosca Commander (GUID surrogates)' if re.fullmatch(r'[0-9a-f-]{36}', s) else 'unknown'
        print('origin guess:', origin, '| entities:', len(E))
        print('classes:', dict(collections.Counter(e['ObjectClass'] for e in E).most_common()))
        for e in E:
            if e['ObjectClass'] in ('TestCase', 'ReuseableTestStepBlock', 'XModule', 'ExecutionList'):
                print(f"  {e['ObjectClass']:24} {e['Surrogate']}  {fpath(e)}/{name(e)}")
    elif cmd == 'tree':
        for e in E:
            if e['ObjectClass'] in ('TestCase', 'ReuseableTestStepBlock') and (not rest or rest[0].lower() in name(e).lower()):
                print(f"\n=== {e['ObjectClass']} {fpath(e)}/{name(e)}" + ('' if noids else f"  [{e['Surrogate']}]"))
                if A(e, 'TestConfigurationParameters'):
                    print('TCPs:', re.findall(r'Name="([^"]+)" Value="([^"]*)"', blob(A(e, 'TestConfigurationParameters'))))
                for i in R(e, 'Items'): walk(i, '  ')
    elif cmd == 'modules':
        for m in (e for e in E if e['ObjectClass'] in ('XModule', 'ApiModule')):
            print(f"\nMODULE {name(m)!r}" + ('' if noids else f" [{m['Surrogate']}]") + f" {fpath(m)}")
            def attr(a, ind):
                ps = {name(p): A(p, 'Value') for p in R(a, 'Properties') if name(p) != 'SelfHealingData'}
                print(f"{ind}- {name(a)!r} {A(a,'BusinessType')} {ps}")
                for c in R(a, 'Attributes'): attr(c, ind + '  ')
            print('  params:', {name(p): A(p, 'Value') for p in R(m, 'Properties') if name(p) != 'SelfHealingData'})
            for a in R(m, 'Attributes'): attr(a, '  ')
    elif cmd == 'entity':
        if not rest or rest[0] not in ents:
            sys.exit(f"entity: unknown surrogate {rest[0] if rest else '(missing)'}")
        e = dict(ents[rest[0]]); e['Attributes'] = {k: (blob(v) if v.startswith('H4sI') else v) for k, v in e['Attributes'].items()}
        print(json.dumps(e, indent=2, ensure_ascii=False))
    elif cmd == 'dump':
        if not rest:
            sys.exit('dump: output path required')
        for e in E:
            if e['ObjectClass'] == 'FileContent': e['Attributes']['Data'] = f"<{len(e['Attributes'].get('Data',''))} b64 chars>"
        json.dump({'Entities': E}, open(rest[0], 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

    else:
        sys.exit(f"unknown command {cmd!r}; run with -h")

if __name__ == '__main__':
    main()
