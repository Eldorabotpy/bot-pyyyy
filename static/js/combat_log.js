/* Registro visual comum para caçada, PvP, PvE, invasões e chefes dimensionais. */
(function () {
    "use strict";

    const states = new WeakMap();
    const tones = new Set(["neutral", "player", "critical", "enemy", "support", "warning", "ally", "event", "dodge", "defense"]);

    function resolveRoot(root) {
        if (typeof root === "string") return document.getElementById(root) || document.querySelector(root);
        return root instanceof Element ? root : null;
    }

    function textOnly(value) {
        const raw = String(value ?? "");
        if (!raw.includes("<")) return raw.trim();
        const parsed = new DOMParser().parseFromString(raw, "text/html");
        return String(parsed.body.textContent || "").replace(/\s+/g, " ").trim();
    }

    function infer(text, raw = {}) {
        const lower = text.toLocaleLowerCase("pt-BR");
        const valueMatch = text.match(/(?:causou|dano|perdeu|cura(?:ou)?|recuperou)\D{0,16}(\d+)/i);
        let tone = raw.tone || "event";
        let title = raw.title || "Acontecimento";

        if (raw.is_inimigo || raw.inimigo || lower.includes("inimigo atacou") || lower.includes("atacou você")) {
            tone = "enemy"; title = "Ataque inimigo";
        } else if (lower.includes("esquiv") || lower.includes("errou")) {
            tone = "dodge"; title = "Esquiva";
        } else if (lower.includes("defendeu") || lower.includes("bloqueou") || lower.includes("defesa")) {
            tone = "defense"; title = "Defesa";
        } else if (lower.includes("crític") || lower.includes("critico") || raw.critico) {
            tone = "critical"; title = "Ataque crítico";
        } else if (lower.includes("cura") || lower.includes("curou") || lower.includes("restaur")) {
            tone = "support"; title = "Recuperação";
        } else if (/falh|insuficiente|quebrad|aguarde|erro/.test(lower)) {
            tone = "warning"; title = "Ação não concluída";
        } else if (raw.golpe || /ataque\s*\d+|golpe\s*\d+/i.test(text) || /dano|causou/.test(lower)) {
            tone = raw.is_ally ? "ally" : "player"; title = "Ataque";
        } else if (raw.is_ally) {
            tone = "ally"; title = "Ação de aliado";
        }

        if (raw.title) title = String(raw.title);
        const hit = Number(raw.hit_number ?? raw.golpe ?? 0);
        const hits = Number(raw.total_hits ?? raw.num_hits ?? 0);
        if (hit > 0) title = `Golpe ${hit}${hits > 0 ? `/${hits}` : ""}`;
        const value = Object.prototype.hasOwnProperty.call(raw, "value")
            ? raw.value
            : raw.is_attack_event === false
                ? null
                : raw.dano ?? raw.damage ?? raw.cura ?? (valueMatch ? Number(valueMatch[1]) : null);
        return {
            actor: String(raw.actor || raw.autor_nome || raw.autor || (raw.is_inimigo || raw.inimigo ? "Inimigo" : "Sistema")),
            title,
            detail: String(raw.detail ?? text ?? ""),
            tone: tones.has(tone) ? tone : "event",
            value,
            unit: String(raw.unit || (raw.cura ? "HP" : "DANO")),
            flag: String(raw.flag || (raw.critico ? "Crítico" : ""))
        };
    }

    function ensure(root) {
        if (!root) return null;
        let state = states.get(root);
        if (state && state.feed?.isConnected) return state;

        root.classList.add("eldora-combat-log");
        root.setAttribute("data-combat-log", "");
        root.setAttribute("role", "region");
        root.setAttribute("aria-label", root.getAttribute("aria-label") || "Registro de combate");

        let feature = root.querySelector(".eldora-log-feature");
        let heading = root.querySelector(".eldora-log-history-heading");
        let feed = root.querySelector(".eldora-log-history");
        if (!feature || !heading || !feed) {
            root.replaceChildren();
            feature = document.createElement("div");
            feature.className = "eldora-log-feature";
            feature.dataset.tone = "neutral";
            const titleId = root.id === "combat-log-box" ? "log-texto-1" : root.id === "pvp-caixa-logs-scroll" ? "pvp-log-texto-1" : "";
            const detailId = root.id === "combat-log-box" ? "log-texto-2" : root.id === "pvp-caixa-logs-scroll" ? "pvp-log-texto-2" : "";
            const numberId = root.id === "combat-log-box" ? "combat-log-value-number" : "";
            const unitId = root.id === "combat-log-box" ? "combat-log-value-unit" : "";
            const phaseId = root.id === "combat-log-box" ? "combat-log-phase" : "";
            const countId = root.id === "combat-log-box" ? "combat-log-count" : "";
            feature.innerHTML = `<span class="eldora-log-mark" aria-hidden="true"></span><div class="eldora-log-feature-copy"><div class="eldora-log-meta"><span class="eldora-log-eyebrow">Última ação</span><span class="eldora-log-phase" data-log-phase ${phaseId ? `id="${phaseId}"` : ""} aria-live="polite">Sua vez</span></div><strong class="eldora-log-title" data-log-title ${titleId ? `id="${titleId}"` : ""}>Combate iniciado</strong><span class="eldora-log-detail" data-log-detail ${detailId ? `id="${detailId}"` : ""}>Aguardando a primeira ação.</span></div><span class="eldora-log-value" data-log-value hidden><strong data-log-number ${numberId ? `id="${numberId}"` : ""}></strong><small data-log-unit ${unitId ? `id="${unitId}"` : ""}></small></span><span class="eldora-log-flag" data-log-flag hidden></span>`;
            heading = document.createElement("div");
            heading.className = "eldora-log-history-heading";
            heading.innerHTML = `<span>Registro da batalha</span><span data-log-count ${countId ? `id="${countId}"` : ""}>0 ações</span>`;
            feed = document.createElement("div");
            feed.className = "eldora-log-history";
            feed.setAttribute("role", "log");
            feed.setAttribute("aria-live", "polite");
            feed.setAttribute("aria-label", "Ações da batalha");
            feed.tabIndex = 0;
            const empty = document.createElement("div");
            empty.className = "eldora-log-empty";
            empty.textContent = "Os acontecimentos da batalha aparecerão aqui.";
            feed.appendChild(empty);
            root.append(feature, heading, feed);
        } else {
            feature.classList.add("eldora-log-feature");
            heading.classList.add("eldora-log-history-heading");
            feed.classList.add("eldora-log-history");
            feed.setAttribute("role", "log");
            feed.setAttribute("aria-live", "polite");
        }

        state = { root, feature, heading, feed, count: feed.querySelectorAll(".eldora-log-entry").length, sessionKey: null, syncCounts: new Map() };
        states.set(root, state);
        return state;
    }

    function setPhase(root, phase) {
        const state = ensure(resolveRoot(root));
        const node = state?.feature.querySelector("[data-log-phase], .combat-log-phase");
        if (node) node.textContent = String(phase || "");
    }

    function clear(root, options = {}) {
        const state = ensure(resolveRoot(root));
        if (!state) return;
        state.feed.replaceChildren();
        state.count = 0;
        state.sessionKey = options.sessionKey ?? null;
        state.syncCounts.clear();
        state.feature.dataset.tone = "neutral";
        const title = state.feature.querySelector("[data-log-title], #log-texto-1, #pvp-log-texto-1");
        const detail = state.feature.querySelector("[data-log-detail], #log-texto-2, #pvp-log-texto-2");
        const value = state.feature.querySelector("[data-log-value], .combat-log-value");
        const flag = state.feature.querySelector("[data-log-flag], .combat-log-flag");
        const count = state.heading.querySelector("[data-log-count], #combat-log-count");
        const phase = state.feature.querySelector("[data-log-phase], .combat-log-phase");
        if (title) title.textContent = options.title || "Combate iniciado";
        if (detail) detail.textContent = options.detail || "Aguardando a primeira ação.";
        if (value) value.hidden = true;
        if (flag) flag.hidden = true;
        if (phase) phase.textContent = options.phase || "Sua vez";
        if (count) count.textContent = "0 ações";
        const empty = document.createElement("div");
        empty.className = "eldora-log-empty";
        empty.textContent = options.emptyText || "Os acontecimentos da batalha aparecerão aqui.";
        state.feed.appendChild(empty);
    }

    function push(root, rawEvent) {
        const state = ensure(resolveRoot(root));
        if (!state) return;
        const event = infer(textOnly(rawEvent?.text ?? rawEvent?.detail ?? ""), rawEvent || {});
        const title = state.feature.querySelector("[data-log-title], #log-texto-1, #pvp-log-texto-1");
        const detail = state.feature.querySelector("[data-log-detail], #log-texto-2, #pvp-log-texto-2");
        const value = state.feature.querySelector("[data-log-value], .combat-log-value");
        const number = state.feature.querySelector("[data-log-number], #combat-log-value-number");
        const unit = state.feature.querySelector("[data-log-unit], #combat-log-value-unit");
        const flag = state.feature.querySelector("[data-log-flag], .combat-log-flag");
        const phase = state.feature.querySelector("[data-log-phase], .combat-log-phase");
        if (title) title.textContent = event.title;
        if (detail) detail.textContent = event.detail;
        state.feature.dataset.tone = event.tone;
        if (phase) phase.textContent = "Turno resolvido";
        if (value) value.hidden = event.value === null || event.value === undefined || event.value === "";
        if (number) number.textContent = String(event.value ?? "");
        if (unit) unit.textContent = event.unit;
        if (flag) { flag.textContent = event.flag; flag.hidden = !event.flag; }

        const wasNearBottom = state.feed.scrollHeight - state.feed.scrollTop - state.feed.clientHeight < 36;
        state.feed.querySelector(".eldora-log-empty")?.remove();
        const line = document.createElement("div");
        line.className = "eldora-log-entry";
        line.dataset.tone = event.tone;
        const copy = document.createElement("div");
        copy.className = "eldora-log-entry-copy";
        const actor = document.createElement("span");
        actor.className = "eldora-log-entry-actor";
        actor.textContent = event.actor;
        const message = document.createElement("strong");
        message.className = "eldora-log-entry-title";
        message.textContent = event.title;
        const sub = document.createElement("span");
        sub.className = "eldora-log-entry-detail";
        sub.textContent = event.detail;
        copy.append(actor, message, sub);
        line.appendChild(copy);
        if (event.value !== null && event.value !== undefined && event.value !== "") {
            const val = document.createElement("span");
            val.className = "eldora-log-entry-value";
            val.textContent = `${event.value}${event.unit ? ` ${event.unit}` : ""}`;
            line.appendChild(val);
        }
        state.feed.appendChild(line);
        state.count += 1;
        const count = state.heading.querySelector("[data-log-count], #combat-log-count");
        if (count) count.textContent = `${state.count} ${state.count === 1 ? "ação" : "ações"}`;
        if (wasNearBottom) state.feed.scrollTop = state.feed.scrollHeight;
    }

    function pushText(root, text, options = {}) {
        push(root, { ...options, text: textOnly(text), detail: options.detail ?? textOnly(text) });
    }

    function sync(root, items, sessionKey) {
        const state = ensure(resolveRoot(root));
        if (!state) return;
        if (sessionKey !== undefined && state.sessionKey !== sessionKey) clear(state.root, { sessionKey, title: "Combate iniciado" });
        const countsNow = new Map();
        (Array.isArray(items) ? items : []).forEach((item) => {
            const raw = typeof item === "string" ? { text: item, detail: item } : (item || {});
            const sig = JSON.stringify([raw.id ?? "", raw.text ?? "", raw.actor ?? raw.autor_nome ?? "", raw.damage ?? raw.dano ?? "", raw.type ?? raw.tipo ?? ""]);
            const occurrence = (countsNow.get(sig) || 0) + 1;
            countsNow.set(sig, occurrence);
            if (occurrence > (state.syncCounts.get(sig) || 0)) push(state.root, raw);
        });
        countsNow.forEach((count, sig) => state.syncCounts.set(sig, Math.max(count, state.syncCounts.get(sig) || 0)));
    }

    window.EldoraCombatLog = { mount: (root) => ensure(resolveRoot(root)), clear, push, pushText, setPhase, sync, textOnly };
    document.addEventListener("DOMContentLoaded", () => document.querySelectorAll("[data-combat-log]").forEach((root) => ensure(root)));
})();
