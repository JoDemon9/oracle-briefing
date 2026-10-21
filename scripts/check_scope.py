"""Daily integrity/preview; units for maintenance; archive audits only by request."""
import argparse
import json
from pathlib import Path
import subprocess


def classify(root,base):
    try:
        if not base:raise ValueError('Missing baseline')
        files=subprocess.check_output(['git','-C',str(root),'diff','--name-only',base,'--'],text=True,stderr=subprocess.DEVNULL).splitlines()
        files+=subprocess.check_output(['git','-C',str(root),'ls-files','--others','--exclude-standard'],text=True).splitlines()
        profile='maintenance' if any(p.startswith(('scripts/','tests/','.github/')) for p in files) else 'central'
    except (ValueError,subprocess.CalledProcessError):files=[];profile='maintenance'
    return {'profile':profile,'changed_files':files,'policy':'Daily receipt integrity and two current-page preview cases. Maintenance adds units; full historical audits are explicit only.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base');parser.add_argument('--full-regression',action='store_true');parser.add_argument('--github-output',type=Path);args=parser.parse_args()
    result=classify(Path(__file__).resolve().parents[1],args.base)
    if args.full_regression:result['profile']='full'
    if args.github_output:
        with args.github_output.open('a') as stream:stream.write('profile='+result['profile']+'\n')
    target=Path('.work/check-scope.json');target.parent.mkdir(exist_ok=True);target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
