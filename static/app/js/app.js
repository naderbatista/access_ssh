/* CMM — app.js */

document.addEventListener('DOMContentLoaded', () => {
    const loginForm     = document.getElementById('login-form');
    const operationForm = document.getElementById('operation-form');
    const authResult    = document.getElementById('auth-result');
    const opResult      = document.getElementById('operation-result');
    const resultConsole = document.getElementById('result-console');
    const adminPanel    = document.getElementById('admin-panel');
    const adminOverlay  = document.getElementById('admin-overlay');
    const actionHidden  = document.getElementById('action-select');
    const actionTabs    = document.getElementById('action-tabs');
    const btnLogout     = document.getElementById('btn-logout');
    const connStatus    = document.getElementById('conn-status');
    const topbarProto   = document.getElementById('topbar-proto-label');
    const connPort      = document.getElementById('conn_port');

    const sshPort    = parseInt(document.body.dataset.sshPort    || '22',  10);
    const telnetPort = parseInt(document.body.dataset.telnetPort || '23', 10);

    const fieldPassword = document.getElementById('field-password-group');
    const fieldConfirm  = document.getElementById('field-confirm-group');
    const fieldGroup    = document.getElementById('field-group-group');
    const targetPw      = document.getElementById('target_password');
    const targetPwConf  = document.getElementById('target_password_confirm');
    const togglePwBtn   = document.getElementById('toggle-target-pw');
    const togglePwConfBtn = document.getElementById('toggle-target-pw-confirm');
    const btnPrintResult = document.getElementById('btn-print-result');

    // modals
    const rootModal     = document.getElementById('root-modal');
    const modalRootPass = document.getElementById('modal_root_password');
    const modalError    = document.getElementById('modal-error');
    const modalCancel   = document.getElementById('modal-cancel');
    const modalConfirm  = document.getElementById('modal-confirm');

    const deleteModal   = document.getElementById('delete-modal');
    const deleteTarget  = document.getElementById('delete-target-name');
    const deleteCancel  = document.getElementById('delete-cancel');
    const deleteConfirm = document.getElementById('delete-confirm');

    let _isRoot = document.body.dataset.isRoot === 'true';
    let _modalResolve = null;
    let _deleteResolve = null;

    function getCsrf() {
        const el = document.querySelector('[name=csrfmiddlewaretoken]');
        return el ? el.value : '';
    }

    // ---- protocol selector ----
    function getProtocol() {
        const checked = document.querySelector('input[name="protocol"]:checked');
        return checked ? checked.value : 'ssh';
    }

    loginForm.addEventListener('change', (e) => {
        if (e.target.name !== 'protocol') return;
        const proto = e.target.value;
        if (proto === 'telnet') {
            connPort.value = telnetPort;
            topbarProto.textContent = 'Telnet';
        } else {
            connPort.value = sshPort;
            topbarProto.textContent = 'SSH';
        }
    });

    // ---- tabs ----
    actionTabs.addEventListener('click', (e) => {
        const tab = e.target.closest('.tab');
        if (!tab) return;
        actionTabs.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        actionHidden.value = tab.dataset.action;
        updateFields();
    });

    function updateFields() {
        const a = actionHidden.value;
        const hidePw = a === 'group' || a === 'delete';
        fieldPassword.classList.toggle('hidden', hidePw);
        fieldConfirm.classList.toggle('hidden', hidePw);
        fieldGroup.classList.toggle('hidden', a === 'password' || a === 'delete');
    }
    updateFields();

    // ---- password toggle ----
    togglePwBtn.addEventListener('click', () => {
        const show = targetPw.type === 'password';
        targetPw.type = show ? 'text' : 'password';
    });
    if (togglePwConfBtn) {
        togglePwConfBtn.addEventListener('click', () => {
            const show = targetPwConf.type === 'password';
            targetPwConf.type = show ? 'text' : 'password';
        });
    }

    // ---- helpers ----
    function setLoading(btn, on, text) {
        const label = btn.querySelector('.btn-label');
        const spin  = btn.querySelector('.btn-spinner');
        if (on) {
            btn._orig = label.textContent;
            label.textContent = text || 'Aguarde...';
            spin.classList.remove('hidden');
            btn.disabled = true;
        } else {
            label.textContent = btn._orig || label.textContent;
            spin.classList.add('hidden');
            btn.disabled = false;
        }
    }

    function showMsg(el, ok, text) {
        el.classList.remove('hidden', 'success', 'error', 'msg--ok', 'msg--error');
        el.classList.add(ok ? 'msg--ok' : 'msg--error');
        el.textContent = text;
    }

    function showConsole(data) {
        if (!data) {
            resultConsole.classList.add('hidden');
            btnPrintResult.classList.add('hidden');
            return;
        }
        resultConsole.classList.remove('hidden');
        let h = '';
        if (data.command) h += '<span class="c-label">$ comando</span>' + esc(data.command);
        if (data.stdout)  h += '<div class="c-block"><span class="c-label">saída</span>' + esc(data.stdout) + '</div>';
        if (data.stderr)  h += '<div class="c-block"><span class="c-label">erro</span>' + esc(data.stderr) + '</div>';
        resultConsole.innerHTML = h;
        btnPrintResult.classList.remove('hidden');
    }

    // PNG screenshot of result
    if (btnPrintResult) {
        btnPrintResult.addEventListener('click', () => {
            btnPrintResult.disabled = true;
            btnPrintResult.textContent = '...';
            html2canvas(resultConsole, {
                backgroundColor: '#1e1e1e',
                scale: 2,
                useCORS: true,
            }).then(canvas => {
                const link = document.createElement('a');
                const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
                link.download = 'resultado-' + ts + '.png';
                link.href = canvas.toDataURL('image/png');
                link.click();
            }).catch(err => {
                alert('Erro ao gerar imagem: ' + err.message);
            }).finally(() => {
                btnPrintResult.disabled = false;
                btnPrintResult.textContent = '📷 PNG';
            });
        });
    }

    function esc(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    function setStatus(online, user) {
        if (online) {
            const host = document.getElementById('conn_host').value.trim();
            connStatus.textContent = (user || 'conectado') + '@' + host;
            connStatus.classList.add('online');
            topbarProto.textContent = getProtocol().toUpperCase();
        } else {
            connStatus.textContent = 'desconectado';
            connStatus.classList.remove('online');
        }
    }

    // ---- admin lock ----
    function unlock(isRoot) {
        _isRoot = !!isRoot;
        adminPanel.classList.remove('disabled-section');
        adminPanel.classList.add('unlocked');
        adminOverlay.classList.add('hidden');
    }
    function lock() {
        _isRoot = false;
        adminPanel.classList.add('disabled-section');
        adminPanel.classList.remove('unlocked');
        adminOverlay.classList.remove('hidden');
        opResult.classList.add('hidden');
        resultConsole.classList.add('hidden');
        setStatus(false);
    }

    // ---- root modal ----
    function openRootModal() {
        modalRootPass.value = '';
        modalError.classList.add('hidden');
        rootModal.classList.remove('hidden');
        setTimeout(() => modalRootPass.focus(), 40);
        return new Promise(r => { _modalResolve = r; });
    }
    function closeRootModal() { rootModal.classList.add('hidden'); }

    modalCancel.addEventListener('click', () => {
        closeRootModal();
        if (_modalResolve) { _modalResolve(null); _modalResolve = null; }
    });
    rootModal.addEventListener('click', (e) => {
        if (e.target === rootModal) { closeRootModal(); if (_modalResolve) { _modalResolve(null); _modalResolve = null; } }
    });
    modalRootPass.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); modalConfirm.click(); }
    });
    modalConfirm.addEventListener('click', () => {
        const p = modalRootPass.value.trim();
        if (!p) { modalError.textContent = 'Informe a senha root.'; modalError.classList.remove('hidden'); return; }
        closeRootModal();
        if (_modalResolve) { _modalResolve({ root_password: p }); _modalResolve = null; }
    });

    // ---- delete modal ----
    function openDeleteModal(name) {
        deleteTarget.textContent = name;
        deleteModal.classList.remove('hidden');
        return new Promise(r => { _deleteResolve = r; });
    }
    function closeDeleteModal() { deleteModal.classList.add('hidden'); }

    deleteCancel.addEventListener('click', () => {
        closeDeleteModal(); if (_deleteResolve) { _deleteResolve(false); _deleteResolve = null; }
    });
    deleteModal.addEventListener('click', (e) => {
        if (e.target === deleteModal) { closeDeleteModal(); if (_deleteResolve) { _deleteResolve(false); _deleteResolve = null; } }
    });
    deleteConfirm.addEventListener('click', () => {
        closeDeleteModal(); if (_deleteResolve) { _deleteResolve(true); _deleteResolve = null; }
    });

    // ---- login ----
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('btn-login');
        setLoading(btn, true, 'Conectando...');
        authResult.classList.add('hidden');
        try {
            const res = await fetch('/login/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrf() },
                body: new FormData(loginForm),
            });
            const j = await res.json();
            showMsg(authResult, j.success, j.message);
            if (j.success) {
                unlock(j.is_root);
                setStatus(true, document.getElementById('common_username').value.trim());
            }
        } catch (err) {
            showMsg(authResult, false, 'Erro de rede: ' + err.message);
        } finally { setLoading(btn, false); }
    });

    // ---- execute ----
    operationForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const action = actionHidden.value;
        const user   = document.getElementById('target_username').value.trim();

        // validar confirmação de senha
        if (action === 'create' || action === 'password') {
            if (targetPw.value !== targetPwConf.value) {
                showMsg(opResult, false, 'As senhas não coincidem.');
                return;
            }
        }

        if (action === 'delete') {
            if (!user) { showMsg(opResult, false, 'Informe o login do usuário.'); return; }
            const ok = await openDeleteModal(user);
            if (!ok) return;
        }

        let rootCreds = null;
        if (!_isRoot) {
            rootCreds = await openRootModal();
            if (!rootCreds) return;
        }

        const btn = document.getElementById('btn-execute');
        setLoading(btn, true, 'Executando...');
        opResult.classList.add('hidden');
        resultConsole.classList.add('hidden');

        try {
            const fd = new FormData(operationForm);
            if (rootCreds) fd.set('root_password', rootCreds.root_password);
            const res = await fetch('/execute/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrf() },
                body: fd,
            });
            const j = await res.json();
            showMsg(opResult, j.success, j.message);
            showConsole(j.data);
            if (j.success) clearFields();
            if (j.group_not_found) groupPrompt(rootCreds);
        } catch (err) {
            showMsg(opResult, false, 'Erro de rede: ' + err.message);
        } finally { setLoading(btn, false); }
    });

    function clearFields() {
        document.getElementById('target_username').value = '';
        document.getElementById('target_password').value = '';
        document.getElementById('target_password_confirm').value = '';
        document.getElementById('group_name').value = '';
    }

    // ---- group prompt ----
    function groupPrompt(rootCreds) {
        resultConsole.classList.remove('hidden');
        resultConsole.innerHTML =
            '<span class="c-label">Grupo não encontrado. Listar grupos disponíveis?</span>' +
            '<div style="margin-top:6px;display:flex;gap:6px">' +
            '<button type="button" class="btn" id="btn-show-groups">Sim</button>' +
            '<button type="button" class="btn btn--flat" id="btn-hide-groups">Não</button></div>';
        document.getElementById('btn-show-groups').addEventListener('click', () => fetchGroups(rootCreds));
        document.getElementById('btn-hide-groups').addEventListener('click', () => resultConsole.classList.add('hidden'));
    }

    async function fetchGroups(rootCreds) {
        resultConsole.innerHTML = '<span class="c-label">carregando...</span>';
        try {
            const opts = { method: 'POST', headers: { 'X-CSRFToken': getCsrf() } };
            if (rootCreds) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(rootCreds); }
            const res = await fetch('/groups/', opts);
            const j = await res.json();
            if (j.success && j.groups) {
                resultConsole.innerHTML = '<span class="c-label">grupos</span>' + esc(j.groups.join(', '));
            } else {
                resultConsole.innerHTML = '<span class="c-label">erro</span>' + esc(j.message || 'Falha ao listar.');
            }
        } catch (err) {
            resultConsole.innerHTML = '<span class="c-label">erro</span>' + esc(err.message);
        }
    }

    // ---- logout ----
    btnLogout.addEventListener('click', async () => {
        try { await fetch('/logout/', { method: 'POST', headers: { 'X-CSRFToken': getCsrf() } }); } catch(_){}
        lock();
        authResult.classList.add('hidden');
        loginForm.reset();
        operationForm.reset();
        actionTabs.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        actionTabs.querySelector('.tab').classList.add('active');
        actionHidden.value = 'create';
        updateFields();
    });

    // ---- Escape fecha modais ----
    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Escape') return;
        if (!rootModal.classList.contains('hidden'))   { closeRootModal();   if (_modalResolve)  { _modalResolve(null);  _modalResolve = null; } }
        if (!deleteModal.classList.contains('hidden'))  { closeDeleteModal(); if (_deleteResolve) { _deleteResolve(false); _deleteResolve = null; } }
    });
});
