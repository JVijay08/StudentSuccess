"""Read layout bounds across real pages of an isolated demo, including open controls."""
from browser_test_support import start_demo
import argparse
import json
import logging
import sys
import threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

BOUNDS = r"""() => {
 const issues=[];
 if(document.documentElement.scrollWidth>innerWidth+1) issues.push({kind:'page overflow',width:document.documentElement.scrollWidth});
 for(const e of document.querySelectorAll('main,article,nav,dialog[open],.utility-panel,h1,h2,h3,p,label,button,input,select,textarea,summary')) {
  if(!e.checkVisibility() || e.closest('.skip-link,.sr-only,.comparison-table-wrap') || e.matches('[type=hidden]')) continue;
  const r=e.getBoundingClientRect();
  if(r.width && (r.left < -1 || r.right > innerWidth+1)) issues.push({kind:'outside viewport',tag:e.tagName,cls:e.className,text:e.textContent.trim().slice(0,55),left:r.left,right:r.right});
  if(e.matches('button,summary') && (e.scrollWidth>e.clientWidth+3 || e.scrollHeight>e.clientHeight+3)) issues.push({kind:'clipped control',text:e.textContent.trim().slice(0,55)});
 }
 return issues;
}"""

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='.test-responsive')
    args=parser.parse_args()
    destination=Path(args.output); destination.mkdir(exist_ok=True)
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app=create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite://'})
    server=make_server('127.0.0.1',0,app,threaded=True)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    origin=f'http://127.0.0.1:{server.server_port}'
    issues=[]; errors=[]; coverage=[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(channel='chrome',headless=True)
            page=browser.new_page(viewport={'width':390,'height':844})
            page.on('pageerror',lambda e:errors.append(str(e)))
            start_demo(page.context.request, origin)
            tasks=page.context.request.get(origin+'/settings/export').json()['tasks']
            task_id=next(t['id'] for t in tasks if t['status']!='completed')
            paths=['/dashboard','/dashboard?view=today','/tasks','/tasks?view=courses',f'/tasks/{task_id}/edit',
                '/tasks/import','/courses','/courses/plan','/courses/compare?catalog=ap&id=AP_CALCULUS_AB&id=AP_STATISTICS',
                '/terms','/colleges?state=GA','/settings','/onboarding','/updates']
            public=browser.new_page()
            public.on('pageerror',lambda e:errors.append(str(e)))
            for width in [320,375,390,430,577,679,681,767,901,1100,1440]:
                for target,urls in [(page,paths),(public,['/','/register','/login','/planner'])]:
                    target.set_viewport_size({'width':width,'height':844})
                    for i,path in enumerate(urls):
                        response=target.goto(origin+path)
                        if response.status!=200: issues.append([width,path,'http',response.status]); continue
                        for state in ['initial','expanded']:
                            if state=='expanded':
                                target.evaluate("document.querySelectorAll('details').forEach(e=>e.open=true)")
                                if target.locator('#welcome-dialog').count(): target.evaluate("document.getElementById('welcome-dialog').showModal()")
                            issues.extend([width,path,state,item] for item in target.evaluate(BOUNDS))
                            if width in [390,1440] and state=='initial':
                                target.screenshot(path=str(destination/f'{"public" if target==public else "app"}-{i}-{width}.png'),full_page=False)
                        coverage.append([width,path])
            page.context.request.post(origin+'/settings',form={'academic_context':'college'})
            for width in [320,375,390,430,1440]:
                page.set_viewport_size({'width':width,'height':844})
                for path in ['/terms','/dashboard','/onboarding']:
                    page.goto(origin+path)
                    page.evaluate("document.querySelectorAll('details').forEach(e=>e.open=true)")
                    issues.extend([width,'college'+path,'expanded',item] for item in page.evaluate(BOUNDS))
                    coverage.append([width,'college'+path])
            for theme in ['dark','high-contrast']:
                page.set_viewport_size({'width':390,'height':844})
                for path in ['/tasks','/terms','/settings']:
                    page.goto(origin+path)
                    page.evaluate("theme=>{Object.assign(document.documentElement.dataset,{theme,textScale:'200',motion:'reduced'});document.querySelectorAll('details').forEach(e=>e.open=true)}",theme)
                    issues.extend([theme,path,'200%',item] for item in page.evaluate(BOUNDS))
            browser.close()
        result=dict(issues=issues,javascript_errors=errors,coverage=coverage)
        (destination/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(dict(issue_count=len(issues),javascript_errors=errors,views=len(coverage),examples=issues[:12])))
        assert not issues and not errors, 'Responsive audit found issues'
    finally: server.shutdown()

if __name__=='__main__': main()
