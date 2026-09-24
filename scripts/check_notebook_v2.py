"""Visual and interaction checks against an isolated local app, never production."""
import json
import logging
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server


CONTROL_AUDIT = r"""() => {
  const rgb = color => color.match(/[\d.]+/g).map(Number);
  const luminance = values => values.slice(0,3).map(v => {
    v /= 255; return v <= .04045 ? v / 12.92 : ((v + .055)/1.055)**2.4;
  }).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
  const background = element => {
    const layers=[];
    for(let node=element;node;node=node.parentElement) layers.unshift(rgb(getComputedStyle(node).backgroundColor));
    return layers.reduce((base,c)=>base.map((v,i)=>v*(1-(c[3]??1))+c[i]*(c[3]??1)),[255,255,255]);
  };
  const issues=[];
  for(const element of document.querySelectorAll('button, a.button, .primary-action, .secondary-action, main a, summary')) {
    if(!element.checkVisibility() || element.disabled || !element.textContent.trim()) continue;
    const style=getComputedStyle(element);
    if(style.visibility==='hidden') continue;
    const fg=luminance(rgb(style.color)), bg=luminance(background(element));
    const contrast=(Math.max(fg,bg)+.05)/(Math.min(fg,bg)+.05);
    const large=parseFloat(style.fontSize)>=24 || (parseFloat(style.fontSize)>=18.66 && Number(style.fontWeight)>=700);
    if(contrast < (large ? 3 : 4.5)-.02) issues.push({kind:'contrast',text:element.textContent.trim().slice(0,50),ratio:contrast.toFixed(2)});
    if(element.matches('button, a.button') && (element.scrollWidth>element.clientWidth+2 || element.scrollHeight>element.clientHeight+2)) issues.push({kind:'clipped control',text:element.textContent.trim().slice(0,50)});
  }
  return issues;
}"""


def main():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI':'sqlite://'})
    server = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    destination=Path('.test-overhaul-v2')
    destination.mkdir(exist_ok=True)
    errors, issues = [], []
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(channel='chrome', headless=True)
            page=browser.new_page(viewport={'width':1440,'height':1000})
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.context.request.post(origin+'/demo')
            page.context.request.post(origin+'/terms', form={'title':'Biology','term':'Fall 2026','weekly_hours':'4','nonpersonal_confirmed':'yes'})
            page.context.request.post(origin+'/tasks', form={'title':'Lab report','subject':'Biology','due_at':'2027-02-01','estimated_minutes':'40','nonpersonal_confirmed':'yes'})
            page.goto(origin+'/tasks')
            row=page.locator('.task-card',has=page.get_by_role('heading',name='Lab report',exact=True))
            task_id=row.get_attribute('id').split('-')[1]
            page.context.request.post(origin+f'/tasks/{task_id}/split')
            page.goto(origin+'/tasks?view=courses&course=Biology')
            expect(page.locator('.assignment-tree')).to_be_visible()
            expect(page.locator('.subtask-branch .task-card')).to_have_count(2)
            page.locator('.subtask-branch .task-card').first.get_by_role('button',name='Start now',exact=True).click()
            expect(page.locator('.subtask-branch .task-card').first.get_by_role('button',name='Complete',exact=True)).to_be_visible()
            page.locator('.subtask-branch .task-card').first.get_by_role('button',name='Complete',exact=True).click()
            expect(page.locator('.assignment-tree>summary')).to_contain_text('50% complete')
            page.get_by_role('link',name='Add assignment',exact=True).click()
            expect(page.locator('#task-form input[name=subject]')).to_have_value('Biology')
            expect(page.locator('#task-form input[name=title]')).to_be_focused()
            paths=['/dashboard','/dashboard?view=today','/tasks','/tasks?view=courses','/terms','/settings',f'/tasks/{task_id}/edit','/tasks/import','/courses','/courses/plan','/courses/compare?catalog=ap&id=AP_CALCULUS_AB&id=AP_STATISTICS','/profile']
            for width in [320,390,768,1440]:
                page.set_viewport_size({'width':width,'height':1000})
                for index,path in enumerate(paths):
                    response=page.goto(origin+path)
                    assert response.status==200, (path,response.status)
                    if page.evaluate('document.documentElement.scrollWidth > innerWidth+1'): issues.append([width,path,'overflow'])
                    for issue in page.evaluate(CONTROL_AUDIT): issues.append([width,path,issue])
                    if width in [390,1440]: page.screenshot(path=str(destination/f'page-{index}-{width}.png'),full_page=path in ['/dashboard','/terms','/tasks?view=courses'])
            # Pointer and keyboard states must remain readable, not just defaults.
            page.goto(origin+'/tasks')
            for selector in ['button:visible:not(:disabled)', 'main a.button:visible', 'main summary:visible']:
                control=page.locator(selector).first
                control.hover()
                for issue in page.evaluate(CONTROL_AUDIT): issues.append(['hover',selector,issue])
                control.focus()
                assert control.evaluate("e=>getComputedStyle(e).outlineStyle!=='none'")
            # Reduced motion suppresses disclosure animations.
            page.evaluate("document.documentElement.dataset.motion='reduced'")
            page.locator('.queue-help>summary').click()
            assert page.evaluate("document.getAnimations().filter(a=>a.playState==='running').length") == 0
            for theme in ['dark','high-contrast']:
                for path in ['/tasks?view=courses','/dashboard','/settings','/terms']:
                    page.set_viewport_size({'width':390,'height':844})
                    page.goto(origin+path)
                    page.evaluate("theme=>{Object.assign(document.documentElement.dataset,{theme,textScale:'200',motion:'reduced'});}",theme)
                    if page.evaluate('document.documentElement.scrollWidth > innerWidth+1'): issues.append([theme,path,'200% overflow'])
                    for issue in page.evaluate(CONTROL_AUDIT): issues.append([theme,path,issue])
                    page.screenshot(path=str(destination/f'{theme}-{path.split("?")[0][1:]}.png'))
                    page.keyboard.press('Tab')
                    assert page.evaluate('document.activeElement!==document.body')
            public=browser.new_page(viewport={'width':1440,'height':1000})
            for width in [320,390,1440]:
                public.set_viewport_size({'width':width,'height':1000})
                for path in ['/','/register','/login','/planner']:
                    public.goto(origin+path)
                    for issue in public.evaluate(CONTROL_AUDIT): issues.append([width,path,issue])
                    if public.evaluate('document.documentElement.scrollWidth>innerWidth+1'): issues.append([width,path,'overflow'])
                    public.screenshot(path=str(destination/f'public-{path[1:] or "landing"}-{width}.png'),full_page=path=='/')
            browser.close()
        result={'javascript_errors':errors,'visual_issues':issues}
        (destination/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result))
        assert not errors and not issues
    finally:
        server.shutdown()


if __name__=='__main__':
    main()
