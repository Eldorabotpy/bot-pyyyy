// Isolated browser behavior checks. No real Google, Telegram, account or network.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '..', 'static/js/portal_auth.js'), 'utf8');
const account = {
    authenticated: true, sucesso: true, username: 'test_account', csrf: 'fresh-csrf',
    google_linked: true, telegram_linked: false, fresh_auth: true,
    personagens: [{id: 'character-1', nome: 'Test Hero'}],
};

function jsonResponse(body, status = 200) {
    return {ok: status < 400, status, json: async () => body};
}
function htmlResponse(status = 502) {
    return {ok: false, status, json: async () => {throw new SyntaxError('Unexpected token <');}};
}
function browser({url, responses}) {
    const elements = new Map();
    const rendered = [];
    const requests = [];
    function element(id) {
        if (!elements.has(id)) elements.set(id, {
            id, hidden: false, open: false, disabled: false, value: '', textContent: '',
            style: {}, dataset: {}, children: [],
            classList: {toggle() {}, add() {}, remove() {}},
            appendChild(child) {this.children.push(child);},
            setAttribute() {}, focus() {}, getClientRects() {return [1];},
            querySelectorAll() {return [];},
        });
        return elements.get(id);
    }
    const location = new URL(url);
    location.assign = () => {};
    const window = {
        location, Telegram: {WebApp: {initData: 'signed-stub'}},
        portalAccept(data) {
            rendered.push(data);
            element('titulo-caixa').textContent = 'SELECIONE SEU DESTINO';
            element('tela-selecao').style.display = 'block';
            element('tela-login').style.display = 'none';
        },
        mostrarCriacao() {}, mostrarAviso() {},
    };
    const document = {
        getElementById: element,
        querySelectorAll: () => [],
        createElement: () => element('created'),
        body: {classList: {add() {}, remove() {}, toggle() {}}},
        head: {appendChild() {}},
        addEventListener() {},
    };
    const fetch = async (route, options = {}) => {
        requests.push({route, options});
        assert.ok(responses.length, `Unexpected request: ${route}`);
        const expected = responses.shift();
        assert.equal(route, expected.route);
        return expected.response;
    };
    vm.runInNewContext(source, {
        window, document, fetch, URL, URLSearchParams,
        history: {replaceState() {}}, localStorage: {removeItem() {}},
        requestAnimationFrame() {}, setTimeout, console,
    }, {filename: 'portal_auth.js'});
    return {window, element, rendered, requests};
}

async function handoffResponseLost() {
    const page = browser({
        url: 'https://example.test/login?google_handoff_token=one-use-test',
        responses: [
            {route: '/api/auth/status', response: jsonResponse({authenticated: false, csrf: 'old-csrf'})},
            {route: '/api/auth/telegram-google-handoff', response: htmlResponse()},
            {route: '/api/auth/status', response: jsonResponse(account)},
        ],
    });
    await page.window.portalAuthReady;
    assert.equal(page.requests.length, 3, 'Handoff error must resync session');
    assert.equal(page.rendered.at(-1)?.username, account.username);
    assert.equal(page.element('titulo-caixa').textContent, 'SELECIONE SEU DESTINO');
    assert.equal(page.element('tela-selecao').style.display, 'block');
    assert.equal(page.element('portal-entry-tabs').hidden, true);
    assert.equal(page.element('portal-identidade').open, false);
    assert.ok(page.element('portal-account-settings-slot').children.includes(page.element('portal-identidade')));
}

async function nonJsonProxyResponse() {
    const page = browser({
        url: 'https://example.test/login',
        responses: [
            {route: '/api/auth/status', response: jsonResponse({authenticated: false, csrf: 'old-csrf'})},
            {route: '/api/auth/telegram', response: htmlResponse()},
            {route: '/api/auth/status', response: jsonResponse({authenticated: false, csrf: 'old-csrf'})},
        ],
    });
    await page.window.portalAuthReady;
    await page.element('portal-telegram').onclick();
    assert.equal(page.requests.length, 3, 'Provider error must resync session');
    const message = page.element('portal-auth-message').textContent;
    assert.match(message, /servidor|conexão|resposta/i);
    assert.doesNotMatch(message, /Unexpected token|SyntaxError|</);
}

async function providerUsesStatusPayload() {
    const page = browser({
        url: 'https://example.test/login',
        responses: [
            {route: '/api/auth/status', response: jsonResponse({authenticated: false, csrf: 'old-csrf'})},
            {route: '/api/auth/telegram', response: jsonResponse({...account, personagens: [{id: 'stale'}]})},
            {route: '/api/auth/status', response: jsonResponse(account)},
        ],
    });
    await page.window.portalAuthReady;
    await page.element('portal-telegram').onclick();
    assert.equal(page.rendered.length, 1, 'Only the status response renders characters');
    assert.equal(page.rendered[0].personagens[0].id, 'character-1');
    assert.equal(page.element('tela-selecao').style.display, 'block');
}

Promise.allSettled([handoffResponseLost(), nonJsonProxyResponse(), providerUsesStatusPayload()]).then(results => {
    const failures = results.filter(result => result.status === 'rejected');
    failures.forEach(result => console.error(result.reason));
    if (failures.length) process.exitCode = 1;
    else console.log('OK: handoff reconciles session and non-JSON response stays user friendly.');
});
