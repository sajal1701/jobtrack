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
      attributes: {},
      setAttribute(name, value) { this.attributes[name] = value; }, reset() { this.values = {}; },
      querySelectorAll() { return buttons; },
    };
  }
  let mode = 'signed-out';
  let failLogout = false;
  let failList = false;
  let networkFailure = false;
  let emptyList = false;
  let total = 1;
  const listRequests = [];
  const fetch = async (path, options = {}) => {
    if (networkFailure) throw new TypeError('Failed to fetch');
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
      listRequests.push(path);
      if (failList) return {ok: false, status: 500, json: async () => ({detail: 'Could not load applications.'})};
      payload = emptyList ? [] : [{company: 'Private Company', role: 'Engineer', status: 'saved', id: 1}];
    } else if (path === '/api/stats') { payload = {total, by_status: {applied: 0, interview: 0, offer: 0}}; }
    else throw new Error(`Unexpected request: ${path}`);
    return {ok: status < 400, status, json: async () => payload};
  };
  const context = vm.createContext({
    document: {getElementById: node, createElement: (tagName) => ({...node(Symbol()), tagName, addEventListener() {}})},
    fetch, URLSearchParams, setTimeout, clearTimeout,
    FormData: class { constructor(form) { return Object.entries(form.values || {}); } },
  });
  vm.runInContext(fs.readFileSync('web/app.js', 'utf8'), context);
  await new Promise(setImmediate);
  assert.equal(node('tracker').hidden, true);
  assert.equal(node('auth-panel').hidden, false);
  const password = node('auth-password');
  password.value = 'a-long-test-password';
  assert.equal(password.type, 'password');
  handlers['toggle-password:click']();
  assert.equal(password.type, 'text');
  assert.equal(password.value, 'a-long-test-password');
  assert.equal(node('toggle-password').textContent, 'Hide password');
  assert.equal(node('toggle-password').attributes['aria-pressed'], 'true');
  handlers['toggle-password:click']();
  assert.equal(password.type, 'password');
  assert.equal(node('toggle-password').textContent, 'Show password');
  assert.equal(node('toggle-password').attributes['aria-pressed'], 'false');
  const form = node('auth-form');
  form.values = {username: 'alice', password: 'a-long-test-password'};
  await handlers['auth-form:submit']({preventDefault() {}, currentTarget: form, submitter: {value: 'login'}});
  assert.equal(node('tracker').hidden, true);
  assert.equal(node('notice').textContent, 'Invalid username or password.');
  assert.equal(buttons.every(button => !button.disabled), true);
  networkFailure = true;
  const connectionMessage = 'Could not connect to JobTrack. Check that the server is running and try again.';
  await handlers['auth-form:submit']({preventDefault() {}, currentTarget: form, submitter: {value: 'login'}});
  assert.equal(node('notice').textContent, connectionMessage);
  assert.equal(node('notice').hidden, false);
  assert.equal(node('notice').className, 'notice error');
  assert.equal(form.values.username, 'alice');
  assert.equal(form.values.password, 'a-long-test-password');
  assert.equal(buttons.every(button => !button.disabled), true);
  networkFailure = false;
  mode = 'throttled';
  await handlers['auth-form:submit']({preventDefault() {}, currentTarget: form, submitter: {value: 'login'}});
  assert.equal(node('notice').textContent, 'Too many sign-in attempts. Try again in a minute.');
  assert.equal(node('notice').hidden, false);
  assert.equal(node('notice').className, 'notice error');
  assert.equal(node('tracker').hidden, true);
  assert.equal(buttons.every(button => !button.disabled), true);
  handlers['toggle-password:click']();
  await handlers['auth-form:submit']({preventDefault() {}, currentTarget: form, submitter: {value: 'register'}});
  assert.equal(password.type, 'password');
  assert.equal(node('toggle-password').attributes['aria-pressed'], 'false');
  assert.equal(node('tracker').hidden, false);
  assert.equal(node('auth-panel').hidden, true);
  assert.equal(node('account-name').textContent, 'Signed in as alice');
  assert.equal(node('total').textContent, 1);
  emptyList = true;
  total = 0;
  await vm.runInContext('load()', context);
  assert.equal(node('applications').children[0].textContent,
    'No applications yet. Add your first opportunity using the form.');
  total = 1;
  node('search').value = 'No match';
  await vm.runInContext('load()', context);
  assert.equal(node('applications').children[0].textContent,
    'No applications match these filters. Try another search or use Clear filters.');
  assert.equal(node('total').textContent, 1);
  emptyList = false;
  await handlers['clear-filters:click']();
  assert.equal(node('applications').children[0].tagName, 'article');
  node('search').value = 'Private & Co';
  node('stage').value = 'interview';
  handlers['search:input']();
  const requestsBeforeClear = listRequests.length;
  await handlers['clear-filters:click']();
  assert.equal(node('search').value, '');
  assert.equal(node('stage').value, '');
  const clearedUrl = new URL(listRequests.at(-1), 'http://localhost');
  assert.equal(clearedUrl.searchParams.get('search'), '');
  assert.equal(clearedUrl.searchParams.has('status'), false);
  assert.equal(node('notice').hidden, true);
  await new Promise(resolve => setTimeout(resolve, 250));
  assert.equal(listRequests.length, requestsBeforeClear + 1);
  failList = true;
  await handlers['clear-filters:click']();
  assert.equal(node('notice').textContent, 'Could not load applications.');
  assert.equal(node('notice').className, 'notice error');
  failList = false;
  networkFailure = true;
  await handlers['logout:click']();
  assert.equal(node('notice').textContent, connectionMessage);
  assert.equal(node('tracker').hidden, false);
  assert.equal(node('account-name').textContent, 'Signed in as alice');
  assert.equal(node('logout').disabled, false);
  networkFailure = false;
  failLogout = true;
  await handlers['logout:click']();
  assert.equal(node('tracker').hidden, false);
  assert.equal(node('notice').textContent, 'Try again.');
  failLogout = false;
  vm.runInContext('setPasswordVisibility(true)', context);
  await handlers['logout:click']();
  assert.equal(password.type, 'password');
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
