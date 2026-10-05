#!/usr/bin/env python3
"""
tosca_run_artifacts.py — get logs, attachments and RECORDING FRAMES from a Tosca Cloud run,
including personal-agent runs, without a human pasting anything.

WHY THIS EXISTS
---------------
`tosca_cli.py playlists logs` works only for shared/team-agent runs. For a **personal-agent**
run the service account (Tricentis_Cloud_API) is 403 on every relevant endpoint, and
`/_playlists/api/v2/playlistRuns` returns only runs with `"private": false` — a personal run is
absent from the list entirely, so no paging trick reaches it.

The MCP server (mcp-remote) caches an OAuth **user** token on disk. Reusing that token verbatim
reaches everything the service token cannot.

    md5(<mcp server url>)  ->  ~/.mcp-auth/mcp-remote-*/<hash>_tokens.json  ->  access_token

    GET /_playlists/api/v2/playlistRuns?playlistId=..&sort=desc(createdAt)   -> items[0].id
    GET /_playlists/api/v2/playlistRuns/<runId>                              -> executionId  *
    GET /_e2g/api/executions/<executionId>                                   -> units
    GET /_e2g/api/executions/<executionId>/units/<unitId>/attachments        -> SAS urls
    GET <sas url>                                        (send NO Authorization header)

    * the single-run GET is the ONLY place executionId appears; list items do not carry it.

Sort syntax is strict: only `desc(field)` / `asc(field)` parse. Supported filter fields are
`playlistId, state, createdBy, sort, pageToken` — everything else 400s.

TOKEN LIFETIME: 3600 s, and there is **no refresh_token**, because .mcp.json pins
`--static-oauth-client-metadata {"scope":"tta"}` without `offline_access`. When it expires the
script says so; ask the user to run `/mcp reload`. Adding `offline_access` to that scope would
make this fully autonomous.

SUBCOMMANDS
-----------
  log     <playlistId>            print the full TBox transcript of the latest run
  fetch   <playlistId>            download logs / Recording.mp4 / TestSteps.json / TBoxResults / JUnit
  frames  <playlistId> [...]      download the recording and cut PNG frames aligned to LOG TIMESTAMPS
  runs    [--name TEXT]           list runs as the Portal Runs page sees them (paged)
  delete-runs --name TEXT [...]   delete runs by playlist-name prefix / state (default: keep succeeded)

A RUN LIVES IN THREE STORES — only the third is what the Portal renders:
  /_playlists/api/v2/playlistRuns/{id}  playlist record; the ONLY place executionId appears
  /_e2g/api/executions/{id}             the execution + its attachments (logs, recording)
  /_playlists/api/v2/runInfo/{id}       what the Portal Runs page lists  <-- delete this to clear the UI
Collect executionIds BEFORE deleting playlistRuns — that delete destroys the mapping.
`GET /runInfo` silently caps at 10 items (`?top=` is a 400); only `POST /runInfo/search` pages properly.

`frames` is the high-leverage one. The agent log gives you step names and wall-clock times; the
recording gives you what was actually on screen. Aligning them answers "was the field empty?",
"was the button disabled?", "did the page actually navigate?" in ONE run instead of several
guess-and-rerun cycles.

    # frames around every step whose name contains "ADD TO CART", plus 2 s after
    python tosca_run_artifacts.py frames <playlistId> --step "ADD TO CART" --after 2
    # explicit offsets in seconds from the start of the recording
    python tosca_run_artifacts.py frames <playlistId> --at 38,42,44

Common options: `--exec <executionId>` to target a specific run instead of the latest,
`--out DIR` to choose the output directory.

Requires: httpx. For `frames`, ffmpeg — the system binary if present, otherwise
`pip install imageio-ffmpeg` provides a bundled one automatically.
"""
import argparse
import base64
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime

try:
    import httpx
except ImportError:
    sys.exit('pip install httpx')

EXT = {'logs': '.txt', 'Recording': '.mp4', 'TestSteps': '.json',
       'TBoxResults': '.tas', 'JUnit': '.xml'}


# --------------------------------------------------------------------------- auth / discovery
def find_mcp_url(root: str) -> str:
    """The token cache key is md5 of the MCP server url exactly as configured."""
    for rel in ('.mcp.json', '.vscode/mcp.json'):
        p = os.path.join(root, rel)
        if os.path.exists(p):
            m = re.search(r'https://[^\s"\']*?/_mcp/api/mcp', open(p).read())
            if m:
                return m.group(0)
    raise SystemExit('Could not find the _mcp/api/mcp URL in .mcp.json or .vscode/mcp.json')


def user_token(mcp_url: str, skew: int = 60):
    key = hashlib.md5(mcp_url.encode()).hexdigest()
    hits = glob.glob(os.path.expanduser(f'~/.mcp-auth/mcp-remote-*/{key}_tokens.json'))
    if not hits:
        raise SystemExit(f'No mcp-remote token cache for {mcp_url}. Connect the MCP client once.')
    best = None
    for f in hits:
        try:
            at = json.load(open(f))['access_token']
            payload = json.loads(base64.urlsafe_b64decode(at.split('.')[1] + '=='))
        except Exception:
            continue
        if best is None or payload['exp'] > best[0]:
            best = (payload['exp'], at, payload.get('sub', '?'))
    if best is None:
        raise SystemExit('Token cache present but unreadable.')
    left = int(best[0] - time.time())
    if left < skew:
        raise SystemExit(
            f'Cached user token expired {-left}s ago and no refresh_token is stored '
            '(.mcp.json pins scope "tta" without "offline_access").\n'
            'Ask the user to run  /mcp reload  and retry.')
    return best[1], left, best[2]


def resolve_execution(cli, base, playlist_id, exec_id=None):
    if exec_id:
        return exec_id
    r = cli.get(f'{base}/_playlists/api/v2/playlistRuns',
                params={'playlistId': playlist_id, 'sort': 'desc(createdAt)'})
    r.raise_for_status()
    items = r.json().get('items', [])
    if not items:
        raise SystemExit('No runs found for that playlist.')
    run = items[0]
    print(f"[run] {run['id']}  {run.get('createdAt')}  state={run.get('state')}")
    r = cli.get(f"{base}/_playlists/api/v2/playlistRuns/{run['id']}")
    r.raise_for_status()
    return r.json()['executionId']


def unit_attachments(cli, base, exec_id):
    """Yield (unit, {name: download_uri})."""
    units = cli.get(f'{base}/_e2g/api/executions/{exec_id}').json().get('items', [])
    for u in units:
        atts = cli.get(f"{base}/_e2g/api/executions/{exec_id}/units/{u['id']}/attachments").json()
        yield u, {a.get('name'): (a.get('contentDownloadUri') or a.get('uri') or a.get('url'))
                  for a in atts if (a.get('contentDownloadUri') or a.get('uri') or a.get('url'))}


def download(uri, dest):
    # The SAS signature IS the auth — sending a bearer here makes Azure reject the request.
    with httpx.stream('GET', uri, timeout=300) as r:
        r.raise_for_status()
        with open(dest, 'wb') as fh:
            for chunk in r.iter_bytes():
                fh.write(chunk)
    return os.path.getsize(dest)


# --------------------------------------------------------------------------- log parsing
STEP_RE = re.compile(r'^\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})Z.*?\[(Succeeded|Failed)\]\s+"([^"]+)"')
REC_RE = re.compile(r'^\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})Z.*Screen recorder: Recording')


def parse_log(text):
    """Return (t0, [(offset_seconds, state, step_name)]). t0 = moment recording started."""
    t0, steps = None, []
    for line in text.splitlines():
        if t0 is None:
            m = REC_RE.match(line)
            if m:
                t0 = datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S')
                continue
        m = STEP_RE.match(line)
        if m and t0:
            t = datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S')
            steps.append(((t - t0).total_seconds(), m.group(2), m.group(3)))
    return t0, steps


def ffmpeg_exe():
    exe = shutil.which('ffmpeg')
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise SystemExit('ffmpeg not found. Install it, or: pip install imageio-ffmpeg')


# --------------------------------------------------------------------------- commands
def cmd_log(args, cli, base, exec_id):
    for unit, atts in unit_attachments(cli, base, exec_id):
        print(f"\n--- unit {unit.get('id')} :: {unit.get('name')} :: {unit.get('state')} ---")
        uri = atts.get('logs')
        if uri:
            print(httpx.get(uri, timeout=120).text)


def cmd_fetch(args, cli, base, exec_id):
    os.makedirs(args.out, exist_ok=True)
    for unit, atts in unit_attachments(cli, base, exec_id):
        for name, uri in atts.items():
            dest = os.path.join(args.out, f'{name}{EXT.get(name, "")}')
            print(f'    {name:<14} -> {dest} ({download(uri, dest)} bytes)')


def runinfo_search(cli, base, per_page=50, cap=2000):
    """Page the Portal's own runInfo search. GET /runInfo caps at 10 regardless of `total`."""
    out, token = [], None
    while True:
        body = {"filter": {"searchTerm": None, "items": [], "linkOperator": "or"},
                "sort": [{"field": "createdAt", "direction": 1}],
                "pageToken": token, "itemsPerPage": per_page,
                "includeFields": None, "excludeFields": None}
        r = cli.post(f'{base}/_playlists/api/v2/runInfo/search', json=body)
        r.raise_for_status()
        j = r.json()
        out += j.get('items', [])
        token = j.get('pageToken') or j.get('nextPageToken')
        if not token or len(out) >= j.get('total', 0) or len(out) >= cap:
            return out


def cmd_runs(args, cli, base, _exec_id=None):
    rows = runinfo_search(cli, base)
    if args.name:
        rows = [x for x in rows if str(x.get('name', '')).startswith(args.name)]
    from collections import Counter
    print(f"{len(rows)} run(s)  states={dict(Counter(x.get('state') for x in rows))}\n")
    for x in sorted(rows, key=lambda r: str(r.get('createdAt')), reverse=True)[:args.limit]:
        print(f"  {str(x.get('state')):<10} {str(x.get('name'))[:40]:<40} "
              f"{str(x.get('createdAt'))[:19]}  {x.get('id')}")


def cmd_delete_runs(args, cli, base, _exec_id=None):
    if not args.name:
        raise SystemExit('--name <playlist-name-prefix> is required (refusing to delete everything)')
    rows = [x for x in runinfo_search(cli, base) if str(x.get('name', '')).startswith(args.name)]
    states = set(s.strip() for s in args.states.split(',')) if args.states else {'failed', 'canceled'}
    doomed = [x for x in rows if x.get('state') in states]
    from collections import Counter
    print(f"matched {len(rows)} run(s) for name prefix {args.name!r}")
    print(f"  states present: {dict(Counter(x.get('state') for x in rows))}")
    print(f"  deleting states {sorted(states)} -> {len(doomed)} run(s); keeping {len(rows)-len(doomed)}")
    if not doomed:
        return
    if not args.yes:
        print('\n  (dry run — pass --yes to actually delete)')
        for x in doomed[:10]:
            print(f"    would delete {x.get('state'):<10} {str(x.get('createdAt'))[:19]} {x.get('id')}")
        if len(doomed) > 10:
            print(f'    … and {len(doomed)-10} more')
        return
    codes = Counter()
    for x in doomed:
        codes[cli.delete(f"{base}/_playlists/api/v2/runInfo/{x['id']}").status_code] += 1
    print('  delete status codes:', dict(codes))
    time.sleep(3)
    left = [x for x in runinfo_search(cli, base) if str(x.get('name', '')).startswith(args.name)]
    print(f"  remaining for {args.name!r}: {len(left)}  "
          f"states={dict(Counter(x.get('state') for x in left))}")


def cmd_frames(args, cli, base, exec_id):
    os.makedirs(args.out, exist_ok=True)
    log_path = os.path.join(args.out, 'logs.txt')
    vid_path = os.path.join(args.out, 'Recording.mp4')

    for unit, atts in unit_attachments(cli, base, exec_id):
        if 'logs' in atts and not os.path.exists(log_path):
            download(atts['logs'], log_path)
        if 'Recording' in atts and not os.path.exists(vid_path):
            print('    downloading recording …')
            download(atts['Recording'], vid_path)
    if not os.path.exists(vid_path):
        raise SystemExit('This run has no Recording attachment '
                         '(recording is only captured for some agents/configs).')

    t0, steps = parse_log(open(log_path, errors='replace').read())
    if t0 is None:
        raise SystemExit('Could not find "Screen recorder: Recording" in the log — cannot align frames.')

    offsets = {}
    if args.at:
        for s in args.at.split(','):
            offsets[float(s.strip())] = f'at{s.strip()}'
    if args.step:
        pat = args.step.lower()
        for off, state, name in steps:
            if pat in name.lower():
                for d in range(0, args.after + 1):
                    offsets[off + d] = f'{re.sub(r"[^A-Za-z0-9]+", "_", name)[:40]}+{d}s'
    if not offsets:                      # default: every failed step, and 2 s after it
        for off, state, name in steps:
            if state == 'Failed':
                offsets[off] = f'FAIL_{re.sub(r"[^A-Za-z0-9]+", "_", name)[:40]}'
                offsets[off + 2] = f'FAIL_{re.sub(r"[^A-Za-z0-9]+", "_", name)[:40]}+2s'
        if not offsets:
            print('No failed steps; pass --step or --at to choose frames.')
            return

    print(f'\n  recording t0 = {t0}   ({len(steps)} steps parsed)')
    ff = ffmpeg_exe()
    for off in sorted(offsets):
        if off < 0:
            continue
        dst = os.path.join(args.out, f'frame_{int(off):04d}s_{offsets[off]}.png')
        subprocess.run([ff, '-y', '-ss', str(off), '-i', vid_path, '-frames:v', '1',
                        '-vf', f'scale={args.width}:-1', dst],
                       capture_output=True)
        if os.path.exists(dst):
            print(f'    t+{off:6.1f}s -> {dst}')

    print('\n  step timeline:')
    for off, state, name in steps:
        mark = ' <== FAILED' if state == 'Failed' else ''
        print(f'    t+{off:6.1f}s  {name}{mark}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['log', 'fetch', 'frames', 'runs', 'delete-runs'])
    ap.add_argument('playlist_id', nargs='?', help='required for log/fetch/frames')
    ap.add_argument('--name', help='runs/delete-runs: playlist-name prefix filter')
    ap.add_argument('--states', help="delete-runs: comma list (default 'failed,canceled')")
    ap.add_argument('--limit', type=int, default=40, help='runs: max rows to print')
    ap.add_argument('--yes', action='store_true', help='delete-runs: actually delete (default dry run)')
    ap.add_argument('--exec', dest='exec_id', help='target this executionId instead of the latest run')
    ap.add_argument('--out', default=None, help='output directory')
    ap.add_argument('--step', help='frames: only steps whose name contains this text')
    ap.add_argument('--at', help='frames: explicit comma-separated offsets in seconds')
    ap.add_argument('--after', type=int, default=1, help='frames: also grab N seconds after each match')
    ap.add_argument('--width', type=int, default=1400, help='frames: output width in px')
    ap.add_argument('--root', default=os.getcwd(), help='project root holding .mcp.json')
    args = ap.parse_args()
    if args.out is None:
        args.out = os.path.join(args.root, '.claude/tmp', f'run-{args.exec_id or "latest"}')

    mcp_url = find_mcp_url(args.root)
    tok, left, who = user_token(mcp_url)
    print(f'[auth] user token ok ({who}), {left}s left')
    base = mcp_url.split('/_mcp/')[0]

    headers = {'Authorization': f'Bearer {tok}', 'accept': 'application/json',
               'content-type': 'application/json'}
    with httpx.Client(timeout=120, headers=headers) as cli:
        if args.command in ('runs', 'delete-runs'):
            {'runs': cmd_runs, 'delete-runs': cmd_delete_runs}[args.command](args, cli, base)
            return
        if not args.playlist_id:
            raise SystemExit(f'{args.command} needs a <playlistId>')
        exec_id = resolve_execution(cli, base, args.playlist_id, args.exec_id)
        print(f'[exec] {exec_id}')
        {'log': cmd_log, 'fetch': cmd_fetch, 'frames': cmd_frames}[args.command](args, cli, base, exec_id)


if __name__ == '__main__':
    main()
