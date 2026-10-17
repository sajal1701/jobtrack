const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

async function main() {
  const handlers = {};
  const nodes = {};
  const buttons = [{disabled: false}, {disabled: false}];
  function node(id) {
    return nodes[id] ||= {
      value: '', hidden: false, textContent: '', children: [],
      addEventListener(event, callback) { handlers[`${id}:${event}`] = callback; },
      replaceChildren(...children) { this.children = children; },
      append(...children) { this.children.push(...children); },
      setAttribute() {}, reset() { this.values = {}; },
      querySelectorAll() { return buttons; },
    };
  }
  let mode = 'signed-out';
  let failLogout = false;
  const fetch = async (path, options = {}) => {
    if (options.method === 'POST') assert.equal(options.headers['X-JobTrack'], '1');
    let status = 200;
    let payload;
    if (path === '/api/auth/me') { status = 401; payload = {detail: 'Please sign in.'}; }
    else if (path === '/api/auth/login' && mode === 'throttled') {
      status = 429; payload = {detail: 'Too many sign-in attempts. Try again in a minute.'};
    } else if (path === '/api/auth/login' && mode === 'signed-out') {
      status = 401; payload = {detail: 'Invalid username or password.'};
    } else if (path === '/api/auth/register') { mode = 'signed-in'; payload = {username: 'alice'}; }
    else if (path === '/api/auth/logout') {
      status = failLogout ? 500 : 204; payload = {detail: 'Try again.'};
    } else if (mode === 'expired') { status = 401; payload = {detail: 'Please sign in.'}; }
    else if (path.startsWith('/api/applications')) {
      payload = [{company: 'Private Company', role: 'Engineer', status: 'saved', id: 1}];
    } else if (path === '/api/stats') { payload = {total: 1, by_status: {applied: 0, interview: 0, offer: 0}}; }
    else throw new Error(`Unexpected request: ${path}`);
    return {ok: status < 400, status, json: async () => payload};
  };
  const context = vm.createContext({
    document: {getElementById: node, createElement: () => ({...node(Symbol()), addEventListener() {}})},
    fetch, URLSearchParams, setTimeout, clearTimeout,
    FormData: class { constructor(form) { return Object.entries(form.values || {}); } },
  });
  vm.runInContext(fs.readFileSync('web/app.js', 'utf8'), context);
  await new Promise(setImmediate);
  assert.equal(node('tracker').hidden, true);
  assert.equal(node('auth-panel').hidden, false);
  const form = node('auth-form');
  form.values = {username: 'alice', password: 'a-long-test-password'};
  await handlers['auth-form:submit']({preventDefault() {}, currentTarget: form, submitter: {value: 'login'}});
  assert.equal(node('tracker').hidden, true);
  assert.equal(node('notice').textContent, 'Invalid username or password.');
  assert.equal(buttons.every(button => !button.disabled), true);
  mode = 'throttled';
  await handlers['auth-form:submit']({preventDefault() {}, currentTarget: form, submitter: {value: 'login'}});
  assert.equal(node('notice').textContent, 'Too many sign-in attempts. Try again in a minute.');
  assert.equal(node('notice').hidden, false);
  assert.equal(node('notice').className, 'notice error');
  assert.equal(node('tracker').hidden, true);
  assert.equal(buttons.every(button => !button.disabled), true);
  await handlers['auth-form:submit']({preventDefault() {}, currentTarget: form, submitter: {value: 'register'}});
  assert.equal(node('tracker').hidden, false);
  assert.equal(node('auth-panel').hidden, true);
  assert.equal(node('account-name').textContent, 'Signed in as alice');
  assert.equal(node('total').textContent, 1);
  failLogout = true;
  await handlers['logout:click']();
  assert.equal(node('tracker').hidden, false);
  assert.equal(node('notice').textContent, 'Try again.');
  failLogout = false;
  await handlers['logout:click']();
  assert.equal(node('tracker').hidden, true);
  assert.equal(node('applications').children.length, 0);
  assert.equal(node('total').textContent, '0');
  vm.runInContext('showAccount({username:"alice"})', context);
  mode = 'expired';
  await vm.runInContext('load().catch(() => {})', context);
  assert.equal(node('tracker').hidden, true);
  assert.equal(node('applications').children.length, 0);
  console.log('Frontend authentication checks passed: login failure, registration, logout failure/success, and session expiry.');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
