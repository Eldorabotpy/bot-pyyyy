(() => {
    let csrf = '';

    window.portalSessionReady = fetch('/api/auth/status', {cache: 'no-store'})
        .then(response => response.ok ? response.json() : Promise.reject(new Error('Sessão indisponível.')))
        .then(status => {
            csrf = status.csrf || '';
            return status;
        })
        .catch(() => null);

    window.portalSessionHeaders = async (headers = {}) => {
        await window.portalSessionReady;
        return {...headers, 'X-Eldora-CSRF': csrf};
    };
})();
